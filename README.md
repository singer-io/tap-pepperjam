# tap-pepperjam

This is a [Singer](https://singer.io) tap that produces JSON-formatted data
following the [Singer
spec](https://github.com/singer-io/getting-started/blob/master/SPEC.md).

This tap:

- Pulls raw data from the [Pepperjam Advertiser API]([xxx](https://support.pepperjam.com/s/advertiser-api-documentation))
- Extracts the following resources:
  - **Creative Endpoints**:
    - [creative_advanced](https://support.pepperjam.com/s/advertiser-api-documentation#AdvancedLinks)
    - [creative_banner](https://support.pepperjam.com/s/advertiser-api-documentation#Banner)
    - [creative_coupon](https://support.pepperjam.com/s/advertiser-api-documentation#CouponCreative)
    - [creative_generic](https://support.pepperjam.com/s/advertiser-api-documentation#Generic)
    - [creative_product](https://support.pepperjam.com/s/advertiser-api-documentation#ProductCreative)
    - [crative_promotion](https://support.pepperjam.com/s/advertiser-api-documentation#CreativePromotion)
    - [creative_text](https://support.pepperjam.com/s/advertiser-api-documentation#Text)
  - [group](https://support.pepperjam.com/s/advertiser-api-documentation#Group)
    - [group_member](https://support.pepperjam.com/s/advertiser-api-documentation#Member)
  - [itemized_list](https://support.pepperjam.com/s/advertiser-api-documentation#ItemizedList)
    - [itemized_list_product](https://support.pepperjam.com/s/advertiser-api-documentation#Product)
  - [publisher](https://support.pepperjam.com/s/advertiser-api-documentation#Publisher)
  - [term](https://support.pepperjam.com/s/advertiser-api-documentation#Term)
  - **Report Endpoints**
    - [creative_performance](https://support.pepperjam.com/s/advertiser-api-documentation#CreativeDetails)
    - [creative_performance_by_publisher](https://support.pepperjam.com/s/advertiser-api-documentation#CreativePerformanceByPublisher)
    - [publisher_performance](https://support.pepperjam.com/s/advertiser-api-documentation#PublisherPerformance)
    - [transaction_details](https://support.pepperjam.com/s/advertiser-api-documentation#TransactionDetails)
    - [transaction_history](https://support.pepperjam.com/s/advertiser-api-documentation#TransactionHistory)
  
- Outputs the schema for each resource
- Incrementally pulls data based on the input state


## Streams

### Standard Endpoints:

[creative_advanced]([creative_advanced](https://support.pepperjam.com/s/advertiser-api-documentation#AdvancedLinks))
- Endpoint: creative/advanced
- Primary key fields: id
- Replication strategy: INCREMENTAL (results filtered)
   - Bookmark: modified (date-time)
- Transformations: none

[creative_banner](https://support.pepperjam.com/s/advertiser-api-documentation#Banner)
- Endpoint: creative/banner
- Primary key fields: id
- Replication strategy: INCREMENTAL (results filtered)
   - Bookmark: modified (date-time)
- Transformations: none

[creative_coupon](https://support.pepperjam.com/s/advertiser-api-documentation#CouponCreative)
- Endpoint: creative/coupon
- Primary key fields: id
- Replication strategy: INCREMENTAL (results filtered)
   - Bookmark: modified (date-time)
- Transformations: none

[creative_generic](https://support.pepperjam.com/s/advertiser-api-documentation#Generic)
- Endpoint: creative/generic
- Primary key fields: type
- Replication strategy: INCREMENTAL (results filtered)
   - Bookmark: modified (date-time)
- Transformations: none

[creative_product](https://support.pepperjam.com/s/advertiser-api-documentation#ProductCreative)
- Endpoint: creative/product
- Primary key fields: type
- Replication strategy: FULL_TABLE
- Transformations: none

[crative_promotion](https://support.pepperjam.com/s/advertiser-api-documentation#CreativePromotion)
- Endpoint: creative/promotion
- Primary key fields: id
- Replication strategy: FULL_TABLE
- Transformations: none

[creative_text](https://support.pepperjam.com/s/advertiser-api-documentation#Text)
- Endpoint: creative/text
- Primary key fields: id
- Replication strategy: INCREMENTAL (results filtered)
   - Bookmark: modified (date-time)
- Transformations: none

[group](https://support.pepperjam.com/s/advertiser-api-documentation#Group)
- Endpoint: group
- Primary key fields: id
- Replication strategy: FULL_TABLE
- Transformations: none

[group_member](https://support.pepperjam.com/s/advertiser-api-documentation#Member)
- Endpoint: group/member
- Primary key fields: id
- Replication strategy: FULL_TABLE for each groupId
- Transformations: Add parent group_id

[itemized_list](https://support.pepperjam.com/s/advertiser-api-documentation#ItemizedList)
- Endpoint: itemized-list
- Primary key fields: id
- Replication strategy: FULL_TABLE
- Transformations: none

[itemized_list_product](https://support.pepperjam.com/s/advertiser-api-documentation#Product)
- Endpoint: itemized-list/product
- Primary key fields: id
- Replication strategy: FULL_TABLE for each listId
- Transformations: none

[publisher](https://support.pepperjam.com/s/advertiser-api-documentation#Publisher)
- Endpoint: publisher
- Primary key fields: id
- Replication strategy: FULL_TABLE for status = joined
- Transformations: none

[itemized_list](https://support.pepperjam.com/s/advertiser-api-documentation#ItemizedList)
- Endpoint: itemized-list
- Primary key fields: id
- Replication strategy: FULL_TABLE
- Transformations: none

[term](https://support.pepperjam.com/s/advertiser-api-documentation#Term)
- Endpoint: term
- Primary key fields: id
- Replication strategy: FULL_TABLE
- Transformations: none


### Report Endpoints

[creative_performance](https://support.pepperjam.com/s/advertiser-api-documentation#CreativeDetails)
- Endpoint: report/creative-details-publisher
- Primary key fields: creative_id, creative_type, date
- Group by: date
- Replication strategy: INCREMENTAL (query filtered)
   - Bookmark query fields: startDate, endDate
   - Bookmark: datetime (date-time)
- Transformations: none

[creative_performance_by_publisher](https://support.pepperjam.com/s/advertiser-api-documentation#CreativePerformanceByPublisher)
- Endpoint: report/creative-details-publisher
- Primary key fields: creative_id, creative_type, publisher_id, date
- Group by: publisher_date
- Replication strategy: INCREMENTAL (query filtered)
   - Bookmark query fields: startDate, endDate
   - Bookmark: datetime (date-time)
- Transformations: none

[publisher_performance](https://support.pepperjam.com/s/advertiser-api-documentation#PublisherPerformance)
- Endpoint: report/demand-details
- Primary key fields: publisher_id, order_id, sale_date
- Group by: publisher_date
- Replication strategy: INCREMENTAL (query filtered)
   - Bookmark query fields: startDate, endDate
   - Bookmark: sale_date (date-time)
- Transformations: none

[transaction_details](https://support.pepperjam.com/s/advertiser-api-documentation#TransactionDetails)
- Endpoint: report/transaction-details
- Primary key fields: transaction_id
- Replication strategy: INCREMENTAL (query filtered)
   - Bookmark query fields: startDate, endDate
   - Bookmark: sale_date (date-time)
- Transformations: none

[transaction_history](https://support.pepperjam.com/s/advertiser-api-documentation#TransactionHistory)
- Endpoint: report/transaction-history
- Primary key fields: transaction_id, item_id, revision
- Replication strategy: INCREMENTAL (query filtered)
   - Bookmark query fields: startDate, endDate
   - Bookmark: sale_date (date-time)
- Transformations: none


## Authentication
[Generate Advertiser API Key](http://www.pepperjamnetwork.com/merchant/api/): The API requires an API Key for Pepperjam to authenticate you as a user. This key is required as a query parameter for all API requests. Login to Pepperjam’s Ascend Console UI. Navigate to https://ascend.pepperjam.com/merchant/api/. Select Generate New Key.


## Quick Start

1. Install

    Clone this repository, and then install using setup.py. We recommend using a virtualenv:

    ```bash
    > virtualenv -p python3 venv
    > source venv/bin/activate
    > python setup.py install
    OR
    > cd .../tap-pepperjam
    > pip install .
    ```
2. Dependent libraries
    The following dependent libraries were installed.
    ```bash
    > pip install singer-python
    > pip install singer-tools
    > pip install target-stitch
    > pip install target-json
    
    ```
    - [singer-tools](https://github.com/singer-io/singer-tools)
    - [target-stitch](https://github.com/singer-io/target-stitch)

3. Create your tap's `config.json` file. The `api_key` is available in the Pepperjam Console UI (see **Authentication** above). The `date_window_days` is the integer number of days (between the from and to dates) for date-windowing through the date-filtered endpoints (default = 30). The `lock_period_days` is the latency look-back period for reports/performance endpoints. The `start_date` is the absolute beginning date from which incremental loading on the initial load will start.

    ```json
    {
        "api_key": "YOUR_API_KEY",
        "date_window_days": "30",
        "lock_period_days": "60",
        "start_date": "2019-01-01T00:00:00Z",
        "user_agent": "tap-pepperjam <api_user_email@your_company.com>",
    }
    ```
    
    Optionally, also create a `state.json` file. `currently_syncing` is an optional attribute used for identifying the last object to be synced in case the job is interrupted mid-stream. The next run would begin where the last job left off.

    ```json
    {
        "currently_syncing": "registers",
        "bookmarks": {
            "transaction_details": "2020-03-23T10:31:14.000000Z",
            "creative_performance_by_publisher": "2020-03-23T00:00:00.000000Z",
            "transaction_history": "2020-03-23T10:31:14.000000Z",
            "creative_performance": "2020-03-23T00:00:00.000000Z",
            "publisher_performance": "2020-03-23T00:00:00.000000Z"
        }
    }
    ```

4. Run the Tap in Discovery Mode
    This creates a catalog.json for selecting objects/fields to integrate:
    ```bash
    tap-pepperjam --config config.json --discover > catalog.json
    ```
   See the Singer docs on discovery mode
   [here](https://github.com/singer-io/getting-started/blob/master/docs/DISCOVERY_MODE.md#discovery-mode).

5. Run the Tap in Sync Mode (with catalog) and [write out to state file](https://github.com/singer-io/getting-started/blob/master/docs/RUNNING_AND_DEVELOPING.md#running-a-singer-tap-with-a-singer-target)

    For Sync mode:
    ```bash
    > tap-pepperjam --config tap_config.json --catalog catalog.json > state.json
    > tail -1 state.json > state.json.tmp && mv state.json.tmp state.json
    ```
    To load to json files to verify outputs:
    ```bash
    > tap-pepperjam --config tap_config.json --catalog catalog.json | target-json > state.json
    > tail -1 state.json > state.json.tmp && mv state.json.tmp state.json
    ```
    To pseudo-load to [Stitch Import API](https://github.com/singer-io/target-stitch) with dry run:
    ```bash
    > tap-pepperjam --config tap_config.json --catalog catalog.json | target-stitch --config target_config.json --dry-run > state.json
    > tail -1 state.json > state.json.tmp && mv state.json.tmp state.json
    ```

6. Test the Tap
    
    While developing the pepperjam tap, the following utilities were run in accordance with Singer.io best practices:
    Pylint to improve [code quality](https://github.com/singer-io/getting-started/blob/master/docs/BEST_PRACTICES.md#code-quality):
    ```bash
    > pylint tap_pepperjam -d missing-docstring -d logging-format-interpolation -d too-many-locals -d too-many-arguments
    ```
    Pylint test resulted in the following score:
    ```bash
    Your code has been rated at 9.70/10
    ```

    To [check the tap](https://github.com/singer-io/singer-tools#singer-check-tap) and verify working:
    ```bash
    > tap-pepperjam --config tap_config.json --catalog catalog.json | singer-check-tap > state.json
    > tail -1 state.json > state.json.tmp && mv state.json.tmp state.json
    ```
    Check tap resulted in the following:
    ```bash
        The output is valid.
        It contained 62636 messages for 18 streams.

            18 schema messages
        62505 record messages
            62 state messages

        Details by stream:
        +-----------------------------------+---------+---------+
        | stream                            | records | schemas |
        +-----------------------------------+---------+---------+
        | creative_generic                  | 1       | 1       |
        | itemized_list_product             | 2       | 1       |
        | group                             | 19      | 1       |
        | creative_advanced                 | 6       | 1       |
        | creative_coupon                   | 24      | 1       |
        | creative_text                     | 46      | 1       |
        | term                              | 171     | 1       |
        | publisher_performance             | 2786    | 1       |
        | creative_product                  | 2       | 1       |
        | publisher                         | 63      | 1       |
        | creative_banner                   | 24      | 1       |
        | creative_performance_by_publisher | 5962    | 1       |
        | transaction_history               | 23654   | 1       |
        | creative_performance              | 5962    | 1       |
        | transaction_details               | 23654   | 1       |
        | itemized_list                     | 34      | 1       |
        | group_member                      | 67      | 1       |
        | creative_promotion                | 28      | 1       |
        +-----------------------------------+---------+---------+

    ```
---

Copyright &copy; 2020 Stitch
