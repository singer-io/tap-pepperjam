"""Integration tests for tap-pepperjam pagination with mocked data.

Verifies that sync_endpoint loops through all pages when the API response
contains a 'next' pagination link, and stops correctly when no next page exists.
"""
import copy
import unittest
from unittest.mock import patch

try:
    from base import PepperjamBaseTest, make_api_response, make_mock_client, _select_stream
except ImportError:
    from tests.base import PepperjamBaseTest, make_api_response, make_mock_client, _select_stream

from tap_pepperjam.sync import sync_endpoint
from tap_pepperjam.discover import discover


# ---------------------------------------------------------------------------
# Pagination tests
# ---------------------------------------------------------------------------

class TestPepperjamPagination(PepperjamBaseTest, unittest.TestCase):
    """Verify sync_endpoint fetches all pages until no 'next' link is present."""

    # Use the publisher stream (simple FULL_TABLE, key_props: id) for all pagination tests.
    STREAM_NAME = "publisher"
    ENDPOINT_CONFIG = {
        "path": "publisher",
        "key_properties": ["id"],
        "data_key": "data",
        "params": {"status": "joined"},
    }
    BASE_URL = "https://api.pepperjamnetwork.com/20120402/advertiser"
    PAGE2_URL = "https://api.pepperjamnetwork.com/20120402/advertiser/publisher/?page=2"
    PAGE3_URL = "https://api.pepperjamnetwork.com/20120402/advertiser/publisher/?page=3"

    def setUp(self):
        super().setUp()
        # Deep-copy so that sync_endpoint mutations (e.g. adding 'page' to
        # params) never bleed across tests.
        self.endpoint_config = copy.deepcopy(self.ENDPOINT_CONFIG)

    @patch("tap_pepperjam.sync.process_records", return_value=(None, 10))
    def test_two_pages_fetched_when_next_link_present(self, mock_pr):
        """sync_endpoint calls client.get twice when the first page returns a next link."""
        page1 = make_api_response(
            [{"id": str(i)} for i in range(10)],
            next_href=self.PAGE2_URL,
        )
        page2 = make_api_response([{"id": str(i)} for i in range(10, 20)])
        catalog = _select_stream(discover(), self.STREAM_NAME)
        client = make_mock_client([page1, page2])

        sync_endpoint(
            client=client,
            config=self.config,
            catalog=catalog,
            state={},
            start_date="2020-01-01T00:00:00Z",
            stream_name=self.STREAM_NAME,
            path=self.endpoint_config["path"],
            endpoint_config=self.endpoint_config,
            bookmark_field=None,
            selected_streams=[self.STREAM_NAME],
        )

        self.assertEqual(client.get.call_count, 2)

    @patch("tap_pepperjam.sync.process_records", return_value=(None, 5))
    def test_three_pages_fetched_for_three_page_response(self, mock_pr):
        """sync_endpoint calls client.get three times for a three-page result set."""
        page1 = make_api_response(
            [{"id": str(i)} for i in range(5)],
            next_href=self.PAGE2_URL,
        )
        page2 = make_api_response(
            [{"id": str(i)} for i in range(5, 10)],
            next_href=self.PAGE3_URL,
        )
        page3 = make_api_response([{"id": str(i)} for i in range(10, 15)])
        catalog = _select_stream(discover(), self.STREAM_NAME)
        client = make_mock_client([page1, page2, page3])

        sync_endpoint(
            client=client,
            config=self.config,
            catalog=catalog,
            state={},
            start_date="2020-01-01T00:00:00Z",
            stream_name=self.STREAM_NAME,
            path=self.endpoint_config["path"],
            endpoint_config=self.endpoint_config,
            bookmark_field=None,
            selected_streams=[self.STREAM_NAME],
        )

        self.assertEqual(client.get.call_count, 3)

    @patch("tap_pepperjam.sync.process_records", return_value=(None, 3))
    def test_single_page_stops_after_one_request(self, mock_pr):
        """sync_endpoint makes exactly one client.get call when no 'next' link is present."""
        page1 = make_api_response([{"id": str(i)} for i in range(3)])
        catalog = _select_stream(discover(), self.STREAM_NAME)
        client = make_mock_client([page1])

        sync_endpoint(
            client=client,
            config=self.config,
            catalog=catalog,
            state={},
            start_date="2020-01-01T00:00:00Z",
            stream_name=self.STREAM_NAME,
            path=self.endpoint_config["path"],
            endpoint_config=self.endpoint_config,
            bookmark_field=None,
            selected_streams=[self.STREAM_NAME],
        )

        self.assertEqual(client.get.call_count, 1)

    @patch("tap_pepperjam.sync.process_records", return_value=(None, 0))
    def test_empty_response_stops_immediately(self, mock_pr):
        """sync_endpoint breaks out immediately when client.get returns an empty response."""
        catalog = _select_stream(discover(), self.STREAM_NAME)
        client = make_mock_client([{}])  # empty dict = no data

        total = sync_endpoint(
            client=client,
            config=self.config,
            catalog=catalog,
            state={},
            start_date="2020-01-01T00:00:00Z",
            stream_name=self.STREAM_NAME,
            path=self.endpoint_config["path"],
            endpoint_config=self.endpoint_config,
            bookmark_field=None,
            selected_streams=[self.STREAM_NAME],
        )

        self.assertEqual(total, 0)
        mock_pr.assert_not_called()

    @patch("tap_pepperjam.sync.process_records", return_value=(None, 0))
    def test_second_page_url_used_for_subsequent_calls(self, mock_pr):
        """sync_endpoint uses the 'next' href from the response for the second request."""
        page1 = make_api_response(
            [{"id": "1"}],
            next_href=self.PAGE2_URL,
        )
        page2 = make_api_response([{"id": "2"}])
        catalog = _select_stream(discover(), self.STREAM_NAME)
        client = make_mock_client([page1, page2])

        sync_endpoint(
            client=client,
            config=self.config,
            catalog=catalog,
            state={},
            start_date="2020-01-01T00:00:00Z",
            stream_name=self.STREAM_NAME,
            path=self.endpoint_config["path"],
            endpoint_config=self.endpoint_config,
            bookmark_field=None,
            selected_streams=[self.STREAM_NAME],
        )

        second_call_kwargs = client.get.call_args_list[1][1]
        self.assertEqual(second_call_kwargs["url"], self.PAGE2_URL)

    @patch("tap_pepperjam.sync.process_records", return_value=(None, 10))
    def test_first_page_passes_query_params(self, mock_pr):
        """sync_endpoint passes query params to client.get on the first page request."""
        page1 = make_api_response([{"id": str(i)} for i in range(10)])
        catalog = _select_stream(discover(), self.STREAM_NAME)
        client = make_mock_client([page1])

        sync_endpoint(
            client=client,
            config=self.config,
            catalog=catalog,
            state={},
            start_date="2020-01-01T00:00:00Z",
            stream_name=self.STREAM_NAME,
            path=self.endpoint_config["path"],
            endpoint_config=self.endpoint_config,
            bookmark_field=None,
            selected_streams=[self.STREAM_NAME],
        )

        first_call_kwargs = client.get.call_args_list[0][1]
        # 'params' is a querystring or dict — the value should be non-None
        self.assertIsNotNone(first_call_kwargs.get("params"))

    @patch("tap_pepperjam.sync.process_records", return_value=(None, 5))
    def test_process_records_called_once_per_page(self, mock_pr):
        """process_records is called exactly once per fetched page."""
        page1 = make_api_response(
            [{"id": str(i)} for i in range(5)],
            next_href=self.PAGE2_URL,
        )
        page2 = make_api_response([{"id": str(i)} for i in range(5, 10)])
        catalog = _select_stream(discover(), self.STREAM_NAME)
        client = make_mock_client([page1, page2])

        sync_endpoint(
            client=client,
            config=self.config,
            catalog=catalog,
            state={},
            start_date="2020-01-01T00:00:00Z",
            stream_name=self.STREAM_NAME,
            path=self.endpoint_config["path"],
            endpoint_config=self.endpoint_config,
            bookmark_field=None,
            selected_streams=[self.STREAM_NAME],
        )

        self.assertEqual(mock_pr.call_count, 2)


if __name__ == "__main__":
    unittest.main()
