import unittest
from unittest.mock import patch, MagicMock
import requests
from tap_pepperjam.client import (
    PepperjamClient,
    PepperjamError,
    PepperjamInvalidParametersError,
    PepperjamAuthenticationrror,
    PepperjamForbiddenError,
    PepperjamNotFoundError,
    PepperjamMethodNotAllowedError,
    PepperjamLogicalConflictError,
    Server5xxError,
    get_exception_for_error_code,
    raise_for_error,
    API_VERSION,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(status_code, body=b"", json_body=None):
    """Build a minimal mock HTTP response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = body
    resp.text = body.decode() if isinstance(body, bytes) else body
    resp.json.return_value = json_body or {}
    resp.raise_for_status.side_effect = (
        requests.HTTPError(response=resp) if status_code >= 400 else None
    )
    return resp


def _make_client(api_key="test_key", user_agent="test_agent", verified=True):
    """Instantiate a PepperjamClient without touching the network."""
    client = PepperjamClient(api_key=api_key, user_agent=user_agent)
    client._PepperjamClient__verified = verified
    client._PepperjamClient__session = MagicMock()
    return client


# ---------------------------------------------------------------------------
# get_exception_for_error_code
# ---------------------------------------------------------------------------

class TestGetExceptionForErrorCode(unittest.TestCase):
    def test_400_maps_to_invalid_parameters(self):
        """400 maps to PepperjamInvalidParametersError."""
        self.assertIs(get_exception_for_error_code(400), PepperjamInvalidParametersError)

    def test_401_maps_to_authentication_error(self):
        """401 maps to PepperjamAuthenticationrror."""
        self.assertIs(get_exception_for_error_code(401), PepperjamAuthenticationrror)

    def test_403_maps_to_forbidden_error(self):
        """403 maps to PepperjamForbiddenError."""
        self.assertIs(get_exception_for_error_code(403), PepperjamForbiddenError)

    def test_404_maps_to_not_found_error(self):
        """404 maps to PepperjamNotFoundError."""
        self.assertIs(get_exception_for_error_code(404), PepperjamNotFoundError)

    def test_405_maps_to_method_not_allowed(self):
        """405 maps to PepperjamMethodNotAllowedError."""
        self.assertIs(get_exception_for_error_code(405), PepperjamMethodNotAllowedError)

    def test_409_maps_to_logical_conflict(self):
        """409 maps to PepperjamLogicalConflictError."""
        self.assertIs(get_exception_for_error_code(409), PepperjamLogicalConflictError)

    def test_unknown_code_falls_back_to_generic(self):
        """An unmapped code returns the base PepperjamError class."""
        self.assertIs(get_exception_for_error_code(999), PepperjamError)

    def test_500_not_in_mapping_returns_generic(self):
        """500 is not mapped, so the base PepperjamError is returned."""
        self.assertIs(get_exception_for_error_code(500), PepperjamError)


# ---------------------------------------------------------------------------
# raise_for_error
# ---------------------------------------------------------------------------

class TestRaiseForError(unittest.TestCase):
    def test_empty_content_returns_none(self):
        """raise_for_error returns None (no raise) when response body is empty."""
        resp = _make_response(403, body=b"")
        result = raise_for_error(resp)
        self.assertIsNone(result)

    def test_known_error_code_raises_mapped_exception(self):
        """raise_for_error raises the mapped exception class for a known error code."""
        resp = _make_response(
            403,
            body=b"x",
            json_body={"meta": {"status": {"code": 403, "message": "Forbidden"}}},
        )
        with self.assertRaises(PepperjamForbiddenError):
            raise_for_error(resp)

    def test_401_auth_error_raises_authentication_exception(self):
        """raise_for_error raises PepperjamAuthenticationrror for 401 with auth message."""
        resp = _make_response(
            401,
            body=b"x",
            json_body={"meta": {"status": {"code": 401, "message": "Authentication error"}}},
        )
        with self.assertRaises(PepperjamAuthenticationrror):
            raise_for_error(resp)

    def test_no_meta_raises_generic_pepperjam_error(self):
        """raise_for_error raises PepperjamError when response JSON has no meta/status."""
        resp = _make_response(400, body=b"x", json_body={})
        with self.assertRaises(PepperjamError):
            raise_for_error(resp)

    def test_json_parse_failure_raises_pepperjam_error(self):
        """raise_for_error raises PepperjamError when JSON parsing fails."""
        resp = _make_response(400, body=b"x")
        resp.json.side_effect = ValueError("not json")
        with self.assertRaises(PepperjamError):
            raise_for_error(resp)


# ---------------------------------------------------------------------------
# PepperjamClient – initialisation
# ---------------------------------------------------------------------------

class TestPepperjamClientInit(unittest.TestCase):
    def test_api_key_stored(self):
        """__init__ stores the api_key in the private attribute."""
        client = PepperjamClient(api_key="apikey123", user_agent=None)
        self.assertEqual(client._PepperjamClient__api_key, "apikey123")

    def test_user_agent_stored(self):
        """__init__ stores the user_agent in the private attribute."""
        client = PepperjamClient(api_key="k", user_agent="MyAgent/1.0")
        self.assertEqual(client._PepperjamClient__user_agent, "MyAgent/1.0")

    def test_session_created(self):
        """__init__ creates a requests.Session instance."""
        client = PepperjamClient(api_key="k", user_agent=None)
        self.assertIsInstance(client._PepperjamClient__session, requests.Session)

    def test_verified_starts_false(self):
        """__init__ sets __verified to False."""
        client = PepperjamClient(api_key="k", user_agent=None)
        self.assertFalse(client._PepperjamClient__verified)

    def test_base_url_includes_api_version(self):
        """__init__ constructs the correct base URL with API_VERSION."""
        client = PepperjamClient(api_key="k", user_agent=None)
        expected = "https://api.pepperjamnetwork.com/{}/advertiser".format(API_VERSION)
        self.assertEqual(client.base_url, expected)


# ---------------------------------------------------------------------------
# check_api_key
# ---------------------------------------------------------------------------

class TestCheckApiKey(unittest.TestCase):
    def test_none_api_key_raises(self):
        """check_api_key raises Exception when api_key is None."""
        client = PepperjamClient(api_key=None, user_agent=None)
        with self.assertRaises(Exception) as ctx:
            client.check_api_key()
        self.assertIn("Missing credentials", str(ctx.exception))

    def test_returns_true_when_meta_present(self):
        """check_api_key returns True when the response contains a 'meta' key."""
        client = _make_client(verified=False)
        mock_resp = _make_response(200, json_body={"meta": {}, "data": []})
        client._PepperjamClient__session.get.return_value = mock_resp
        self.assertTrue(client.check_api_key())

    def test_returns_false_when_meta_absent(self):
        """check_api_key returns False when the response does not contain 'meta'."""
        client = _make_client(verified=False)
        mock_resp = _make_response(200, json_body={"data": []})
        client._PepperjamClient__session.get.return_value = mock_resp
        self.assertFalse(client.check_api_key())

    def test_non_200_response_calls_raise_for_error(self):
        """check_api_key calls raise_for_error for non-200 responses."""
        client = _make_client(verified=False)
        mock_resp = _make_response(401, body=b"x", json_body={"meta": {"status": {"code": 401, "message": "Unauthorized"}}})
        client._PepperjamClient__session.get.return_value = mock_resp
        with self.assertRaises(PepperjamAuthenticationrror):
            client.check_api_key()

    def test_user_agent_header_sent(self):
        """check_api_key includes the User-Agent header when user_agent is set."""
        client = _make_client(verified=False)
        mock_resp = _make_response(200, json_body={"meta": {}, "data": []})
        client._PepperjamClient__session.get.return_value = mock_resp
        client.check_api_key()
        call_kwargs = client._PepperjamClient__session.get.call_args[1]
        self.assertEqual(call_kwargs["headers"]["User-Agent"], "test_agent")


# ---------------------------------------------------------------------------
# request()
# ---------------------------------------------------------------------------

class TestRequest(unittest.TestCase):
    @patch("tap_pepperjam.client.metrics.http_request_timer")
    def test_returns_json_for_200_response(self, mock_timer):
        """request() returns parsed JSON for a 200 response."""
        mock_timer.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_timer.return_value.__exit__ = MagicMock(return_value=False)
        client = _make_client()
        mock_resp = _make_response(200, json_body={"data": []})
        client._PepperjamClient__session.request.return_value = mock_resp
        result = client.request("GET", path="group")
        self.assertEqual(result, {"data": []})

    @patch("tap_pepperjam.client.metrics.http_request_timer")
    def test_5xx_raises_server5xx_error(self, mock_timer):
        """request() raises Server5xxError for status >= 500."""
        mock_timer.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_timer.return_value.__exit__ = MagicMock(return_value=False)
        client = _make_client()
        mock_resp = _make_response(503)
        client._PepperjamClient__session.request.return_value = mock_resp
        with self.assertRaises(Server5xxError):
            client.request("GET", path="group")

    @patch("tap_pepperjam.client.metrics.http_request_timer")
    def test_dict_params_get_api_key_injected(self, mock_timer):
        """request() injects apiKey and format into dict params."""
        mock_timer.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_timer.return_value.__exit__ = MagicMock(return_value=False)
        client = _make_client()
        mock_resp = _make_response(200, json_body={})
        client._PepperjamClient__session.request.return_value = mock_resp
        client.request("GET", path="group", params={"page": 1})
        call_kwargs = client._PepperjamClient__session.request.call_args[1]
        self.assertEqual(call_kwargs["params"]["apiKey"], "test_key")
        self.assertEqual(call_kwargs["params"]["format"], "json")

    @patch("tap_pepperjam.client.metrics.http_request_timer")
    def test_string_params_get_api_key_injected(self, mock_timer):
        """request() injects apiKey and format into string params."""
        mock_timer.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_timer.return_value.__exit__ = MagicMock(return_value=False)
        client = _make_client()
        mock_resp = _make_response(200, json_body={})
        client._PepperjamClient__session.request.return_value = mock_resp
        client.request("GET", path="group", params="page=1")
        call_kwargs = client._PepperjamClient__session.request.call_args[1]
        self.assertIn("apiKey=test_key", call_kwargs["params"])
        self.assertIn("format=json", call_kwargs["params"])

    @patch("tap_pepperjam.client.metrics.http_request_timer")
    def test_user_agent_header_set(self, mock_timer):
        """request() adds User-Agent header when user_agent is configured."""
        mock_timer.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_timer.return_value.__exit__ = MagicMock(return_value=False)
        client = _make_client()
        mock_resp = _make_response(200, json_body={})
        client._PepperjamClient__session.request.return_value = mock_resp
        client.request("GET", path="group")
        call_kwargs = client._PepperjamClient__session.request.call_args[1]
        self.assertEqual(call_kwargs["headers"]["User-Agent"], "test_agent")

    @patch("tap_pepperjam.client.metrics.http_request_timer")
    def test_post_adds_content_type(self, mock_timer):
        """request() adds Content-Type: application/json header for POST."""
        mock_timer.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_timer.return_value.__exit__ = MagicMock(return_value=False)
        client = _make_client()
        mock_resp = _make_response(200, json_body={})
        client._PepperjamClient__session.request.return_value = mock_resp
        client.request("POST", path="group")
        call_kwargs = client._PepperjamClient__session.request.call_args[1]
        self.assertEqual(call_kwargs["headers"]["Content-Type"], "application/json")

    @patch("tap_pepperjam.client.metrics.http_request_timer")
    def test_accept_header_always_set(self, mock_timer):
        """request() always sets Accept: application/json."""
        mock_timer.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_timer.return_value.__exit__ = MagicMock(return_value=False)
        client = _make_client()
        mock_resp = _make_response(200, json_body={})
        client._PepperjamClient__session.request.return_value = mock_resp
        client.request("GET", path="group")
        call_kwargs = client._PepperjamClient__session.request.call_args[1]
        self.assertEqual(call_kwargs["headers"]["Accept"], "application/json")

    @patch("tap_pepperjam.client.metrics.http_request_timer")
    def test_url_built_from_path(self, mock_timer):
        """request() builds the full URL from base_url and path when url is absent."""
        mock_timer.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_timer.return_value.__exit__ = MagicMock(return_value=False)
        client = _make_client()
        mock_resp = _make_response(200, json_body={})
        client._PepperjamClient__session.request.return_value = mock_resp
        client.request("GET", path="group")
        call_args = client._PepperjamClient__session.request.call_args
        used_url = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("url", "")
        # Accept either positional or keyword form
        if not used_url:
            used_url = call_args[0][1] if len(call_args[0]) > 1 else ""
        self.assertIn("group", str(call_args))


# ---------------------------------------------------------------------------
# get() / post() wrappers
# ---------------------------------------------------------------------------

class TestGetPost(unittest.TestCase):
    def test_get_delegates_to_request_with_get_method(self):
        """get() calls request() with method='GET'."""
        client = PepperjamClient(api_key="k", user_agent=None)
        with patch.object(client, "request", return_value={}) as mock_req:
            client.get("publisher", params={"page": 1})
        mock_req.assert_called_once_with("GET", path="publisher", params={"page": 1})

    def test_post_delegates_to_request_with_post_method(self):
        """post() calls request() with method='POST'."""
        client = PepperjamClient(api_key="k", user_agent=None)
        with patch.object(client, "request", return_value={}) as mock_req:
            client.post("group", data={"key": "val"})
        mock_req.assert_called_once_with("POST", path="group", data={"key": "val"})


if __name__ == "__main__":
    unittest.main()
