"""Base class and shared utilities for tap-pepperjam mock integration tests.

Mock mode: pure unittest — no real credentials, no tap-tester dependency.
HTTP calls are mocked by passing a MagicMock client to the tap's sync functions.
"""
import json
import os


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FULL_TABLE = "FULL_TABLE"
INCREMENTAL = "INCREMENTAL"
API_LIMIT = 500  # limit constant in sync.py (line: limit = 500)


# ---------------------------------------------------------------------------
# MockResponse — minimal requests.Response stand-in (used by test_client tests)
# ---------------------------------------------------------------------------

class MockResponse:
    """Minimal requests.Response stand-in."""

    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            err = requests.exceptions.HTTPError(f"HTTP {self.status_code}")
            err.response = self
            raise err


# ---------------------------------------------------------------------------
# Helpers to build API response envelopes matching the Pepperjam API shape
# ---------------------------------------------------------------------------

def make_api_response(records, next_href=None):
    """Build a dict matching Pepperjam's paginated API response shape."""
    pagination = {"total_results": len(records)}
    if next_href:
        pagination["next"] = {"rel": "next", "href": next_href}
    return {"data": records, "meta": {"pagination": pagination}}


def make_mock_client(responses):
    """Return a MagicMock PepperjamClient whose .get() returns items from *responses*.

    *responses* is an iterable; each call to client.get() pops the next item.
    """
    from unittest.mock import MagicMock
    client = MagicMock()
    client.base_url = "https://api.pepperjamnetwork.com/20120402/advertiser"
    client.get.side_effect = list(responses)
    return client


# ---------------------------------------------------------------------------
# PepperjamBaseTest — mixin (not a TestCase)
# ---------------------------------------------------------------------------

class PepperjamBaseTest:
    """Base test mixin for tap-pepperjam integration tests with mocked data.

    Not a TestCase itself — mix with unittest.TestCase in each test class.
    """

    # ── Metadata constants (mirrors tap_tester.base_suite_tests.base_case) ──
    PRIMARY_KEYS = "primary_keys"
    REPLICATION_METHOD = "replication_method"
    REPLICATION_KEYS = "replication_keys"
    OBEYS_START_DATE = "obeys_start_date"
    API_LIMIT_KEY = "api_limit"
    PARENT = "parent"

    default_start_date = "2020-01-01T00:00:00Z"

    # ── Mock config — dummy values, no os.getenv() ──────────────────────────

    @staticmethod
    def get_mock_config():
        """Return mock configuration with dummy values — no real credentials."""
        return {
            "api_key": "mock_pepperjam_api_key_12345",
            "user_agent": "tap-pepperjam <mock@example.com>",
            "start_date": "2020-01-01T00:00:00Z",
            "date_window_days": "30",
            "lock_period_days": "60",
        }

    @staticmethod
    def get_mock_state():
        """Return initial mock state."""
        return {}

    # ── Stream metadata table ────────────────────────────────────────────────

    @classmethod
    def expected_metadata(cls):
        """The expected streams and metadata about the streams."""
        return {
            "creative_advanced": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: INCREMENTAL,
                cls.REPLICATION_KEYS: {"modified"},
                cls.OBEYS_START_DATE: True,
                cls.API_LIMIT_KEY: API_LIMIT,
            },
            "creative_banner": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: INCREMENTAL,
                cls.REPLICATION_KEYS: {"modified"},
                cls.OBEYS_START_DATE: True,
                cls.API_LIMIT_KEY: API_LIMIT,
            },
            "creative_coupon": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: INCREMENTAL,
                cls.REPLICATION_KEYS: {"modified"},
                cls.OBEYS_START_DATE: True,
                cls.API_LIMIT_KEY: API_LIMIT,
            },
            "creative_generic": {
                cls.PRIMARY_KEYS: {"type"},
                cls.REPLICATION_METHOD: INCREMENTAL,
                cls.REPLICATION_KEYS: {"modified"},
                cls.OBEYS_START_DATE: True,
                cls.API_LIMIT_KEY: API_LIMIT,
            },
            "creative_product": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.OBEYS_START_DATE: False,
                cls.API_LIMIT_KEY: API_LIMIT,
            },
            "creative_promotion": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.OBEYS_START_DATE: False,
                cls.API_LIMIT_KEY: API_LIMIT,
            },
            "creative_text": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: INCREMENTAL,
                cls.REPLICATION_KEYS: {"modified"},
                cls.OBEYS_START_DATE: True,
                cls.API_LIMIT_KEY: API_LIMIT,
            },
            "group": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.OBEYS_START_DATE: False,
                cls.API_LIMIT_KEY: API_LIMIT,
            },
            "group_member": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.OBEYS_START_DATE: False,
                cls.API_LIMIT_KEY: API_LIMIT,
                cls.PARENT: "group",
            },
            "itemized_list": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.OBEYS_START_DATE: False,
                cls.API_LIMIT_KEY: API_LIMIT,
            },
            "itemized_list_product": {
                cls.PRIMARY_KEYS: {"id", "list_id"},
                cls.REPLICATION_METHOD: FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.OBEYS_START_DATE: False,
                cls.API_LIMIT_KEY: API_LIMIT,
                cls.PARENT: "itemized_list",
            },
            "publisher": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.OBEYS_START_DATE: False,
                cls.API_LIMIT_KEY: API_LIMIT,
            },
            "term": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.OBEYS_START_DATE: False,
                cls.API_LIMIT_KEY: API_LIMIT,
            },
            "creative_performance": {
                cls.PRIMARY_KEYS: {"creative_id", "creative_type", "date"},
                cls.REPLICATION_METHOD: INCREMENTAL,
                cls.REPLICATION_KEYS: {"datetime"},
                cls.OBEYS_START_DATE: True,
                cls.API_LIMIT_KEY: API_LIMIT,
            },
            "creative_performance_by_publisher": {
                cls.PRIMARY_KEYS: {"creative_id", "creative_type", "publisher_id", "date"},
                cls.REPLICATION_METHOD: INCREMENTAL,
                cls.REPLICATION_KEYS: {"datetime"},
                cls.OBEYS_START_DATE: True,
                cls.API_LIMIT_KEY: API_LIMIT,
            },
            "publisher_performance": {
                cls.PRIMARY_KEYS: {"publisher_id", "date"},
                cls.REPLICATION_METHOD: INCREMENTAL,
                cls.REPLICATION_KEYS: {"datetime"},
                cls.OBEYS_START_DATE: True,
                cls.API_LIMIT_KEY: API_LIMIT,
            },
            "transaction_details": {
                cls.PRIMARY_KEYS: {"transaction_id"},
                cls.REPLICATION_METHOD: INCREMENTAL,
                cls.REPLICATION_KEYS: {"sale_date"},
                cls.OBEYS_START_DATE: True,
                cls.API_LIMIT_KEY: API_LIMIT,
            },
            "transaction_history": {
                cls.PRIMARY_KEYS: {"transaction_id", "item_id", "revision"},
                cls.REPLICATION_METHOD: INCREMENTAL,
                cls.REPLICATION_KEYS: {"sale_date"},
                cls.OBEYS_START_DATE: True,
                cls.API_LIMIT_KEY: API_LIMIT,
            },
        }

    @classmethod
    def expected_stream_names(cls):
        """Return the set of all expected stream names."""
        return set(cls.expected_metadata().keys())

    @classmethod
    def incremental_streams(cls):
        """Return stream names that use INCREMENTAL replication."""
        return {
            name for name, meta in cls.expected_metadata().items()
            if meta[cls.REPLICATION_METHOD] == INCREMENTAL
        }

    @classmethod
    def full_table_streams(cls):
        """Return stream names that use FULL_TABLE replication."""
        return {
            name for name, meta in cls.expected_metadata().items()
            if meta[cls.REPLICATION_METHOD] == FULL_TABLE
        }

    @classmethod
    def child_streams(cls):
        """Return stream names that have a parent stream."""
        return {
            name for name, meta in cls.expected_metadata().items()
            if cls.PARENT in meta
        }

    # ── Schema-driven mock data generation ──────────────────────────────────

    @staticmethod
    def _schema_path(stream_name):
        base_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        return os.path.join(base_dir, "tap_pepperjam", "schemas",
                            f"{stream_name}.json")

    @classmethod
    def _load_schema(cls, stream_name):
        with open(cls._schema_path(stream_name), "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _schema_type(schema):
        """Return a concrete type string, resolving null unions."""
        t = schema.get("type", "object")
        if isinstance(t, list):
            non_null = [x for x in t if x != "null"]
            return non_null[0] if non_null else "null"
        return t

    @staticmethod
    def _generate_value(schema, date_value="2024-01-15T12:00:00Z"):
        """Recursively generate one valid mock value for a JSON-schema fragment."""
        if "enum" in schema and schema["enum"]:
            return schema["enum"][0]

        # anyOf / oneOf / allOf — return None (satisfies the null branch)
        if "anyOf" in schema or "oneOf" in schema:
            return None

        schema_type = PepperjamBaseTest._schema_type(schema)
        if schema_type == "object":
            properties = schema.get("properties", {})
            return {
                key: PepperjamBaseTest._generate_value(val, date_value)
                for key, val in properties.items()
            }
        if schema_type == "array":
            return [PepperjamBaseTest._generate_value(
                schema.get("items", {"type": "string"}), date_value)]
        if schema_type == "string":
            fmt = schema.get("format")
            if fmt == "date-time":
                return date_value
            if fmt == "email":
                return "mock@example.com"
            return "mock_value"
        return {"integer": 1, "number": 1.0, "boolean": True}.get(schema_type)

    @classmethod
    def _generate_stream_record(cls, stream_name, date_value="2024-01-15T12:00:00Z"):
        """Generate one schema-valid mock record for the given stream."""
        return cls._generate_value(cls._load_schema(stream_name),
                                   date_value=date_value)

    # ── setUp / tearDown ─────────────────────────────────────────────────────

    def setUp(self):
        self.config = self.get_mock_config()
        self.state = {}
