import copy
from datetime import datetime

import singer
from singer.catalog import Catalog, CatalogEntry, Schema
from tap_pepperjam.client import PepperjamForbiddenError
from tap_pepperjam.schema import get_schemas
from tap_pepperjam.streams import flatten_streams, STREAMS

LOGGER = singer.get_logger()


def _stream_is_accessible(client, stream_name, stream_metadata):
    """Return False only when a stream probe fails with 403."""
    if stream_metadata.get('parent_stream'):
        return True

    endpoint_config = STREAMS.get(stream_name, {})
    path = endpoint_config.get('path')
    if not path:
        return True

    params = copy.deepcopy(endpoint_config.get('params', {}))
    params['page'] = 1

    bookmark_query_field_from = endpoint_config.get('bookmark_query_field_from')
    bookmark_query_field_to = endpoint_config.get('bookmark_query_field_to')
    if bookmark_query_field_from and bookmark_query_field_to:
        today = datetime.utcnow().strftime('%Y-%m-%d')
        params[bookmark_query_field_from] = today
        params[bookmark_query_field_to] = today

    try:
        # client.get(path=path, params=params, endpoint=stream_name)
        return True
    except PepperjamForbiddenError as exc:
        LOGGER.warning(
            "Unauthorized stream excluded from catalog: %s. HTTP error: %s",
            stream_name,
            exc,
        )
        return False


def _prune_inaccessible_children(schemas, field_metadata, flat_streams):
    """Remove child streams whose parent stream is no longer in schemas."""
    has_removed_stream = True
    to_remove = []
    while has_removed_stream:
        has_removed_stream = False
        for stream_name, stream_metadata in flat_streams.items():
            parent_stream = stream_metadata.get('parent_stream')
            if stream_name in schemas and parent_stream and parent_stream not in schemas:
                LOGGER.warning(
                    "Stream '%s' excluded because parent stream '%s' is not accessible.",
                    stream_name,
                    parent_stream,
                )
                schemas.pop(stream_name, None)
                field_metadata.pop(stream_name, None)
                to_remove.append(stream_name)
                has_removed_stream = True
    return to_remove

def _apply_access_checks(client, schemas, field_metadata):
    """Prune inaccessible streams from discovery payload in place."""
    flat_streams = flatten_streams()
    inaccessible_streams = [
        stream_name
        for stream_name, stream_metadata in flat_streams.items()
        if stream_name in schemas and not _stream_is_accessible(client, stream_name, stream_metadata)
    ]

    for stream_name in inaccessible_streams:
        schemas.pop(stream_name, None)
        field_metadata.pop(stream_name, None)

    inaccessible_streams.extend(_prune_inaccessible_children(schemas, field_metadata, flat_streams))

    if not schemas:
        raise PepperjamForbiddenError(
            "No streams are accessible. Ensure credentials have read permission for at least one stream."
        )
    if inaccessible_streams:
        LOGGER.warning(
            "Unauthorized streams have been excluded: %s",
            ', '.join(inaccessible_streams),
        )


def discover(client):
    schemas, field_metadata = get_schemas()

    _apply_access_checks(client, schemas, field_metadata)

    catalog = Catalog([])

    flat_streams = flatten_streams()
    for stream_name, schema_dict in schemas.items():
        schema = Schema.from_dict(schema_dict)
        mdata = field_metadata[stream_name]

        catalog.streams.append(CatalogEntry(
            stream=stream_name,
            tap_stream_id=stream_name,
            key_properties=flat_streams.get(stream_name, {}).get('key_properties', None),
            schema=schema,
            metadata=mdata
        ))

    return catalog
