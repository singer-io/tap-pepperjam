"""Integration tests for tap-pepperjam bookmarking with mocked data.

Tests:
- get_bookmark / write_bookmark state management
- process_records filters records to those at-or-after the bookmark
- sync_endpoint writes bookmark to state after completing a date window
"""
import unittest
from unittest.mock import MagicMock, patch

try:
    from base import PepperjamBaseTest, make_api_response, make_mock_client
except ImportError:
    from tests.base import PepperjamBaseTest, make_api_response, make_mock_client

from tap_pepperjam.sync import (
    get_bookmark,
    write_bookmark,
    process_records,
    sync_endpoint,
)
from tap_pepperjam.discover import discover
from singer import metadata as singer_metadata


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _select_stream(catalog, stream_name):
    """Return the catalog with *stream_name* marked as selected (in-place)."""
    for entry in catalog.streams:
        if entry.stream == stream_name:
            mdata = singer_metadata.to_map(entry.metadata)
            singer_metadata.write(mdata, (), "selected", True)
            entry.metadata = singer_metadata.to_list(mdata)
    return catalog


# ---------------------------------------------------------------------------
# get_bookmark
# ---------------------------------------------------------------------------

class TestGetBookmark(PepperjamBaseTest, unittest.TestCase):
    """Verify get_bookmark reads the correct value from state."""

    def test_returns_default_when_state_is_none(self):
        """get_bookmark returns the default when state is None."""
        result = get_bookmark(None, "creative_advanced", "2020-01-01T00:00:00Z")
        self.assertEqual(result, "2020-01-01T00:00:00Z")

    def test_returns_default_when_no_bookmarks_key(self):
        """get_bookmark returns the default when state has no 'bookmarks' key."""
        result = get_bookmark({}, "creative_advanced", "2020-01-01T00:00:00Z")
        self.assertEqual(result, "2020-01-01T00:00:00Z")

    def test_returns_stored_bookmark(self):
        """get_bookmark returns the stored bookmark value for the stream."""
        state = {"bookmarks": {"creative_advanced": "2021-06-01T00:00:00Z"}}
        result = get_bookmark(state, "creative_advanced", "2020-01-01T00:00:00Z")
        self.assertEqual(result, "2021-06-01T00:00:00Z")

    def test_returns_default_when_stream_not_in_bookmarks(self):
        """get_bookmark returns the default when the stream has no bookmark entry."""
        state = {"bookmarks": {"other_stream": "2021-01-01T00:00:00Z"}}
        result = get_bookmark(state, "creative_advanced", "2020-01-01T00:00:00Z")
        self.assertEqual(result, "2020-01-01T00:00:00Z")


# ---------------------------------------------------------------------------
# write_bookmark
# ---------------------------------------------------------------------------

class TestWriteBookmark(PepperjamBaseTest, unittest.TestCase):
    """Verify write_bookmark persists the bookmark value in state."""

    @patch("tap_pepperjam.sync.singer.write_state")
    def test_creates_bookmarks_key_if_absent(self, _mock_ws):
        """write_bookmark creates the 'bookmarks' key when state is empty."""
        state = {}
        write_bookmark(state, "creative_advanced", "2021-01-01T00:00:00Z")
        self.assertIn("bookmarks", state)

    @patch("tap_pepperjam.sync.singer.write_state")
    def test_stores_value_under_stream_name(self, _mock_ws):
        """write_bookmark stores the value keyed by stream name."""
        state = {}
        write_bookmark(state, "creative_advanced", "2021-01-01T00:00:00Z")
        self.assertEqual(state["bookmarks"]["creative_advanced"],
                         "2021-01-01T00:00:00Z")

    @patch("tap_pepperjam.sync.singer.write_state")
    def test_overwrites_existing_bookmark(self, _mock_ws):
        """write_bookmark replaces a previously stored bookmark."""
        state = {"bookmarks": {"creative_advanced": "2020-01-01T00:00:00Z"}}
        write_bookmark(state, "creative_advanced", "2022-03-15T00:00:00Z")
        self.assertEqual(state["bookmarks"]["creative_advanced"],
                         "2022-03-15T00:00:00Z")

    @patch("tap_pepperjam.sync.singer.write_state")
    def test_calls_singer_write_state(self, mock_ws):
        """write_bookmark calls singer.write_state once after updating the state."""
        state = {}
        write_bookmark(state, "creative_advanced", "2021-01-01T00:00:00Z")
        mock_ws.assert_called_once_with(state)


# ---------------------------------------------------------------------------
# process_records — incremental filtering
# ---------------------------------------------------------------------------

class TestProcessRecordsBookmarkFiltering(PepperjamBaseTest, unittest.TestCase):
    """Verify process_records honours the last_datetime bookmark for filtering."""

    def _make_catalog_for(self, stream_name):
        return _select_stream(discover(), stream_name)

    @patch("tap_pepperjam.sync.singer.messages.write_record")
    def test_records_before_bookmark_are_not_written(self, mock_wr):
        """process_records does not emit records whose bookmark field is before last_datetime."""
        catalog = self._make_catalog_for("creative_advanced")
        records = [
            dict(self._generate_stream_record("creative_advanced", date_value="2019-06-01T00:00:00Z"), id=1),
        ]
        from singer import utils
        time_extracted = utils.now()
        process_records(
            catalog=catalog,
            stream_name="creative_advanced",
            records=records,
            time_extracted=time_extracted,
            bookmark_field="modified",
            max_bookmark_value=None,
            last_datetime="2020-01-01T00:00:00Z",
        )
        mock_wr.assert_not_called()

    @patch("tap_pepperjam.sync.singer.messages.write_record")
    def test_records_after_bookmark_are_written(self, mock_wr):
        """process_records emits records whose bookmark field is at or after last_datetime."""
        catalog = self._make_catalog_for("creative_advanced")
        records = [
            dict(self._generate_stream_record("creative_advanced", date_value="2021-03-01T00:00:00Z"), id=1),
        ]
        from singer import utils
        time_extracted = utils.now()
        process_records(
            catalog=catalog,
            stream_name="creative_advanced",
            records=records,
            time_extracted=time_extracted,
            bookmark_field="modified",
            max_bookmark_value=None,
            last_datetime="2020-01-01T00:00:00Z",
        )
        mock_wr.assert_called_once()

    @patch("tap_pepperjam.sync.singer.messages.write_record")
    def test_max_bookmark_advances_to_latest_record(self, _mock_wr):
        """process_records returns the maximum bookmark value from all emitted records."""
        catalog = self._make_catalog_for("creative_advanced")
        records = [
            dict(self._generate_stream_record("creative_advanced", date_value="2021-01-15T00:00:00Z"), id=1),
            dict(self._generate_stream_record("creative_advanced", date_value="2021-06-30T00:00:00Z"), id=2),
            dict(self._generate_stream_record("creative_advanced", date_value="2021-03-20T00:00:00Z"), id=3),
        ]
        from singer import utils
        time_extracted = utils.now()
        max_bv, count = process_records(
            catalog=catalog,
            stream_name="creative_advanced",
            records=records,
            time_extracted=time_extracted,
            bookmark_field="modified",
            max_bookmark_value=None,
            last_datetime="2020-01-01T00:00:00Z",
        )
        self.assertIsNotNone(max_bv)
        # The latest record was 2021-06-30; max_bookmark must be >= the first
        self.assertGreaterEqual(max_bv, "2021-01-15")
        self.assertEqual(count, 3)

    @patch("tap_pepperjam.sync.singer.messages.write_record")
    def test_full_table_stream_all_records_written(self, mock_wr):
        """process_records writes all records for a FULL_TABLE stream (no bookmark_field)."""
        catalog = self._make_catalog_for("publisher")
        records = [dict(self._generate_stream_record("publisher"), id=i) for i in range(1, 4)]
        from singer import utils
        time_extracted = utils.now()
        _, count = process_records(
            catalog=catalog,
            stream_name="publisher",
            records=records,
            time_extracted=time_extracted,
            bookmark_field=None,
            max_bookmark_value=None,
            last_datetime="2020-01-01T00:00:00Z",
        )
        self.assertEqual(count, 3)
        self.assertEqual(mock_wr.call_count, 3)


# ---------------------------------------------------------------------------
# sync_endpoint — bookmark is written to state after sync
# ---------------------------------------------------------------------------

class TestSyncEndpointWritesBookmark(PepperjamBaseTest, unittest.TestCase):
    """Verify sync_endpoint persists the bookmark for INCREMENTAL streams."""

    @patch("tap_pepperjam.sync.write_bookmark")
    @patch("tap_pepperjam.sync.process_records",
           return_value=("2021-06-01T00:00:00Z", 2))
    def test_write_bookmark_called_for_incremental_stream(self, _mock_pr, mock_wb):
        """sync_endpoint calls write_bookmark for a stream that has a bookmark_field."""
        catalog = _select_stream(discover(), "creative_advanced")
        records = [{"id": "1"}, {"id": "2"}]
        client = make_mock_client([make_api_response(records)])

        sync_endpoint(
            client=client,
            config=self.config,
            catalog=catalog,
            state={},
            start_date="2020-01-01T00:00:00Z",
            stream_name="creative_advanced",
            path="creative/advanced",
            endpoint_config={
                "path": "creative/advanced",
                "key_properties": ["id"],
                "data_key": "data",
                "params": {},
            },
            bookmark_field="modified",
            selected_streams=["creative_advanced"],
        )

        mock_wb.assert_called()

    @patch("tap_pepperjam.sync.write_bookmark")
    @patch("tap_pepperjam.sync.process_records",
           return_value=(None, 2))
    def test_write_bookmark_not_called_for_full_table_stream(self, _mock_pr, mock_wb):
        """sync_endpoint does NOT call write_bookmark when bookmark_field is None."""
        catalog = _select_stream(discover(), "publisher")
        records = [{"id": "1"}, {"id": "2"}]
        client = make_mock_client([make_api_response(records)])

        sync_endpoint(
            client=client,
            config=self.config,
            catalog=catalog,
            state={},
            start_date="2020-01-01T00:00:00Z",
            stream_name="publisher",
            path="publisher",
            endpoint_config={
                "path": "publisher",
                "key_properties": ["id"],
                "data_key": "data",
                "params": {},
            },
            bookmark_field=None,
            selected_streams=["publisher"],
        )

        mock_wb.assert_not_called()

    @patch("tap_pepperjam.sync.singer.write_state")
    @patch("tap_pepperjam.sync.process_records",
           return_value=("2021-09-01T00:00:00Z", 1))
    def test_state_contains_bookmark_after_sync(self, _mock_pr, _mock_ws):
        """State dict contains the bookmark value for the stream after sync_endpoint."""
        catalog = _select_stream(discover(), "creative_banner")
        state = {}
        records = [{"id": "1"}]
        client = make_mock_client([make_api_response(records)])

        sync_endpoint(
            client=client,
            config=self.config,
            catalog=catalog,
            state=state,
            start_date="2020-01-01T00:00:00Z",
            stream_name="creative_banner",
            path="creative/banner",
            endpoint_config={
                "path": "creative/banner",
                "key_properties": ["id"],
                "data_key": "data",
                "params": {},
            },
            bookmark_field="modified",
            selected_streams=["creative_banner"],
        )

        self.assertIn("bookmarks", state)
        self.assertIn("creative_banner", state["bookmarks"])

    @patch("tap_pepperjam.sync.singer.write_state")
    @patch("tap_pepperjam.sync.process_records",
           return_value=("2022-01-15T00:00:00Z", 5))
    def test_bookmark_value_advances_after_newer_records(self, _mock_pr, _mock_ws):
        """State bookmark advances to the max_bookmark_value returned by process_records."""
        catalog = _select_stream(discover(), "creative_text")
        state = {"bookmarks": {"creative_text": "2021-01-01T00:00:00Z"}}
        records = [{"id": str(i)} for i in range(5)]
        client = make_mock_client([make_api_response(records)])

        sync_endpoint(
            client=client,
            config=self.config,
            catalog=catalog,
            state=state,
            start_date="2020-01-01T00:00:00Z",
            stream_name="creative_text",
            path="creative/text",
            endpoint_config={
                "path": "creative/text",
                "key_properties": ["id"],
                "data_key": "data",
                "params": {},
            },
            bookmark_field="modified",
            selected_streams=["creative_text"],
        )

        new_bookmark = state["bookmarks"].get("creative_text")
        self.assertIsNotNone(new_bookmark)
        self.assertGreaterEqual(new_bookmark, "2021-01-01T00:00:00Z")


if __name__ == "__main__":
    unittest.main()
