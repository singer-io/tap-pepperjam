"""Integration tests for tap-pepperjam stream discovery with mocked data.

Calls the tap's own discover() function directly — no HTTP calls needed
because discovery only reads local JSON schema files.
"""
import unittest
from singer import metadata

try:
    from base import PepperjamBaseTest
except ImportError:
    from tests.base import PepperjamBaseTest

from tap_pepperjam.discover import discover
from tap_pepperjam.streams import flatten_streams


class PepperjamDiscoveryTest(PepperjamBaseTest, unittest.TestCase):
    """Verify tap-pepperjam discovery returns the expected catalog structure."""

    def setUp(self):
        super().setUp()
        # discover() reads only local JSON files — no HTTP, no credentials needed
        self.catalog = discover()
        self.discovered_streams = {e.stream: e for e in self.catalog.streams}

    # ── Completeness ─────────────────────────────────────────────────────────

    def test_discovery_returns_all_expected_streams(self):
        """discover() returns a catalog entry for every stream in expected_metadata."""
        expected = self.expected_stream_names()
        actual = set(self.discovered_streams.keys())
        self.assertEqual(actual, expected)

    def test_discovery_returns_no_unexpected_streams(self):
        """discover() does not return streams that are not in expected_metadata."""
        expected = self.expected_stream_names()
        for stream_name in self.discovered_streams:
            self.assertIn(stream_name, expected,
                          msg=f"Unexpected stream discovered: {stream_name}")

    # ── Schema structure ──────────────────────────────────────────────────────

    def test_every_stream_schema_has_properties(self):
        """Every discovered stream schema contains a 'properties' key."""
        for stream_name, entry in self.discovered_streams.items():
            with self.subTest(stream=stream_name):
                schema_dict = entry.schema.to_dict()
                self.assertIn("properties", schema_dict)

    def test_every_stream_schema_has_at_least_one_property(self):
        """Every stream schema has at least one property defined."""
        for stream_name, entry in self.discovered_streams.items():
            with self.subTest(stream=stream_name):
                props = entry.schema.to_dict().get("properties", {})
                self.assertGreater(len(props), 0,
                                   msg=f"Stream {stream_name} has no properties in schema")

    # ── Primary keys ─────────────────────────────────────────────────────────

    def test_primary_keys_match_expected_for_all_streams(self):
        """key_properties match expected primary keys for every stream."""
        expected_meta = self.expected_metadata()
        for stream_name, entry in self.discovered_streams.items():
            with self.subTest(stream=stream_name):
                expected_pks = expected_meta[stream_name][self.PRIMARY_KEYS]
                actual_pks = set(entry.key_properties or [])
                self.assertEqual(actual_pks, expected_pks)

    def test_tap_stream_id_equals_stream_name(self):
        """tap_stream_id is identical to the stream name for every catalog entry."""
        for stream_name, entry in self.discovered_streams.items():
            with self.subTest(stream=stream_name):
                self.assertEqual(entry.tap_stream_id, stream_name)

    # ── Metadata: replication ─────────────────────────────────────────────────

    def test_incremental_streams_have_replication_method_in_metadata(self):
        """INCREMENTAL streams expose 'forced-replication-method' = INCREMENTAL in metadata."""
        for stream_name in self.incremental_streams():
            with self.subTest(stream=stream_name):
                entry = self.discovered_streams[stream_name]
                mdata = metadata.to_map(entry.metadata)
                rep_method = metadata.get(mdata, (), "forced-replication-method")
                self.assertEqual(rep_method, "INCREMENTAL")

    def test_full_table_streams_have_replication_method_in_metadata(self):
        """FULL_TABLE streams expose 'forced-replication-method' = FULL_TABLE in metadata."""
        for stream_name in self.full_table_streams():
            with self.subTest(stream=stream_name):
                entry = self.discovered_streams[stream_name]
                mdata = metadata.to_map(entry.metadata)
                rep_method = metadata.get(mdata, (), "forced-replication-method")
                self.assertEqual(rep_method, "FULL_TABLE")

    def test_incremental_streams_have_valid_replication_keys(self):
        """INCREMENTAL streams expose valid-replication-keys in stream-level metadata."""
        expected_meta = self.expected_metadata()
        for stream_name in self.incremental_streams():
            with self.subTest(stream=stream_name):
                entry = self.discovered_streams[stream_name]
                mdata = metadata.to_map(entry.metadata)
                valid_keys = set(metadata.get(mdata, (), "valid-replication-keys") or [])
                expected_keys = expected_meta[stream_name][self.REPLICATION_KEYS]
                self.assertEqual(valid_keys, expected_keys)

    def test_full_table_streams_have_no_valid_replication_keys(self):
        """FULL_TABLE streams have no valid-replication-keys in metadata."""
        for stream_name in self.full_table_streams():
            with self.subTest(stream=stream_name):
                entry = self.discovered_streams[stream_name]
                mdata = metadata.to_map(entry.metadata)
                valid_keys = metadata.get(mdata, (), "valid-replication-keys")
                self.assertFalse(valid_keys,
                                 msg=f"FULL_TABLE stream {stream_name} should have no replication keys")

    # ── Parent/child stream metadata ──────────────────────────────────────────

    def test_group_member_primary_keys(self):
        """'group_member' child stream has correct primary key."""
        entry = self.discovered_streams["group_member"]
        self.assertIn("id", entry.key_properties)

    def test_itemized_list_product_primary_keys(self):
        """'itemized_list_product' child stream has composite primary key."""
        entry = self.discovered_streams["itemized_list_product"]
        self.assertEqual(set(entry.key_properties), {"id", "list_id"})

    # ── Specific stream spot-checks ──────────────────────────────────────────

    def test_transaction_history_has_three_key_properties(self):
        """'transaction_history' key_properties includes transaction_id, item_id, revision."""
        entry = self.discovered_streams["transaction_history"]
        self.assertEqual(set(entry.key_properties),
                         {"transaction_id", "item_id", "revision"})

    def test_creative_performance_has_correct_primary_keys(self):
        """'creative_performance' key_properties includes creative_id, creative_type, date."""
        entry = self.discovered_streams["creative_performance"]
        self.assertEqual(set(entry.key_properties),
                         {"creative_id", "creative_type", "date"})

    def test_publisher_performance_has_datetime_replication_key(self):
        """'publisher_performance' reports 'datetime' as its valid-replication-key."""
        entry = self.discovered_streams["publisher_performance"]
        mdata = metadata.to_map(entry.metadata)
        valid_keys = set(metadata.get(mdata, (), "valid-replication-keys") or [])
        self.assertIn("datetime", valid_keys)

    def test_flatten_streams_matches_expected_stream_names(self):
        """flatten_streams() produces the same set of stream names as expected_metadata."""
        flat = set(flatten_streams().keys())
        self.assertEqual(flat, self.expected_stream_names())


if __name__ == "__main__":
    unittest.main()
