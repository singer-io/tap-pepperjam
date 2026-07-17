"""Integration tests for tap-pepperjam start_date filtering with mocked data.

Verifies that:
- INCREMENTAL streams filter records based on the start_date bookmark
- A later start_date results in fewer or equal records than an earlier start_date
- FULL_TABLE streams always replicate all records regardless of start_date
"""
import unittest
from unittest.mock import MagicMock, patch

try:
    from base import PepperjamBaseTest, make_api_response, make_mock_client, _select_stream
except ImportError:
    from tests.base import PepperjamBaseTest, make_api_response, make_mock_client, _select_stream

from tap_pepperjam.sync import process_records, sync_endpoint, get_bookmark
from tap_pepperjam.discover import discover
from singer import utils


# ---------------------------------------------------------------------------
# Start date tests
# ---------------------------------------------------------------------------

class TestPepperjamStartDate(PepperjamBaseTest, unittest.TestCase):
    """Verify start_date filtering behaviour for incremental and full-table streams."""

    # ── get_bookmark uses start_date as default ────────────────────────────

    def test_get_bookmark_returns_start_date_when_no_bookmark(self):
        """get_bookmark returns start_date when state contains no bookmark for the stream."""
        start_date = "2021-01-01T00:00:00Z"
        result = get_bookmark({}, "creative_advanced", start_date)
        self.assertEqual(result, start_date)

    def test_get_bookmark_ignores_start_date_when_bookmark_exists(self):
        """get_bookmark returns stored bookmark, not start_date, when bookmark is present."""
        start_date = "2021-01-01T00:00:00Z"
        stored = "2022-06-15T00:00:00Z"
        state = {"bookmarks": {"creative_advanced": stored}}
        result = get_bookmark(state, "creative_advanced", start_date)
        self.assertEqual(result, stored)

    # ── process_records: early vs late start_date ─────────────────────────

    @patch("tap_pepperjam.sync.singer.messages.write_record")
    def test_records_from_before_start_date_are_excluded(self, mock_wr):
        """process_records excludes records dated before last_datetime (start_date)."""
        catalog = _select_stream(discover(MagicMock()), "creative_advanced")
        time_extracted = utils.now()
        # All three records pre-date the start_date of 2021-01-01
        r1 = dict(self._generate_stream_record("creative_advanced", date_value="2018-01-01T00:00:00Z"), id=1)
        r2 = dict(self._generate_stream_record("creative_advanced", date_value="2019-06-01T00:00:00Z"), id=2)
        r3 = dict(self._generate_stream_record("creative_advanced", date_value="2020-12-31T00:00:00Z"), id=3)
        records = [r1, r2, r3]
        process_records(
            catalog=catalog,
            stream_name="creative_advanced",
            records=records,
            time_extracted=time_extracted,
            bookmark_field="modified",
            max_bookmark_value=None,
            last_datetime="2021-01-01T00:00:00Z",
        )
        mock_wr.assert_not_called()

    @patch("tap_pepperjam.sync.singer.messages.write_record")
    def test_only_records_on_or_after_start_date_are_emitted(self, mock_wr):
        """process_records emits only records at or after last_datetime (start_date)."""
        catalog = _select_stream(discover(MagicMock()), "creative_advanced")
        time_extracted = utils.now()
        r_old = self._generate_stream_record("creative_advanced", date_value="2019-06-01T00:00:00Z")
        r_old["id"] = 10   # excluded (before start_date)
        r_exact = self._generate_stream_record("creative_advanced", date_value="2021-01-01T00:00:00Z")
        r_exact["id"] = 20  # included (== start_date)
        r_new = self._generate_stream_record("creative_advanced", date_value="2022-03-15T00:00:00Z")
        r_new["id"] = 30    # included (after start_date)
        records = [r_old, r_exact, r_new]
        _, count = process_records(
            catalog=catalog,
            stream_name="creative_advanced",
            records=records,
            time_extracted=time_extracted,
            bookmark_field="modified",
            max_bookmark_value=None,
            last_datetime="2021-01-01T00:00:00Z",
        )
        self.assertEqual(count, 2)
        self.assertEqual(mock_wr.call_count, 2)

    @patch("tap_pepperjam.sync.singer.messages.write_record")
    def test_later_start_date_yields_fewer_records(self, mock_wr):
        """A later start_date causes fewer records to be emitted than an earlier start_date."""
        catalog = _select_stream(discover(MagicMock()), "creative_banner")
        time_extracted = utils.now()
        mixed_records = [
            dict(self._generate_stream_record("creative_banner", date_value="2020-03-01T00:00:00Z"), id=1),
            dict(self._generate_stream_record("creative_banner", date_value="2020-08-15T00:00:00Z"), id=2),
            dict(self._generate_stream_record("creative_banner", date_value="2021-02-20T00:00:00Z"), id=3),
            dict(self._generate_stream_record("creative_banner", date_value="2021-11-10T00:00:00Z"), id=4),
        ]

        # Early start_date — expect all records emitted
        _, early_count = process_records(
            catalog=catalog,
            stream_name="creative_banner",
            records=mixed_records,
            time_extracted=time_extracted,
            bookmark_field="modified",
            max_bookmark_value=None,
            last_datetime="2020-01-01T00:00:00Z",
        )

        mock_wr.reset_mock()

        # Later start_date — expect fewer records
        _, late_count = process_records(
            catalog=catalog,
            stream_name="creative_banner",
            records=mixed_records,
            time_extracted=time_extracted,
            bookmark_field="modified",
            max_bookmark_value=None,
            last_datetime="2021-01-01T00:00:00Z",
        )

        self.assertLessEqual(late_count, early_count)

    # ── FULL_TABLE streams ignore start_date ──────────────────────────────

    @patch("tap_pepperjam.sync.singer.messages.write_record")
    def test_full_table_stream_emits_all_records_regardless_of_start_date(self, mock_wr):
        """process_records emits every record for a FULL_TABLE stream (no date filter)."""
        catalog = _select_stream(discover(MagicMock()), "publisher")
        time_extracted = utils.now()
        records = [dict(self._generate_stream_record("publisher"), id=i) for i in range(1, 6)]

        _, count = process_records(
            catalog=catalog,
            stream_name="publisher",
            records=records,
            time_extracted=time_extracted,
            bookmark_field=None,
            max_bookmark_value=None,
            last_datetime="2025-01-01T00:00:00Z",  # very late — no effect on FULL_TABLE
        )

        self.assertEqual(count, 5)
        self.assertEqual(mock_wr.call_count, 5)

    # ── sync_endpoint: start_date used as initial bookmark ────────────────

    @patch("tap_pepperjam.sync.singer.write_state")
    @patch("tap_pepperjam.sync.process_records",
           return_value=("2022-01-15T00:00:00Z", 3))
    def test_sync_endpoint_uses_start_date_as_initial_bookmark(self, mock_pr, _mock_ws):
        """When state has no bookmark, sync_endpoint uses start_date as last_datetime."""
        catalog = _select_stream(discover(MagicMock()), "creative_text")
        client = make_mock_client([make_api_response([{"id": str(i)} for i in range(3)])])
        start_date = "2021-06-01T00:00:00Z"

        sync_endpoint(
            client=client,
            config=self.config,
            catalog=catalog,
            state={},
            start_date=start_date,
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

        # process_records should have been called with last_datetime == start_date
        call_kwargs = mock_pr.call_args[1]
        self.assertEqual(call_kwargs["last_datetime"], start_date)


if __name__ == "__main__":
    unittest.main()
