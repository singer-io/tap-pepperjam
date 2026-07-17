import unittest
from unittest.mock import MagicMock, patch
from singer.catalog import Catalog, CatalogEntry

from tap_pepperjam.client import PepperjamForbiddenError
from tap_pepperjam.streams import flatten_streams, STREAMS
from tap_pepperjam.schema import get_schemas
from tap_pepperjam.discover import discover, _apply_access_checks, _stream_is_accessible


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
        self.catalog = discover(MagicMock())
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


class TestDiscoveryAccessChecks(unittest.TestCase):
    @patch("tap_pepperjam.discover.LOGGER.warning")
    def test_stream_is_accessible_logs_unauthorized_stream_message_on_403(self, mock_warning):
        """_stream_is_accessible logs exact unauthorized-stream warning when API returns 403."""
        client = MagicMock()
        client.get.side_effect = PepperjamForbiddenError("403: Forbidden")

        result = _stream_is_accessible(client, "group", {"parent_stream": None})

        self.assertFalse(result)
        mock_warning.assert_called_once_with(
            "Unauthorized stream excluded from catalog: %s. HTTP error: %s",
            "group",
            client.get.side_effect,
        )

    @patch("tap_pepperjam.discover._stream_is_accessible", return_value=True)
    def test_apply_access_checks_keeps_all_streams_when_accessible(self, _mock_access):
        """No streams are removed when all stream probes are accessible."""
        schemas, field_metadata = get_schemas()
        original_names = set(schemas.keys())

        _apply_access_checks(MagicMock(), schemas, field_metadata)

        self.assertEqual(set(schemas.keys()), original_names)
        self.assertEqual(set(field_metadata.keys()), original_names)

    @patch("tap_pepperjam.discover._stream_is_accessible")
    def test_apply_access_checks_removes_inaccessible_parent_and_children(self, mock_access):
        """Inaccessible parent streams are removed and their children are pruned."""
        def access_side_effect(_client, stream_name, stream_metadata):
            if stream_name == "group":
                return False
            if stream_metadata.get("parent_stream"):
                return True
            return True

        mock_access.side_effect = access_side_effect

        schemas, field_metadata = get_schemas()
        self.assertIn("group", schemas)
        self.assertIn("group_member", schemas)

        _apply_access_checks(MagicMock(), schemas, field_metadata)

        self.assertNotIn("group", schemas)
        self.assertNotIn("group_member", schemas)
        self.assertNotIn("group", field_metadata)
        self.assertNotIn("group_member", field_metadata)

    @patch("tap_pepperjam.discover._stream_is_accessible", return_value=False)
    def test_apply_access_checks_raises_when_no_streams_accessible(self, _mock_access):
        """Discovery raises PepperjamForbiddenError when no streams are accessible."""
        schemas, field_metadata = get_schemas()

        with self.assertRaises(PepperjamForbiddenError):
            _apply_access_checks(MagicMock(), schemas, field_metadata)

    @patch("tap_pepperjam.discover._stream_is_accessible", return_value=False)
    def test_apply_access_checks_raises_with_expected_message_when_no_streams_accessible(self, _mock_access):
        """No-access failure includes the exact guidance message."""
        schemas, field_metadata = get_schemas()

        with self.assertRaises(PepperjamForbiddenError) as err:
            _apply_access_checks(MagicMock(), schemas, field_metadata)

        self.assertEqual(
            str(err.exception),
            "No streams are accessible. Ensure credentials have read permission for at least one stream.",
        )

    @patch("tap_pepperjam.discover.LOGGER.warning")
    @patch("tap_pepperjam.discover._stream_is_accessible")
    def test_apply_access_checks_logs_unauthorized_streams_excluded_message(self, mock_access, mock_warning):
        """Partial access logs the combined unauthorized-streams exclusion message."""
        def access_side_effect(_client, stream_name, stream_metadata):
            if stream_metadata.get("parent_stream"):
                return True
            return stream_name != "group"

        mock_access.side_effect = access_side_effect
        schemas, field_metadata = get_schemas()

        _apply_access_checks(MagicMock(), schemas, field_metadata)

        mock_warning.assert_any_call(
            "Unauthorized streams have been excluded: %s",
            "group, group_member",
        )

    @patch("tap_pepperjam.discover._apply_access_checks")
    def test_discover_calls_access_checks_when_client_provided(self, mock_apply):
        """discover(client=...) applies access checks before catalog generation."""
        client = MagicMock()
        discover(client=client)
        mock_apply.assert_called_once()

    @patch("tap_pepperjam.discover._apply_access_checks")
    def test_discover_skips_access_checks_without_client(self, mock_apply):
        """discover() without a client preserves schema-only behavior for tests."""
        discover(MagicMock())
        mock_apply.assert_called_once()


if __name__ == "__main__":
    unittest.main()
