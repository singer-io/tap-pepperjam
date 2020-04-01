import backoff
import requests
from requests.exceptions import ConnectionError
from singer import metrics
import singer

LOGGER = singer.get_logger()

API_VERSION = '20120402'


class Server5xxError(Exception):
    pass


class Server429Error(Exception):
    pass


class PepperjamError(Exception):
    pass


class PepperjamInvalidParametersError(PepperjamError):
    pass


class PepperjamAuthenticationrror(PepperjamError):
    pass


class PepperjamForbiddenError(PepperjamError):
    pass


class PepperjamNotFoundError(PepperjamError):
    pass


class PepperjamMethodNotAllowedError(PepperjamError):
    pass


class PepperjamLogicalConflictError(PepperjamError):
    pass


ERROR_CODE_EXCEPTION_MAPPING = {
    400: PepperjamInvalidParametersError,
    401: PepperjamAuthenticationrror,
    403: PepperjamForbiddenError,
    404: PepperjamNotFoundError,
    405: PepperjamMethodNotAllowedError,
    409: PepperjamLogicalConflictError}


# Error Message Example:
# {
#     "meta":{
#         "status":{
#             "code": 403,
#             "message": "Forbidden"
#         }
#     },
#     "data":[]
# }

def get_exception_for_error_code(error_code):
    return ERROR_CODE_EXCEPTION_MAPPING.get(error_code, PepperjamError)

def raise_for_error(response):
    try:
        response.raise_for_status()
    except (requests.HTTPError, requests.ConnectionError) as error:
        try:
            content_length = len(response.content)
            if content_length == 0:
                # There is nothing we can do here since Pepperjam has neither sent
                # us a 2xx response nor a response content.
                return
            response = response.json()
            error_code = response.get('meta', {}).get('status', {}).get('code')
            error_message = response.get('meta', {}).get('status', {}).get('message')
            if error_code and error_message:
                message = '%s: %s' % error_code, error_message
                ex = get_exception_for_error_code(error_code)
                if error_code == 401 and 'Authentication error' in error_message:
                    LOGGER.error("Your API Key is invalid or has expired as per Pepperjam’s \
                        security policy. \n Please generate a new API Key in the Pepperjam Console \
                            and resume extraction.")
                raise ex(message)
            else:
                raise PepperjamError(error)
        except (ValueError, TypeError):
            raise PepperjamError(error)


class PepperjamClient(object):
    def __init__(self,
                 api_key,
                 user_agent=None):
        self.__api_key = api_key
        self.__user_agent = user_agent
        self.__session = requests.Session()
        self.__verified = False
        self.base_url = 'https://api.pepperjamnetwork.com/{}/advertiser'.format(
            API_VERSION)

    def __enter__(self):
        self.__verified = self.check_api_key()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.__session.close()

    @backoff.on_exception(backoff.expo,
                          Server5xxError,
                          max_tries=5,
                          factor=2)
    def check_api_key(self):
        if self.__api_key is None:
            raise Exception('Error: Missing credentials api_key.')
        headers = {}
        if self.__user_agent:
            headers['User-Agent'] = self.__user_agent
        params = {
            'apiKey': self.__api_key,
            'format': 'json',
            'page': 1
        }
        headers['Accept'] = 'application/json'
        response = self.__session.get(
            # Simple endpoint that returns 1 page of Group records
            url='{}/{}'.format(self.base_url, 'group'),
            params=params,
            headers=headers)
        if response.status_code != 200:
            LOGGER.error('Error status_code = {}'.format(response.status_code))
            raise_for_error(response)
        else:
            resp = response.json()
            if 'meta' in resp:
                return True
            else:
                return False


    @backoff.on_exception(backoff.expo,
                          (Server5xxError, ConnectionError, Server429Error),
                          max_tries=5,
                          factor=2)
    def request(self, method, path=None, url=None, **kwargs):
        if not self.__verified:
            self.__verified = self.check_api_key()

        if not url and path:
            url = '{}/{}/'.format(self.base_url, path)

        if 'endpoint' in kwargs:
            endpoint = kwargs['endpoint']
            del kwargs['endpoint']
        else:
            endpoint = None

        # Authenticate: apiKey in query parameters
        params = kwargs.get('params')
        if not params:
            params = {}
        if isinstance(params, str):
            if 'format' not in params:
                params = '{}&format=json'.format(params)
            if not 'apiKey' in params:
                params = '{}&apiKey={}'.format(params, self.__api_key)
        elif isinstance(params, dict):
            if 'format' not in params:
                params['format'] = 'json'
            if 'apiKey' not in params:
                params['apiKey'] = self.__api_key
        kwargs['params'] = params

        if 'headers' not in kwargs:
            kwargs['headers'] = {}
        kwargs['headers']['Accept'] = 'application/json'

        if self.__user_agent:
            kwargs['headers']['User-Agent'] = self.__user_agent

        if method == 'POST':
            kwargs['headers']['Content-Type'] = 'application/json'

        with metrics.http_request_timer(endpoint) as timer:
            response = self.__session.request(method, url, **kwargs)
            timer.tags[metrics.Tag.http_status_code] = response.status_code

        if response.status_code >= 500:
            raise Server5xxError()

        if response.status_code != 200:
            raise_for_error(response)

        return response.json()

    def get(self, path, **kwargs):
        return self.request('GET', path=path, **kwargs)

    def post(self, path, **kwargs):
        return self.request('POST', path=path, **kwargs)
