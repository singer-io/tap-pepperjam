# streams: API URL endpoints to be called
# properties:
#   <root node>: Plural stream name for the endpoint
#   path: API endpoint relative path, when added to the base URL, creates the full path
#   key_properties: Primary key field(s) for the object endpoint
#   replication_method: FULL_TABLE or INCREMENTAL
#   replication_keys: bookmark_field(s), typically a date-time, used for filtering the results
#        and setting the state
#   params: Query, sort, and other endpoint specific parameters
#   data_key: JSON element containing the records for the endpoint
#   bookmark_query_field: Typically a date-time field used for filtering the query
#   bookmark_type: Data type for bookmark, integer or datetime
#   children: A collection of child endpoints (where the endpoint path includes the parent id)
#   parent: On each of the children, the singular stream name for parent element

STREAMS = {
    # Reference: https://support.pepperjam.com/s/advertiser-api-documentation#AdvancedLinks
    'creative_advanced': {
        'path': 'creative/advanced',
        'key_properties': ['id'],
        'replication_method': 'INCREMENTAL',
        'replication_keys': ['modified'],
        'data_key': 'data',
        'params': {}
    },

    # Reference: https://support.pepperjam.com/s/advertiser-api-documentation#Banner
    'creative_banner': {
        'path': 'creative/banner',
        'key_properties': ['id'],
        'replication_method': 'INCREMENTAL',
        'replication_keys': ['modified'],
        'data_key': 'data',
        'params': {}
    },

    # Reference: https://support.pepperjam.com/s/advertiser-api-documentation#CouponCreative
    'creative_coupon': {
        'path': 'creative/coupon',
        'key_properties': ['id'],
        'replication_method': 'INCREMENTAL',
        'replication_keys': ['modified'],
        'data_key': 'data',
        'params': {}
    },

    # Reference: https://support.pepperjam.com/s/advertiser-api-documentation#Generic
    'creative_generic': {
        'path': 'creative/generic',
        'key_properties': ['type'],
        'replication_method': 'INCREMENTAL',
        'replication_keys': ['modified'],
        'data_key': 'data',
        'params': {}
    },

    # Reference: https://support.pepperjam.com/s/advertiser-api-documentation#ProductCreative
    'creative_product': {
        'path': 'creative/product',
        'key_properties': ['id'],
        'replication_method': 'FULL_TABLE',
        'data_key': 'data',
        'params': {}
    },

    # Reference: https://support.pepperjam.com/s/advertiser-api-documentation#CreativePromotion
    'creative_promotion': {
        'path': 'creative/promotion',
        'key_properties': ['id'],
        'replication_method': 'FULL_TABLE',
        'data_key': 'data',
        'params': {}
    },

    # Reference: https://support.pepperjam.com/s/advertiser-api-documentation#Text
    'creative_text': {
        'path': 'creative/text',
        'key_properties': ['id'],
        'replication_method': 'INCREMENTAL',
        'replication_keys': ['modified'],
        'data_key': 'data',
        'params': {}
    },

    # Reference: https://support.pepperjam.com/s/advertiser-api-documentation#Group
    'group': {
        'path': 'group',
        'key_properties': ['id'],
        'replication_method': 'FULL_TABLE',
        'data_key': 'data',
        'params': {},
        'children': {
            # Reference: https://support.pepperjam.com/s/advertiser-api-documentation#Member
            'group_member': {
                'path': 'group/member',
                'key_properties': ['id'],
                'replication_method': 'FULL_TABLE',
                'data_key': 'data',
                'params': {
                    'groupId': '<parent_id>'
                },
                'parent': 'group'
            }
        }
    },

    # Reference: https://support.pepperjam.com/s/advertiser-api-documentation#ItemizedList
    'itemized_list': {
        'path': 'itemized-list',
        'key_properties': ['id'],
        'replication_method': 'FULL_TABLE',
        'data_key': 'data',
        'params': {},
        'children': {
            # Reference: https://support.pepperjam.com/s/advertiser-api-documentation#Product
            'itemized_list_product': {
                'path': 'itemized-list/product',
                'key_properties': ['id', 'list_id'],
                'replication_method': 'FULL_TABLE',
                'data_key': 'data',
                'params': {
                    'listId': '<parent_id>'
                }
            }
        }
    },

    # Reference: https://support.pepperjam.com/s/advertiser-api-documentation#Publisher
    'publisher': {
        'path': 'publisher',
        'key_properties': ['id'],
        'replication_method': 'FULL_TABLE',
        'data_key': 'data',
        'params': {
            'status': 'joined'
        }
    },

    # Reference: https://support.pepperjam.com/s/advertiser-api-documentation#Term
    'term': {
        'path': 'term',
        'key_properties': ['id'],
        'replication_method': 'FULL_TABLE',
        'data_key': 'data',
        'params': {}
    },

    # Reference: https://support.pepperjam.com/s/advertiser-api-documentation#CreativeDetails
    'creative_performance': {
        'path': 'report/creative-details',
        'key_properties': ['creative_id', 'creative_type', 'date'],
        'replication_method': 'INCREMENTAL',
        'replication_keys': ['datetime'],
        'bookmark_query_field_from': 'startDate',
        'bookmark_query_field_to': 'endDate',
        'lock_period_ind': True,
        'params': {
            'groupBy': 'date'
        }
    },
    # Reference: https://support.pepperjam.com/s/advertiser-api-documentation#CreativePerformanceByPublisher
    'creative_performance_by_publisher': {
        'path': 'report/creative-details-publisher',
        'key_properties': ['creative_id', 'creative_type', 'publisher_id', 'date'],
        'replication_method': 'INCREMENTAL',
        'replication_keys': ['datetime'],
        'bookmark_query_field_from': 'startDate',
        'bookmark_query_field_to': 'endDate',
        'lock_period_ind': True,
        'params': {
            'groupBy': 'publisher_date'
        }
    },

    # Reference: https://support.pepperjam.com/s/advertiser-api-documentation#PublisherPerformance
    'publisher_performance': {
        'path': 'report/transaction-summary',
        'key_properties': ['publisher_id', 'date'],
        'replication_method': 'INCREMENTAL',
        'replication_keys': ['datetime'],
        'bookmark_query_field_from': 'startDate',
        'bookmark_query_field_to': 'endDate',
        'lock_period_ind': True,
        'params': {
            'groupBy': 'publisher_date'
        }
    },

    # Reference: https://support.pepperjam.com/s/advertiser-api-documentation#TransactionDetails
    'transaction_details': {
        'path': 'report/transaction-details',
        'key_properties': ['transaction_id'],
        'replication_method': 'INCREMENTAL',
        'replication_keys': ['sale_date'],
        'bookmark_query_field_from': 'startDate',
        'bookmark_query_field_to': 'endDate',
        'lock_period_ind': True,
        'params': {}
    },

    # Reference: https://support.pepperjam.com/s/advertiser-api-documentation#TransactionHistory
    'transaction_history': {
        'path': 'report/transaction-history',
        'key_properties': ['transaction_id', 'sale_date', 'process_date'],
        'replication_method': 'INCREMENTAL',
        'replication_keys': ['sale_date'],
        'bookmark_query_field_from': 'startDate',
        'bookmark_query_field_to': 'endDate',
        'lock_period_ind': False,
        'params': {
            'separateCommission': 1
        }
    }
}



def flatten_streams():
    flat_streams = {}
    # Loop through parents
    for stream_name, endpoint_config in STREAMS.items():
        flat_streams[stream_name] = {
            'key_properties': endpoint_config.get('key_properties'),
            'replication_method': endpoint_config.get('replication_method'),
            'replication_keys': endpoint_config.get('replication_keys')
        }
        # Loop through children
        children = endpoint_config.get('children')
        if children:
            for child_stream_name, child_enpoint_config in children.items():
                flat_streams[child_stream_name] = {
                    'key_properties': child_enpoint_config.get('key_properties'),
                    'replication_method': child_enpoint_config.get('replication_method'),
                    'replication_keys': child_enpoint_config.get('replication_keys')
                }
    return flat_streams
