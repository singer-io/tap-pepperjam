"""Integration tests for tap-pepperjam automatic/minimum field replication.

Verifies that primary keys and replication keys (automatic fields) are always
present in emitted records, regardless of selection state.
"""
import unittest
from unittest.mock import patch

try:
    from base import PepperjamBaseTest
except ImportError:
    from tests.base import PepperjamBaseTest

from tap_pepperjam.discover import discover
from tap_pepperjam.sync import process_records
from singer import metadata as singer_metadata
from singer import utils


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _select_stream(catalog, stream_name):
    for entry in catalog.streams:
        if entry.stream == stream_name:
            mdata = singer_metadata.to_map(entry.metadata)
            singer_metadata.write(mdata, (), "selected", True)
            entry.metadata = singer_metadata.to_list(mdata)
    return catalog


# ---------------------------------------------------------------------------
# Automatic fields tests
# ---------------------------------------------------------------------------

class TestPepperjamAutomaticFields(PepperjamBaseTest, unittest.TestCase):
    """Verify primary keys and replication keys are always replicated."""

    def _automatic_fields_for(self, stream_name):
        """Return the union of primary keys and replication keys for a stream."""
        meta = self.expected_metadata()[stream_name]
        return meta[self.PRIMARY_KEYS] | meta[self.REPLICATION_KEYS]

    # ── Metadata: automatic field declarations ─────────────────────────────

    def test_primary_keys_marked_as_automatic_in_metadata(self):
        """Every primary key field has inclusion='automatic' in stream metadata."""
        for stream_name, meta in self.expected_metadata().items():
            with self.subTest(stream=stream_name):
                catalog = discover()
                entry = next(e for e in catalog.streams if e.stream == stream_name)
                mdata = singer_metadata.to_map(entry.metadata)
                for pk in meta[self.PRIMARY_KEYS]:
                    # Singer field-level metadata key is tuple ("properties", field_name)
                    inclusion = mdata.get(("properties", pk), {}).get("inclusion")
                    self.assertEqual(
                        inclusion, "automatic",
                        msg=f"Stream '{stream_name}', field '{pk}' expected inclusion=automatic, got '{inclusion}'",
                    )

    def test_replication_keys_marked_as_automatic_or_available(self):
        """Every replication key has inclusion='automatic' or 'available' in metadata."""
        for stream_name, meta in self.expected_metadata().items():
            for rep_key in meta[self.REPLICATION_KEYS]:
                with self.subTest(stream=stream_name, field=rep_key):
                    catalog = discover()
                    entry = next(e for e in catalog.streams if e.stream == stream_name)
                    mdata = singer_metadata.to_map(entry.metadata)
                    # Singer field-level metadata key is tuple ("properties", field_name)
                    inclusion = mdata.get(("properties", rep_key), {}).get("inclusion")
                    self.assertIn(
                        inclusion, {"automatic", "available"},
                        msg=f"Stream '{stream_name}', rep_key '{rep_key}' has unexpected inclusion '{inclusion}'",
                    )

    # ── Record output: primary keys always present ─────────────────────────

    @patch("tap_pepperjam.sync.singer.messages.write_record")
    def test_publisher_primary_key_always_in_emitted_record(self, mock_wr):
        """Primary key 'id' is always present in emitted publisher records."""
        catalog = _select_stream(discover(), "publisher")
        record = self._generate_stream_record("publisher")
        time_extracted = utils.now()

        process_records(
            catalog=catalog,
            stream_name="publisher",
            records=[record],
            time_extracted=time_extracted,
            bookmark_field=None,
            max_bookmark_value=None,
            last_datetime=self.default_start_date,
        )

        self.assertEqual(mock_wr.call_count, 1)
        emitted = mock_wr.call_args[0][1]
        self.assertIn("id", emitted)

    @patch("tap_pepperjam.sync.singer.messages.write_record")
    def test_creative_advanced_primary_key_in_emitted_record(self, mock_wr):
        """Primary key 'id' is always present in emitted creative_advanced records."""
        catalog = _select_stream(discover(), "creative_advanced")
        record = self._generate_stream_record("creative_advanced",
                                              date_value="2024-06-01T00:00:00Z")
        time_extracted = utils.now()

        process_records(
            catalog=catalog,
            stream_name="creative_advanced",
            records=[record],
            time_extracted=time_extracted,
            bookmark_field="modified",
            max_bookmark_value=None,
            last_datetime=self.default_start_date,
        )

        self.assertEqual(mock_wr.call_count, 1)
        emitted = mock_wr.call_args[0][1]
        self.assertIn("id", emitted)

    @patch("tap_pepperjam.sync.singer.messages.write_record")
    def test_transaction_history_all_primary_keys_in_emitted_record(self, mock_wr):
        """All three primary keys are present in emitted transaction_history records."""
        catalog = _select_stream(discover(), "transaction_history")
        record = self._generate_stream_record("transaction_history",
                                              date_value="2024-06-01T00:00:00Z")
        time_extracted = utils.now()

        process_records(
            catalog=catalog,
            stream_name="transaction_history",
            records=[record],
            time_extracted=time_extracted,
            bookmark_field="sale_date",
            max_bookmark_value=None,
            last_datetime=self.default_start_date,
        )

        self.assertEqual(mock_wr.call_count, 1)
        emitted = mock_wr.call_args[0][1]
        for pk in {"transaction_id", "item_id", "revision"}:
            self.assertIn(pk, emitted,
                          msg=f"transaction_history PK '{pk}' missing from emitted record")

    # ── expected_metadata: completeness check ─────────────────────────────

    def test_every_stream_has_at_least_one_primary_key(self):
        """Every stream defined in expected_metadata has at least one primary key."""
        for stream_name, meta in self.expected_metadata().items():
            with self.subTest(stream=stream_name):
                self.assertGreater(
                    len(meta[self.PRIMARY_KEYS]), 0,
                    msg=f"Stream '{stream_name}' has no primary keys defined",
                )

    def test_incremental_streams_have_at_least_one_replication_key(self):
        """Every INCREMENTAL stream has at least one replication key defined."""
        for stream_name, meta in self.expected_metadata().items():
            if meta[self.REPLICATION_METHOD] == "INCREMENTAL":
                with self.subTest(stream=stream_name):
                    self.assertGreater(
                        len(meta[self.REPLICATION_KEYS]), 0,
                        msg=f"INCREMENTAL stream '{stream_name}' has no replication keys",
                    )

    def test_full_table_streams_have_no_replication_keys(self):
        """Every FULL_TABLE stream has an empty replication_keys set."""
        for stream_name, meta in self.expected_metadata().items():
            if meta[self.REPLICATION_METHOD] == "FULL_TABLE":
                with self.subTest(stream=stream_name):
                    self.assertEqual(
                        meta[self.REPLICATION_KEYS], set(),
                        msg=f"FULL_TABLE stream '{stream_name}' should have no replication keys",
                    )


if __name__ == "__main__":
    unittest.main()
