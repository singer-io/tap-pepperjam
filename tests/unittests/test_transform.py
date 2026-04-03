import unittest
from decimal import Decimal

from tap_pepperjam.transform import (
    string_to_decimal,
    est_to_utc_datetime,
    date_to_datetime,
    transform_json,
)


# ---------------------------------------------------------------------------
# string_to_decimal
# ---------------------------------------------------------------------------

class TestStringToDecimal(unittest.TestCase):
    def test_converts_string_to_decimal(self):
        """string_to_decimal converts a numeric string field to Decimal."""
        data = {"data": [{"price": "10.99"}]}
        result = string_to_decimal(data, "data", ["price"])
        self.assertEqual(result["data"][0]["price"], Decimal("10.99"))

    def test_strips_currency_symbols(self):
        """string_to_decimal strips non-numeric characters such as '$'."""
        data = {"data": [{"price": "$10.99"}]}
        result = string_to_decimal(data, "data", ["price"])
        self.assertEqual(result["data"][0]["price"], Decimal("10.99"))

    def test_skips_falsy_values(self):
        """string_to_decimal leaves falsy (empty) fields unchanged."""
        data = {"data": [{"price": ""}]}
        result = string_to_decimal(data, "data", ["price"])
        self.assertEqual(result["data"][0]["price"], "")

    def test_empty_number_fields_list_returns_unchanged(self):
        """string_to_decimal returns data unchanged when number_fields is empty."""
        data = {"data": [{"price": "10.99"}]}
        result = string_to_decimal(data, "data", [])
        self.assertEqual(result["data"][0]["price"], "10.99")

    def test_handles_multiple_records(self):
        """string_to_decimal processes all records in the data list."""
        data = {"data": [{"price": "1.00"}, {"price": "2.00"}]}
        result = string_to_decimal(data, "data", ["price"])
        self.assertEqual(result["data"][0]["price"], Decimal("1.00"))
        self.assertEqual(result["data"][1]["price"], Decimal("2.00"))

    def test_handles_multiple_number_fields(self):
        """string_to_decimal processes multiple number_fields per record."""
        data = {"data": [{"price": "5.00", "commission": "1.50"}]}
        result = string_to_decimal(data, "data", ["price", "commission"])
        self.assertEqual(result["data"][0]["price"], Decimal("5.00"))
        self.assertEqual(result["data"][0]["commission"], Decimal("1.50"))


# ---------------------------------------------------------------------------
# est_to_utc_datetime
# ---------------------------------------------------------------------------

class TestEstToUtcDatetime(unittest.TestCase):
    def test_converts_est_datetime_to_utc_string(self):
        """est_to_utc_datetime converts an EST datetime to a UTC ISO 8601 string."""
        data = {"data": [{"created": "2021-01-01 12:00:00"}]}
        result = est_to_utc_datetime(data, "data", ["created"])
        converted = result["data"][0]["created"]
        self.assertIsNotNone(converted)
        # 12:00 EST (UTC-5) = 17:00 UTC
        self.assertIn("2021-01-01", converted)

    def test_zero_datetime_becomes_none(self):
        """est_to_utc_datetime returns None for the sentinel '0000-00-00 00:00:00'."""
        data = {"data": [{"created": "0000-00-00 00:00:00"}]}
        result = est_to_utc_datetime(data, "data", ["created"])
        self.assertIsNone(result["data"][0]["created"])

    def test_none_field_left_unchanged(self):
        """est_to_utc_datetime leaves a None field as-is (falsy, no conversion)."""
        data = {"data": [{"created": None}]}
        result = est_to_utc_datetime(data, "data", ["created"])
        self.assertIsNone(result["data"][0]["created"])

    def test_invalid_datetime_string_becomes_none(self):
        """est_to_utc_datetime returns None for an unparseable datetime string."""
        data = {"data": [{"created": "not-a-date"}]}
        result = est_to_utc_datetime(data, "data", ["created"])
        self.assertIsNone(result["data"][0]["created"])

    def test_empty_datetime_fields_list_leaves_data_unchanged(self):
        """est_to_utc_datetime with an empty datetime_fields list returns data unchanged."""
        data = {"data": [{"created": "2021-01-01 12:00:00"}]}
        result = est_to_utc_datetime(data, "data", [])
        self.assertEqual(result["data"][0]["created"], "2021-01-01 12:00:00")

    def test_handles_multiple_datetime_fields(self):
        """est_to_utc_datetime processes multiple datetime_fields per record."""
        data = {"data": [{"start_date": "2021-03-01 08:00:00", "end_date": "2021-03-02 08:00:00"}]}
        result = est_to_utc_datetime(data, "data", ["start_date", "end_date"])
        self.assertIsNotNone(result["data"][0]["start_date"])
        self.assertIsNotNone(result["data"][0]["end_date"])


# ---------------------------------------------------------------------------
# date_to_datetime
# ---------------------------------------------------------------------------

class TestDateToDatetime(unittest.TestCase):
    def test_appends_datetime_field_from_date(self):
        """date_to_datetime adds a 'datetime' field with T00:00:00Z suffix."""
        data = {"data": [{"date": "2021-06-15"}]}
        result = date_to_datetime(data, "data")
        self.assertEqual(result["data"][0]["datetime"], "2021-06-15T00:00:00Z")

    def test_zero_date_becomes_none(self):
        """date_to_datetime sets 'datetime' to None for the sentinel '0000-00-00'."""
        data = {"data": [{"date": "0000-00-00"}]}
        result = date_to_datetime(data, "data")
        self.assertIsNone(result["data"][0]["datetime"])

    def test_missing_date_field_no_datetime_added(self):
        """date_to_datetime does not add 'datetime' when 'date' field is absent."""
        data = {"data": [{"id": "1"}]}
        result = date_to_datetime(data, "data")
        self.assertNotIn("datetime", result["data"][0])

    def test_handles_multiple_records(self):
        """date_to_datetime processes all records in the list."""
        data = {"data": [{"date": "2021-01-01"}, {"date": "2021-12-31"}]}
        result = date_to_datetime(data, "data")
        self.assertEqual(result["data"][0]["datetime"], "2021-01-01T00:00:00Z")
        self.assertEqual(result["data"][1]["datetime"], "2021-12-31T00:00:00Z")


# ---------------------------------------------------------------------------
# transform_json
# ---------------------------------------------------------------------------

class TestTransformJson(unittest.TestCase):
    def test_creative_advanced_converts_modified_datetime(self):
        """transform_json converts EST 'modified' field to UTC for creative_advanced."""
        data = {"data": [{"modified": "2021-01-01 10:00:00", "start_date": None,
                          "end_date": None, "view_date": None, "created": None}]}
        result = transform_json(data, "creative_advanced", "data")
        self.assertIsNotNone(result[0]["modified"])

    def test_creative_banner_converts_modified_datetime(self):
        """transform_json converts EST 'modified' field to UTC for creative_banner."""
        data = {"data": [{"modified": "2021-02-15 09:00:00", "start_date": None,
                          "end_date": None, "view_date": None, "created": None}]}
        result = transform_json(data, "creative_banner", "data")
        self.assertIsNotNone(result[0]["modified"])

    def test_creative_performance_adds_datetime_field(self):
        """transform_json adds a 'datetime' field for creative_performance."""
        data = {"data": [{"date": "2021-06-15", "click_through_rate": "1.5",
                          "sales": "100", "earnings_per_click": "0.5", "commission": "5"}]}
        result = transform_json(data, "creative_performance", "data")
        self.assertEqual(result[0]["datetime"], "2021-06-15T00:00:00Z")

    def test_creative_performance_converts_decimal_fields(self):
        """transform_json converts numeric string fields for creative_performance."""
        data = {"data": [{"date": "2021-06-15", "click_through_rate": "1.50",
                          "sales": "200", "earnings_per_click": "0.75", "commission": "10"}]}
        result = transform_json(data, "creative_performance", "data")
        self.assertEqual(result[0]["click_through_rate"], Decimal("1.50"))

    def test_publisher_performance_adds_datetime_field(self):
        """transform_json adds a 'datetime' field for publisher_performance."""
        data = {"data": [{"date": "2021-08-01", "sale_lead_amount": "10",
                          "earnings_per_click": "0.5", "bonus_amount": "0",
                          "total_commission": "50", "site_bonus": "0",
                          "site_commission": "25", "publisher_bonus": "0",
                          "publisher_commission": "25"}]}
        result = transform_json(data, "publisher_performance", "data")
        self.assertEqual(result[0]["datetime"], "2021-08-01T00:00:00Z")

    def test_creative_product_converts_price_to_decimal(self):
        """transform_json converts price fields to Decimal for creative_product."""
        data = {"data": [{"price": "9.99", "price_retail": "12.99",
                          "price_sale": "8.99", "price_shipping": "2.99"}]}
        result = transform_json(data, "creative_product", "data")
        self.assertEqual(result[0]["price"], Decimal("9.99"))
        self.assertEqual(result[0]["price_retail"], Decimal("12.99"))

    def test_transaction_details_converts_sale_amount(self):
        """transform_json converts 'sale_amount' to Decimal for transaction_details."""
        data = {"data": [{"sale_date": "2021-03-01 09:00:00", "sale_amount": "150.00",
                          "commission": "5.00", "commission_publisher": "2.50",
                          "commission_site": "2.50"}]}
        result = transform_json(data, "transaction_details", "data")
        self.assertEqual(result[0]["sale_amount"], Decimal("150.00"))

    def test_transaction_history_converts_commission_and_datetime(self):
        """transform_json handles both Decimal and datetime conversions for transaction_history."""
        data = {"data": [{"commission": "5.00", "sale_date": "2021-03-01 09:00:00",
                          "process_date": None, "publisher_commission": "2.00",
                          "site_commission": "1.50", "sale_amount": "100.00"}]}
        result = transform_json(data, "transaction_history", "data")
        self.assertEqual(result[0]["commission"], Decimal("5.00"))
        self.assertIsNotNone(result[0]["sale_date"])

    def test_unknown_stream_returns_data_unchanged(self):
        """transform_json returns records unchanged for an unrecognised stream name."""
        data = {"data": [{"id": "1", "name": "test"}]}
        result = transform_json(data, "unknown_stream", "data")
        self.assertEqual(result[0]["id"], "1")
        self.assertEqual(result[0]["name"], "test")

    def test_creative_generic_converts_modified(self):
        """transform_json converts 'modified' EST datetime for creative_generic."""
        data = {"data": [{"modified": "2021-05-10 14:00:00"}]}
        result = transform_json(data, "creative_generic", "data")
        self.assertIsNotNone(result[0]["modified"])

    def test_returns_list(self):
        """transform_json always returns a list of records."""
        data = {"data": [{"id": "1"}]}
        result = transform_json(data, "unknown_stream", "data")
        self.assertIsInstance(result, list)


if __name__ == "__main__":
    unittest.main()
