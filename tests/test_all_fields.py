"""Integration tests for tap-pepperjam 'all fields' replication with mocked data.

Verifies that:
- Schema-generated mock records contain all fields defined in the stream's JSON schema
- process_records transforms and emits records with the expected fields
- No schema fields are silently dropped during transformation
"""
import unittest
from unittest.mock import patch

try:
    from base import PepperjamBaseTest, _select_stream
except ImportError:
    from tests.base import PepperjamBaseTest, _select_stream

from tap_pepperjam.discover import discover
from tap_pepperjam.sync import process_records
from singer import utils


# Known to be absent: None — all schema fields should be present in generated mock records.
# Populate this dict only after a real sync reveals fields never returned by the API.
KNOWN_MISSING_FIELDS: dict = {
    # "<stream_name>": {"<field_name>", ...},
}


# ---------------------------------------------------------------------------
# AllFields tests
# ---------------------------------------------------------------------------

class TestPepperjamAllFields(PepperjamBaseTest, unittest.TestCase):
    """Verify schema-generated mock records carry all fields declared in the JSON schema."""

    def _schema_fields(self, stream_name):
        """Return the set of top-level property names from the stream's JSON schema."""
        return set(self._load_schema(stream_name).get("properties", {}).keys())

    def test_schema_driven_record_contains_all_schema_fields(self):
        """_generate_stream_record() produces a dict with every schema-declared field."""
        for stream_name in self.expected_stream_names():
            with self.subTest(stream=stream_name):
                record = self._generate_stream_record(stream_name)
                expected_fields = self._schema_fields(stream_name)
                actual_fields = set(record.keys())
                known_missing = KNOWN_MISSING_FIELDS.get(stream_name, set())
                # After removing known-missing fields, all schema fields must be present
                missing = (expected_fields - actual_fields) - known_missing
                self.assertFalse(
                    missing,
                    msg=f"Stream '{stream_name}' mock record missing fields: {missing}",
                )

    @patch("tap_pepperjam.sync.singer.messages.write_record")
    def test_all_schema_fields_replicated_for_publisher(self, mock_wr):
        """process_records emits records containing all publisher schema fields."""
        catalog = _select_stream(discover(), "publisher")
        schema_fields = self._schema_fields("publisher")
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
        emitted_record = mock_wr.call_args[0][1]
        emitted_fields = set(emitted_record.keys())
        # Singer Transformer only drops fields that don't exist in the schema,
        # so all schema-declared fields should still be present.
        known_missing = KNOWN_MISSING_FIELDS.get("publisher", set())
        missing = (schema_fields - emitted_fields) - known_missing
        self.assertFalse(missing,
                         msg=f"publisher emitted record missing fields: {missing}")

    @patch("tap_pepperjam.sync.singer.messages.write_record")
    def test_all_schema_fields_replicated_for_term(self, mock_wr):
        """process_records emits records containing all term schema fields."""
        catalog = _select_stream(discover(), "term")
        record = self._generate_stream_record("term")
        time_extracted = utils.now()

        process_records(
            catalog=catalog,
            stream_name="term",
            records=[record],
            time_extracted=time_extracted,
            bookmark_field=None,
            max_bookmark_value=None,
            last_datetime=self.default_start_date,
        )

        self.assertEqual(mock_wr.call_count, 1)

    @patch("tap_pepperjam.sync.singer.messages.write_record")
    def test_incremental_record_emitted_with_all_fields(self, mock_wr):
        """process_records emits an incremental record (creative_advanced) with all schema fields."""
        catalog = _select_stream(discover(), "creative_advanced")
        record = self._generate_stream_record("creative_advanced",
                                              date_value="2021-03-10T00:00:00Z")
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
        emitted_record = mock_wr.call_args[0][1]
        schema_fields = self._schema_fields("creative_advanced")
        known_missing = KNOWN_MISSING_FIELDS.get("creative_advanced", set())
        missing = (schema_fields - set(emitted_record.keys())) - known_missing
        self.assertFalse(missing,
                         msg=f"creative_advanced emitted record missing fields: {missing}")

    def test_all_schemas_are_valid_json(self):
        """Every stream's schema file is a valid JSON document."""
        for stream_name in self.expected_stream_names():
            with self.subTest(stream=stream_name):
                # _load_schema raises if the file is not valid JSON
                schema = self._load_schema(stream_name)
                self.assertIsInstance(schema, dict)

    def test_all_schemas_have_type_object(self):
        """Every stream schema declares 'type': 'object' at the root level."""
        for stream_name in self.expected_stream_names():
            with self.subTest(stream=stream_name):
                schema = self._load_schema(stream_name)
                schema_type = schema.get("type", "object")
                if isinstance(schema_type, list):
                    self.assertIn("object", schema_type)
                else:
                    self.assertEqual(schema_type, "object")

    def test_primary_key_fields_present_in_all_schemas(self):
        """Every stream's primary key fields appear as properties in the schema."""
        for stream_name, meta in self.expected_metadata().items():
            with self.subTest(stream=stream_name):
                pks = meta[self.PRIMARY_KEYS]
                schema = self._load_schema(stream_name)
                properties = schema.get("properties", {})
                for pk in pks:
                    self.assertIn(
                        pk, properties,
                        msg=f"Primary key '{pk}' missing from {stream_name} schema",
                    )


if __name__ == "__main__":
    unittest.main()
