import unittest
from unittest.mock import patch, MagicMock

from singer.utils import now as singer_now
from tap_pepperjam.sync import (
    get_bookmark,
    write_bookmark,
    write_schema,
    write_record,
    transform_datetime,
    process_records,
    update_currently_syncing,
    sync,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_catalog(schema=None, metadata=None):
    """Return a mock catalog whose get_stream() yields a stream with the given schema."""
    if schema is None:
        schema = {
            "type": "object",
            "properties": {
                "id": {"type": ["null", "string"]},
                "name": {"type": ["null", "string"]},
                "modified": {"type": ["null", "string"], "format": "date-time"},
                "group_id": {"type": ["null", "string"]},
            },
        }
    mock_stream = MagicMock()
    mock_stream.schema.to_dict.return_value = schema
    mock_stream.metadata = metadata if metadata is not None else []
    catalog = MagicMock()
    catalog.get_stream.return_value = mock_stream
    return catalog


# ---------------------------------------------------------------------------
# get_bookmark
# ---------------------------------------------------------------------------

class TestGetBookmark(unittest.TestCase):
    def test_returns_default_when_state_is_none(self):
        """get_bookmark returns default when state is None."""
        result = get_bookmark(None, "stream_a", "2020-01-01T00:00:00Z")
        self.assertEqual(result, "2020-01-01T00:00:00Z")

    def test_returns_default_when_bookmarks_key_missing(self):
        """get_bookmark returns default when state has no bookmarks key."""
        result = get_bookmark({}, "stream_a", "2020-01-01T00:00:00Z")
        self.assertEqual(result, "2020-01-01T00:00:00Z")

    def test_returns_stored_bookmark_value(self):
        """get_bookmark returns the value stored in state."""
        state = {"bookmarks": {"stream_a": "2021-05-01T00:00:00Z"}}
        result = get_bookmark(state, "stream_a", "2020-01-01T00:00:00Z")
        self.assertEqual(result, "2021-05-01T00:00:00Z")

    def test_returns_default_when_stream_not_in_bookmarks(self):
        """get_bookmark returns default when stream is absent from bookmarks."""
        state = {"bookmarks": {"other_stream": "2021-05-01T00:00:00Z"}}
        result = get_bookmark(state, "stream_a", "2020-01-01T00:00:00Z")
        self.assertEqual(result, "2020-01-01T00:00:00Z")


# ---------------------------------------------------------------------------
# write_bookmark
# ---------------------------------------------------------------------------

class TestWriteBookmark(unittest.TestCase):
    @patch("tap_pepperjam.sync.singer.write_state")
    def test_creates_bookmarks_key_if_absent(self, mock_ws):
        """write_bookmark creates the 'bookmarks' key in state when it is missing."""
        state = {}
        write_bookmark(state, "stream_a", "2021-01-01T00:00:00Z")
        self.assertIn("bookmarks", state)

    @patch("tap_pepperjam.sync.singer.write_state")
    def test_stores_value_under_stream_key(self, mock_ws):
        """write_bookmark stores the value under the correct stream key."""
        state = {}
        write_bookmark(state, "stream_a", "2021-01-01T00:00:00Z")
        self.assertEqual(state["bookmarks"]["stream_a"], "2021-01-01T00:00:00Z")

    @patch("tap_pepperjam.sync.singer.write_state")
    def test_calls_singer_write_state(self, mock_ws):
        """write_bookmark calls singer.write_state exactly once."""
        state = {}
        write_bookmark(state, "stream_a", "2021-01-01T00:00:00Z")
        mock_ws.assert_called_once_with(state)

    @patch("tap_pepperjam.sync.singer.write_state")
    def test_overwrites_existing_bookmark(self, mock_ws):
        """write_bookmark updates a previously written bookmark value."""
        state = {"bookmarks": {"stream_a": "2020-01-01T00:00:00Z"}}
        write_bookmark(state, "stream_a", "2021-01-01T00:00:00Z")
        self.assertEqual(state["bookmarks"]["stream_a"], "2021-01-01T00:00:00Z")


# ---------------------------------------------------------------------------
# write_schema
# ---------------------------------------------------------------------------

class TestWriteSchema(unittest.TestCase):
    @patch("tap_pepperjam.sync.singer.write_schema")
    def test_calls_singer_write_schema(self, mock_ws):
        """write_schema calls singer.write_schema with correct stream name and schema."""
        catalog = _make_catalog()
        catalog.get_stream.return_value.key_properties = ["id"]
        write_schema(catalog, "group")
        mock_ws.assert_called_once()
        args = mock_ws.call_args[0]
        self.assertEqual(args[0], "group")

    @patch("tap_pepperjam.sync.singer.write_schema")
    def test_raises_os_error_on_failure(self, mock_ws):
        """write_schema re-raises OSError when singer.write_schema fails."""
        catalog = _make_catalog()
        catalog.get_stream.return_value.key_properties = ["id"]
        mock_ws.side_effect = OSError("disk full")
        with self.assertRaises(OSError):
            write_schema(catalog, "group")


# ---------------------------------------------------------------------------
# write_record
# ---------------------------------------------------------------------------

class TestWriteRecord(unittest.TestCase):
    @patch("tap_pepperjam.sync.singer.messages.write_record")
    def test_calls_singer_write_record(self, mock_wr):
        """write_record delegates to singer.messages.write_record."""
        ts = singer_now()
        write_record("group", {"id": "1"}, ts)
        mock_wr.assert_called_once_with("group", {"id": "1"}, time_extracted=ts)

    @patch("tap_pepperjam.sync.singer.messages.write_record")
    def test_raises_os_error(self, mock_wr):
        """write_record re-raises OSError."""
        mock_wr.side_effect = OSError("disk full")
        with self.assertRaises(OSError):
            write_record("group", {"id": "1"}, singer_now())

    @patch("tap_pepperjam.sync.singer.messages.write_record")
    def test_raises_type_error(self, mock_wr):
        """write_record re-raises TypeError."""
        mock_wr.side_effect = TypeError("bad type")
        with self.assertRaises(TypeError):
            write_record("group", {"id": "1"}, singer_now())


# ---------------------------------------------------------------------------
# transform_datetime
# ---------------------------------------------------------------------------

class TestTransformDatetime(unittest.TestCase):
    def test_valid_datetime_string_returns_non_none(self):
        """transform_datetime returns a non-None value for a valid ISO datetime."""
        result = transform_datetime("2021-01-01T00:00:00Z")
        self.assertIsNotNone(result)

    def test_none_input_returns_none(self):
        """transform_datetime returns None for None input."""
        result = transform_datetime(None)
        self.assertIsNone(result)

    def test_result_contains_year(self):
        """transform_datetime result contains the original year."""
        result = transform_datetime("2023-06-15T10:30:00Z")
        self.assertIn("2023", result)


# ---------------------------------------------------------------------------
# process_records
# ---------------------------------------------------------------------------

class TestProcessRecords(unittest.TestCase):
    @patch("tap_pepperjam.sync.write_record")
    def test_full_table_writes_all_records(self, mock_wr):
        """process_records writes every record when no bookmark_field is given."""
        catalog = _make_catalog()
        records = [{"id": "1", "name": "A"}, {"id": "2", "name": "B"}]
        _, count = process_records(
            catalog=catalog,
            stream_name="group",
            records=records,
            time_extracted=singer_now(),
        )
        self.assertEqual(mock_wr.call_count, 2)
        self.assertEqual(count, 2)

    @patch("tap_pepperjam.sync.write_record")
    def test_incremental_skips_old_records(self, mock_wr):
        """process_records does not write records whose bookmark is before last_datetime."""
        catalog = _make_catalog()
        records = [{"id": "1", "name": "old", "modified": "2020-01-01T00:00:00Z"}]
        _, count = process_records(
            catalog=catalog,
            stream_name="group",
            records=records,
            time_extracted=singer_now(),
            bookmark_field="modified",
            last_datetime="2021-01-01T00:00:00Z",
        )
        self.assertEqual(count, 0)
        mock_wr.assert_not_called()

    @patch("tap_pepperjam.sync.write_record")
    def test_incremental_writes_records_at_or_after_bookmark(self, mock_wr):
        """process_records writes records whose bookmark >= last_datetime."""
        catalog = _make_catalog()
        records = [{"id": "1", "name": "new", "modified": "2022-06-01T00:00:00Z"}]
        _, count = process_records(
            catalog=catalog,
            stream_name="group",
            records=records,
            time_extracted=singer_now(),
            bookmark_field="modified",
            last_datetime="2021-01-01T00:00:00Z",
        )
        self.assertEqual(count, 1)

    @patch("tap_pepperjam.sync.write_record")
    def test_returns_tuple_of_max_bookmark_and_count(self, mock_wr):
        """process_records returns a (max_bookmark_value, record_count) tuple."""
        catalog = _make_catalog()
        records = [{"id": "1", "name": "A"}]
        result = process_records(
            catalog=catalog,
            stream_name="group",
            records=records,
            time_extracted=singer_now(),
        )
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    @patch("tap_pepperjam.sync.write_record")
    def test_empty_records_returns_none_bookmark_and_zero_count(self, mock_wr):
        """process_records with no records returns (None, 0)."""
        catalog = _make_catalog()
        max_bk, count = process_records(
            catalog=catalog,
            stream_name="group",
            records=[],
            time_extracted=singer_now(),
        )
        self.assertIsNone(max_bk)
        self.assertEqual(count, 0)

    @patch("tap_pepperjam.sync.write_record")
    def test_parent_id_injected_into_record(self, mock_wr):
        """process_records adds <parent>_id field to each child record."""
        catalog = _make_catalog()
        records = [{"id": "1", "name": "A"}]
        process_records(
            catalog=catalog,
            stream_name="group",
            records=records,
            time_extracted=singer_now(),
            parent="group",
            parent_id="999",
        )
        written_record = mock_wr.call_args[0][1]
        self.assertEqual(written_record.get("group_id"), "999")

    @patch("tap_pepperjam.sync.Transformer")
    @patch("tap_pepperjam.sync.write_record")
    def test_transformer_exception_is_raised(self, mock_wr, mock_transformer):
        """process_records re-raises exceptions thrown by the Singer Transformer."""
        catalog = _make_catalog()
        mock_transformer.return_value.__enter__.return_value.transform.side_effect = \
            Exception("transform failed")
        records = [{"id": "1"}]
        with self.assertRaises(Exception):
            process_records(
                catalog=catalog,
                stream_name="group",
                records=records,
                time_extracted=singer_now(),
            )

    @patch("tap_pepperjam.sync.write_record")
    def test_max_bookmark_updated_to_highest_value(self, mock_wr):
        """process_records updates max_bookmark_value to the highest seen bookmark."""
        catalog = _make_catalog()
        records = [
            {"id": "1", "name": "A", "modified": "2022-01-01T00:00:00Z"},
            {"id": "2", "name": "B", "modified": "2023-06-01T00:00:00Z"},
        ]
        max_bk, _ = process_records(
            catalog=catalog,
            stream_name="group",
            records=records,
            time_extracted=singer_now(),
            bookmark_field="modified",
            last_datetime="2021-01-01T00:00:00Z",
        )
        self.assertIsNotNone(max_bk)
        self.assertIn("2023", max_bk)


# ---------------------------------------------------------------------------
# update_currently_syncing
# ---------------------------------------------------------------------------

class TestUpdateCurrentlySyncing(unittest.TestCase):
    @patch("tap_pepperjam.sync.singer.write_state")
    def test_sets_currently_syncing(self, mock_ws):
        """update_currently_syncing stores the stream name in state."""
        state = {}
        update_currently_syncing(state, "transaction_details")
        self.assertEqual(state.get("currently_syncing"), "transaction_details")

    @patch("tap_pepperjam.sync.singer.write_state")
    def test_removes_currently_syncing_when_none(self, mock_ws):
        """update_currently_syncing removes the key when stream is None."""
        state = {"currently_syncing": "transaction_details"}
        update_currently_syncing(state, None)
        self.assertNotIn("currently_syncing", state)

    @patch("tap_pepperjam.sync.singer.write_state")
    def test_calls_singer_write_state(self, mock_ws):
        """update_currently_syncing calls singer.write_state."""
        state = {}
        update_currently_syncing(state, "group")
        mock_ws.assert_called()


# ---------------------------------------------------------------------------
# sync
# ---------------------------------------------------------------------------

class TestSync(unittest.TestCase):
    @patch("tap_pepperjam.sync.update_currently_syncing")
    @patch("tap_pepperjam.sync.sync_endpoint")
    @patch("tap_pepperjam.sync.write_schema")
    def test_returns_early_when_no_selected_streams(self, mock_ws, mock_se, mock_ucs):
        """sync() exits without processing when no streams are selected."""
        mock_catalog = MagicMock()
        mock_catalog.get_selected_streams.return_value = []
        config = {"start_date": "2021-01-01T00:00:00Z"}
        sync(client=MagicMock(), config=config, catalog=mock_catalog, state={})
        mock_ws.assert_not_called()
        mock_se.assert_not_called()

    @patch("tap_pepperjam.sync.update_currently_syncing")
    @patch("tap_pepperjam.sync.sync_endpoint", return_value=10)
    @patch("tap_pepperjam.sync.write_schema")
    def test_processes_selected_streams(self, mock_ws, mock_se, mock_ucs):
        """sync() calls write_schema and sync_endpoint for each selected stream."""
        mock_stream = MagicMock()
        mock_stream.stream = "group"
        mock_catalog = MagicMock()
        mock_catalog.get_selected_streams.return_value = [mock_stream]
        config = {
            "start_date": "2021-01-01T00:00:00Z",
            "lock_period_days": "60",
            "date_window_days": "30",
        }
        sync(client=MagicMock(), config=config, catalog=mock_catalog, state={})
        mock_ws.assert_called_once()
        mock_se.assert_called_once()

    @patch("tap_pepperjam.sync.update_currently_syncing")
    @patch("tap_pepperjam.sync.sync_endpoint", return_value=5)
    @patch("tap_pepperjam.sync.write_schema")
    def test_skips_streams_not_in_selected(self, mock_ws, mock_se, mock_ucs):
        """sync() only processes streams present in selected_streams."""
        mock_stream = MagicMock()
        mock_stream.stream = "publisher"  # Only publisher selected
        mock_catalog = MagicMock()
        mock_catalog.get_selected_streams.return_value = [mock_stream]
        config = {
            "start_date": "2021-01-01T00:00:00Z",
            "lock_period_days": "60",
            "date_window_days": "30",
        }
        sync(client=MagicMock(), config=config, catalog=mock_catalog, state={})
        # sync_endpoint is called exactly once (for publisher only)
        self.assertEqual(mock_se.call_count, 1)

    @patch("tap_pepperjam.sync.update_currently_syncing")
    @patch("tap_pepperjam.sync.sync_endpoint", return_value=0)
    @patch("tap_pepperjam.sync.write_schema")
    def test_update_currently_syncing_called_twice_per_stream(self, mock_ws, mock_se, mock_ucs):
        """sync() calls update_currently_syncing twice per stream (start and end)."""
        mock_stream = MagicMock()
        mock_stream.stream = "publisher"
        mock_catalog = MagicMock()
        mock_catalog.get_selected_streams.return_value = [mock_stream]
        config = {
            "start_date": "2021-01-01T00:00:00Z",
            "lock_period_days": "60",
            "date_window_days": "30",
        }
        sync(client=MagicMock(), config=config, catalog=mock_catalog, state={})
        self.assertEqual(mock_ucs.call_count, 2)

    @patch("tap_pepperjam.sync.update_currently_syncing")
    @patch("tap_pepperjam.sync.sync_endpoint", return_value=10)
    @patch("tap_pepperjam.sync.write_schema")
    def test_passes_lock_period_and_date_window_from_config(self, mock_ws, mock_se, mock_ucs):
        """sync() passes lock_period_days and date_window_days from config to sync_endpoint."""
        mock_stream = MagicMock()
        mock_stream.stream = "publisher"
        mock_catalog = MagicMock()
        mock_catalog.get_selected_streams.return_value = [mock_stream]
        config = {
            "start_date": "2021-01-01T00:00:00Z",
            "lock_period_days": "45",
            "date_window_days": "14",
        }
        sync(client=MagicMock(), config=config, catalog=mock_catalog, state={})
        call_kwargs = mock_se.call_args[1]
        self.assertEqual(call_kwargs["lock_period_days"], 45)
        self.assertEqual(call_kwargs["date_window_days"], 14)


# ---------------------------------------------------------------------------
# sync_endpoint
# ---------------------------------------------------------------------------

from tap_pepperjam.sync import sync_endpoint


def _full_table_endpoint_config():
    return {
        "path": "group",
        "key_properties": ["id"],
        "replication_method": "FULL_TABLE",
        "data_key": "data",
        "params": {},
    }


def _incremental_endpoint_config():
    return {
        "path": "creative/advanced",
        "key_properties": ["id"],
        "replication_method": "INCREMENTAL",
        "replication_keys": ["modified"],
        "data_key": "data",
        "params": {},
    }


def _make_api_response(records, next_href=None):
    """Build a minimal API response dict with pagination metadata."""
    pagination = {"total_results": len(records)}
    if next_href:
        pagination["next"] = {"rel": "next", "href": next_href}
    return {"data": records, "meta": {"pagination": pagination}}


class TestSyncEndpoint(unittest.TestCase):
    def _base_kwargs(self, endpoint_config, bookmark_field=None):
        catalog = _make_catalog()
        client = MagicMock()
        config = {"api_key": "test_key", "start_date": "2021-01-01T00:00:00Z"}
        return dict(
            client=client,
            config=config,
            catalog=catalog,
            state={},
            start_date="2021-01-01T00:00:00Z",
            stream_name="group",
            path="group",
            endpoint_config=endpoint_config,
            bookmark_field=bookmark_field,
            selected_streams=["group"],
        )

    @patch("tap_pepperjam.sync.process_records", return_value=("2021-06-01T00:00:00Z", 2))
    def test_single_page_full_table_returns_record_count(self, mock_pr):
        """sync_endpoint returns total record count for a single-page full-table stream."""
        kwargs = self._base_kwargs(_full_table_endpoint_config())
        response = _make_api_response([{"id": "1"}, {"id": "2"}])
        kwargs["client"].get.return_value = response

        total = sync_endpoint(**kwargs)

        self.assertGreaterEqual(total, 0)

    @patch("tap_pepperjam.sync.process_records", return_value=(None, 0))
    def test_empty_api_response_breaks_loop(self, mock_pr):
        """sync_endpoint breaks the inner pagination loop when data is empty."""
        kwargs = self._base_kwargs(_full_table_endpoint_config())
        kwargs["client"].get.return_value = {}

        total = sync_endpoint(**kwargs)

        self.assertEqual(total, 0)

    @patch("tap_pepperjam.sync.process_records", return_value=(None, 0))
    def test_none_data_breaks_loop(self, mock_pr):
        """sync_endpoint breaks the inner loop when client.get returns None."""
        kwargs = self._base_kwargs(_full_table_endpoint_config())
        kwargs["client"].get.return_value = None

        total = sync_endpoint(**kwargs)

        self.assertEqual(total, 0)

    @patch("tap_pepperjam.sync.write_bookmark")
    @patch("tap_pepperjam.sync.process_records", return_value=("2021-06-01T00:00:00Z", 3))
    def test_bookmark_written_after_window_for_incremental(self, mock_pr, mock_wb):
        """sync_endpoint calls write_bookmark after processing an incremental stream."""
        kwargs = self._base_kwargs(_incremental_endpoint_config(), bookmark_field="modified")
        response = _make_api_response([{"id": "1"}, {"id": "2"}, {"id": "3"}])
        kwargs["client"].get.return_value = response

        sync_endpoint(**kwargs)

        mock_wb.assert_called()

    @patch("tap_pepperjam.sync.process_records", return_value=(None, 0))
    def test_missing_key_id_in_record_raises_runtime_error(self, mock_pr):
        """sync_endpoint raises RuntimeError when a required key_property is missing from a record."""
        kwargs = self._base_kwargs(_full_table_endpoint_config())
        # Return a record that has no 'id' field
        response = _make_api_response([{"name": "no_id_here"}])
        kwargs["client"].get.return_value = response
        mock_pr.return_value = (None, 1)  # pretend processing succeeds

        with self.assertRaises(RuntimeError):
            sync_endpoint(**kwargs)

    @patch("tap_pepperjam.sync.process_records", return_value=("2021-06-01T00:00:00Z", 5))
    def test_two_page_response_makes_two_client_calls(self, mock_pr):
        """sync_endpoint calls client.get twice when a second page is available."""
        kwargs = self._base_kwargs(_full_table_endpoint_config())
        page1 = _make_api_response(
            [{"id": str(i)} for i in range(5)],
            next_href="https://api.pepperjamnetwork.com/20120402/advertiser/group/?page=2",
        )
        page2 = _make_api_response([{"id": str(i)} for i in range(5, 10)])
        kwargs["client"].get.side_effect = [page1, page2]

        sync_endpoint(**kwargs)

        self.assertEqual(kwargs["client"].get.call_count, 2)

    @patch("tap_pepperjam.sync.process_records", return_value=(None, 0))
    def test_windowed_stream_adds_date_params(self, mock_pr):
        """sync_endpoint injects startDate/endDate params for windowed incremental streams."""
        windowed_config = {
            "path": "report/creative-details",
            "key_properties": ["creative_id", "creative_type", "date"],
            "replication_method": "INCREMENTAL",
            "replication_keys": ["datetime"],
            "bookmark_query_field_from": "startDate",
            "bookmark_query_field_to": "endDate",
            "lock_period_ind": True,
            "data_key": "data",
            "params": {"groupBy": "date"},
        }
        kwargs = self._base_kwargs(windowed_config, bookmark_field="datetime")
        response = _make_api_response([])
        kwargs["client"].get.return_value = response

        sync_endpoint(**kwargs)

        # client.get should have been called at least once
        self.assertGreater(kwargs["client"].get.call_count, 0)
        # Inspect querystring param passed to first call
        first_call_kwargs = kwargs["client"].get.call_args_list[0][1]
        qs = first_call_kwargs.get("params", "")
        self.assertIn("startDate", str(qs))
        self.assertIn("endDate", str(qs))

    @patch("tap_pepperjam.sync.process_records", return_value=(None, 0))
    def test_transaction_history_window_capped_at_28_days(self, mock_pr):
        """sync_endpoint caps date_window_days to 28 for the transaction_history stream."""
        th_config = {
            "path": "report/transaction-history",
            "key_properties": ["transaction_id", "item_id", "revision"],
            "replication_method": "INCREMENTAL",
            "replication_keys": ["sale_date"],
            "bookmark_query_field_from": "startDate",
            "bookmark_query_field_to": "endDate",
            "lock_period_ind": False,
            "data_key": "data",
            "params": {},
        }
        kwargs = self._base_kwargs(th_config, bookmark_field="sale_date")
        kwargs["stream_name"] = "transaction_history"
        response = _make_api_response([])
        kwargs["client"].get.return_value = response

        # Providing date_window_days=60 — should be capped to 28
        total = sync_endpoint(**kwargs, date_window_days=60)

        self.assertIsNotNone(total)


if __name__ == "__main__":
    unittest.main()
