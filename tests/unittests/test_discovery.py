import unittest
from singer.catalog import Catalog, CatalogEntry

from tap_pepperjam.streams import flatten_streams, STREAMS
from tap_pepperjam.schema import get_schemas
from tap_pepperjam.discover import discover


# ---------------------------------------------------------------------------
# flatten_streams
# ---------------------------------------------------------------------------

class TestFlattenStreams(unittest.TestCase):
    def test_all_parent_streams_included(self):
        """flatten_streams includes every top-level stream key from STREAMS."""
        flat = flatten_streams()
        for stream_name in STREAMS:
            self.assertIn(stream_name, flat)

    def test_child_group_member_included(self):
        """flatten_streams includes the 'group_member' child stream."""
        flat = flatten_streams()
        self.assertIn("group_member", flat)

    def test_child_itemized_list_product_included(self):
        """flatten_streams includes the 'itemized_list_product' child stream."""
        flat = flatten_streams()
        self.assertIn("itemized_list_product", flat)

    def test_returns_dict(self):
        """flatten_streams returns a dictionary."""
        self.assertIsInstance(flatten_streams(), dict)

    def test_incremental_stream_key_properties(self):
        """flatten_streams preserves key_properties for an incremental stream."""
        flat = flatten_streams()
        self.assertEqual(flat["creative_advanced"]["key_properties"], ["id"])

    def test_incremental_stream_replication_method(self):
        """flatten_streams preserves replication_method for an incremental stream."""
        flat = flatten_streams()
        self.assertEqual(flat["creative_advanced"]["replication_method"], "INCREMENTAL")

    def test_incremental_stream_replication_keys(self):
        """flatten_streams preserves replication_keys for an incremental stream."""
        flat = flatten_streams()
        self.assertEqual(flat["creative_advanced"]["replication_keys"], ["modified"])

    def test_full_table_stream_no_replication_keys(self):
        """flatten_streams has None replication_keys for FULL_TABLE streams."""
        flat = flatten_streams()
        self.assertIsNone(flat["publisher"]["replication_keys"])

    def test_child_key_properties_correct(self):
        """flatten_streams preserves key_properties for 'itemized_list_product'."""
        flat = flatten_streams()
        self.assertEqual(flat["itemized_list_product"]["key_properties"], ["id", "list_id"])

    def test_transaction_history_replication_keys(self):
        """flatten_streams has the correct replication_keys for transaction_history."""
        flat = flatten_streams()
        self.assertEqual(flat["transaction_history"]["replication_keys"], ["sale_date"])


# ---------------------------------------------------------------------------
# get_schemas
# ---------------------------------------------------------------------------

class TestGetSchemas(unittest.TestCase):
    def setUp(self):
        self.schemas, self.field_metadata = get_schemas()
        self.flat = flatten_streams()

    def test_schema_returned_for_every_flat_stream(self):
        """get_schemas includes a schema for every stream in flatten_streams."""
        for stream_name in self.flat:
            self.assertIn(stream_name, self.schemas, msg=f"Missing schema for {stream_name}")

    def test_field_metadata_returned_for_every_flat_stream(self):
        """get_schemas includes metadata for every stream in flatten_streams."""
        for stream_name in self.flat:
            self.assertIn(stream_name, self.field_metadata, msg=f"Missing metadata for {stream_name}")

    def test_each_schema_is_a_dict(self):
        """get_schemas returns each schema as a dict."""
        for stream_name, schema in self.schemas.items():
            self.assertIsInstance(schema, dict, msg=f"Schema for {stream_name} is not a dict")

    def test_each_schema_has_properties(self):
        """get_schemas returns schemas with a 'properties' key."""
        for stream_name, schema in self.schemas.items():
            self.assertIn("properties", schema, msg=f"Stream {stream_name} missing 'properties'")

    def test_schemas_is_dict(self):
        """get_schemas first return value is a dict."""
        self.assertIsInstance(self.schemas, dict)

    def test_field_metadata_is_list(self):
        """get_schemas metadata value for each stream is a list."""
        for stream_name, mdata in self.field_metadata.items():
            self.assertIsInstance(mdata, list, msg=f"Metadata for {stream_name} is not a list")


# ---------------------------------------------------------------------------
# discover
# ---------------------------------------------------------------------------

class TestDiscover(unittest.TestCase):
    def setUp(self):
        self.catalog = discover()
        self.flat = flatten_streams()

    def test_returns_catalog_instance(self):
        """discover() returns a Singer Catalog instance."""
        self.assertIsInstance(self.catalog, Catalog)

    def test_catalog_contains_all_flat_streams(self):
        """discover() includes a CatalogEntry for every stream in flatten_streams."""
        stream_names = {entry.stream for entry in self.catalog.streams}
        for stream_name in self.flat:
            self.assertIn(stream_name, stream_names)

    def test_all_entries_are_catalog_entry_instances(self):
        """discover() catalog entries are CatalogEntry objects."""
        for entry in self.catalog.streams:
            self.assertIsInstance(entry, CatalogEntry)

    def test_group_stream_key_properties(self):
        """discover() 'group' CatalogEntry has key_properties=['id']."""
        entry = next(e for e in self.catalog.streams if e.stream == "group")
        self.assertEqual(entry.key_properties, ["id"])

    def test_transaction_history_key_properties(self):
        """discover() 'transaction_history' entry has all three key_properties."""
        entry = next(e for e in self.catalog.streams if e.stream == "transaction_history")
        self.assertEqual(entry.key_properties, ["transaction_id", "item_id", "revision"])

    def test_tap_stream_id_matches_stream_name(self):
        """discover() sets tap_stream_id equal to stream name for every entry."""
        for entry in self.catalog.streams:
            self.assertEqual(entry.tap_stream_id, entry.stream)

    def test_creative_performance_key_properties(self):
        """discover() 'creative_performance' has correct composite key_properties."""
        entry = next(e for e in self.catalog.streams if e.stream == "creative_performance")
        self.assertEqual(entry.key_properties, ["creative_id", "creative_type", "date"])

    def test_publisher_performance_key_properties(self):
        """discover() 'publisher_performance' has correct composite key_properties."""
        entry = next(e for e in self.catalog.streams if e.stream == "publisher_performance")
        self.assertEqual(entry.key_properties, ["publisher_id", "date"])


if __name__ == "__main__":
    unittest.main()
