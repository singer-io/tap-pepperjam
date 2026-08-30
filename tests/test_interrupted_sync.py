"""Integration tests for tap-pepperjam interrupted sync resumption with mocked data.

Verifies that:
- update_currently_syncing correctly tracks the in-progress stream
- Clearing currently_syncing after completion removes it from state
- After an interruption, get_bookmark returns the mid-point bookmark
- Restarting sync from interrupted state only emits records newer than the bookmark
- FULL_TABLE streams are always fully replicated on resume (no bookmark to respect)
"""
import unittest
from unittest.mock import MagicMock, patch

try:
    from base import PepperjamBaseTest, make_api_response, make_mock_client, _select_stream
except ImportError:
    from tests.base import PepperjamBaseTest, make_api_response, make_mock_client, _select_stream

from tap_pepperjam.sync import (
    get_bookmark,
    update_currently_syncing,
    process_records,
    sync_endpoint,
)
from tap_pepperjam.discover import discover
from singer import utils


# ---------------------------------------------------------------------------
# update_currently_syncing
# ---------------------------------------------------------------------------

class TestUpdateCurrentlySyncing(PepperjamBaseTest, unittest.TestCase):
    """Verify currently_syncing state tracking works correctly."""

    @patch("tap_pepperjam.sync.singer.write_state")
    def test_currently_syncing_set_to_stream_name(self, _mock_ws):
        """update_currently_syncing writes the stream name to state."""
        state = {}
        update_currently_syncing(state, "creative_advanced")
        self.assertEqual(state.get("currently_syncing"), "creative_advanced")

    @patch("tap_pepperjam.sync.singer.write_state")
    def test_currently_syncing_cleared_when_none(self, _mock_ws):
        """update_currently_syncing removes 'currently_syncing' key when given None."""
        state = {"currently_syncing": "creative_advanced"}
        update_currently_syncing(state, None)
        self.assertNotIn("currently_syncing", state)

    @patch("tap_pepperjam.sync.singer.write_state")
    def test_currently_syncing_noop_when_not_present_and_none(self, _mock_ws):
        """When called with None on a state without 'currently_syncing', the else branch
        runs singer.set_currently_syncing(state, None) setting the key to None."""
        state = {}
        update_currently_syncing(state, None)
        # The tap's else-branch calls singer.set_currently_syncing which sets key to None
        self.assertIsNone(state.get("currently_syncing"))

    @patch("tap_pepperjam.sync.singer.write_state")
    def test_currently_syncing_updated_between_streams(self, _mock_ws):
        """update_currently_syncing can switch from one stream to another."""
        state = {}
        update_currently_syncing(state, "creative_advanced")
        self.assertEqual(state.get("currently_syncing"), "creative_advanced")
        update_currently_syncing(state, "publisher")
        self.assertEqual(state.get("currently_syncing"), "publisher")


# ---------------------------------------------------------------------------
# Interrupted sync: bookmark-based resumption
# ---------------------------------------------------------------------------

class TestInterruptedSyncResumption(PepperjamBaseTest, unittest.TestCase):
    """Verify that bookmark state from an interrupted sync is respected on resume."""

    INTERRUPT_BOOKMARK = "2021-06-15T00:00:00Z"

    def _interrupted_state(self, stream_name, rep_key):
        """Return a state dict that mimics an interrupted sync midway through a stream."""
        return {
            "currently_syncing": stream_name,
            "bookmarks": {
                stream_name: self.INTERRUPT_BOOKMARK,
            },
        }

    def test_get_bookmark_reads_interrupt_state(self):
        """After interruption, get_bookmark returns the mid-point bookmark."""
        state = self._interrupted_state("creative_advanced", "modified")
        bm = get_bookmark(state, "creative_advanced", "2020-01-01T00:00:00Z")
        self.assertEqual(bm, self.INTERRUPT_BOOKMARK)

    @patch("tap_pepperjam.sync.singer.messages.write_record")
    def test_resume_does_not_replay_already_synced_records(self, mock_wr):
        """Records with modified < interrupt bookmark are NOT replayed on resume."""
        catalog = _select_stream(discover(MagicMock()), "creative_advanced")
        time_extracted = utils.now()
        # Simulate records fetched on resume — all are before the interrupt point
        r1 = self._generate_stream_record("creative_advanced", date_value="2021-01-01T00:00:00Z")
        r1["id"] = 1
        r2 = self._generate_stream_record("creative_advanced", date_value="2021-04-30T00:00:00Z")
        r2["id"] = 2
        records_before_interrupt = [r1, r2]
        process_records(
            catalog=catalog,
            stream_name="creative_advanced",
            records=records_before_interrupt,
            time_extracted=time_extracted,
            bookmark_field="modified",
            max_bookmark_value=None,
            last_datetime=self.INTERRUPT_BOOKMARK,
        )
        mock_wr.assert_not_called()

    @patch("tap_pepperjam.sync.singer.messages.write_record")
    def test_resume_emits_only_new_records(self, mock_wr):
        """Only records with modified >= interrupt bookmark are emitted on resume."""
        catalog = _select_stream(discover(MagicMock()), "creative_advanced")
        time_extracted = utils.now()
        r_old = self._generate_stream_record("creative_advanced", date_value="2021-05-01T00:00:00Z")
        r_old["id"] = 10  # before → excluded
        r_at = self._generate_stream_record("creative_advanced", date_value="2021-06-15T00:00:00Z")
        r_at["id"] = 20   # at bookmark → included
        r_new = self._generate_stream_record("creative_advanced", date_value="2021-12-31T00:00:00Z")
        r_new["id"] = 30  # after → included
        records = [r_old, r_at, r_new]
        _, count = process_records(
            catalog=catalog,
            stream_name="creative_advanced",
            records=records,
            time_extracted=time_extracted,
            bookmark_field="modified",
            max_bookmark_value=None,
            last_datetime=self.INTERRUPT_BOOKMARK,
        )
        self.assertEqual(count, 2)
        self.assertEqual(mock_wr.call_count, 2)

    @patch("tap_pepperjam.sync.singer.write_state")
    @patch("tap_pepperjam.sync.process_records",
           return_value=("2021-12-01T00:00:00Z", 2))
    def test_resumed_sync_endpoint_advances_bookmark_past_interrupt(self, _mock_pr, _mock_ws):
        """After a successful resume, the bookmark advances past the interrupt point."""
        catalog = _select_stream(discover(MagicMock()), "creative_banner")
        state = self._interrupted_state("creative_banner", "modified")
        client = make_mock_client([
            make_api_response([{"id": "new_1"}, {"id": "new_2"}])
        ])

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

        new_bookmark = state["bookmarks"].get("creative_banner")
        self.assertIsNotNone(new_bookmark)
        self.assertGreaterEqual(new_bookmark, self.INTERRUPT_BOOKMARK)


# ---------------------------------------------------------------------------
# Full-table streams always fully replicate (ignore state)
# ---------------------------------------------------------------------------

class TestFullTableStreamOnResume(PepperjamBaseTest, unittest.TestCase):
    """Verify FULL_TABLE streams are fully replicated regardless of stored state."""

    @patch("tap_pepperjam.sync.singer.messages.write_record")
    def test_full_table_stream_emits_all_records_with_stale_state(self, mock_wr):
        """FULL_TABLE stream emits all records even when state has leftover entries."""
        catalog = _select_stream(discover(MagicMock()), "publisher")
        time_extracted = utils.now()
        records = [dict(self._generate_stream_record("publisher"), id=i) for i in range(1, 5)]

        # Even with stale state, FULL_TABLE has no bookmark_field — all records emitted
        _, count = process_records(
            catalog=catalog,
            stream_name="publisher",
            records=records,
            time_extracted=time_extracted,
            bookmark_field=None,    # FULL_TABLE — no filtering
            max_bookmark_value=None,
            last_datetime="2024-01-01T00:00:00Z",
        )

        self.assertEqual(count, 4)
        self.assertEqual(mock_wr.call_count, 4)

    @patch("tap_pepperjam.sync.singer.messages.write_record")
    def test_full_table_group_emits_all_records(self, mock_wr):
        """'group' FULL_TABLE stream emits all records even with a very recent state."""
        catalog = _select_stream(discover(MagicMock()), "group")
        time_extracted = utils.now()
        records = [dict(self._generate_stream_record("group"), id=i) for i in range(1, 3)]

        _, count = process_records(
            catalog=catalog,
            stream_name="group",
            records=records,
            time_extracted=time_extracted,
            bookmark_field=None,
            max_bookmark_value=None,
            last_datetime="2099-01-01T00:00:00Z",  # far future — no effect on FULL_TABLE
        )

        self.assertEqual(count, 2)

    # ── currently_syncing cleared on completion ────────────────────────────

    @patch("tap_pepperjam.sync.singer.write_state")
    @patch("tap_pepperjam.sync.process_records", return_value=(None, 3))
    def test_currently_syncing_cleared_after_full_table_sync(self, _mock_pr, _mock_ws):
        """update_currently_syncing(state, None) removes the key after stream completes."""
        state = {"currently_syncing": "publisher"}
        update_currently_syncing(state, None)
        self.assertNotIn("currently_syncing", state)


if __name__ == "__main__":
    unittest.main()
