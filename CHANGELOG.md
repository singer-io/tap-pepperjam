# Changelog

## 0.0.5
  * Fix beta testing issues with `endDate` query parameter requesting a future date (Eastern time zone). Changed query `startDate` and `endDate` to use Eastern time zone for date windows and not UTC time.

## 0.0.4
  * Fix issue where `api_key` is appearing in logs. Fix issue where `transaction_history` date window cannot exceed 28 days.

## 0.0.3
  * Fix primary key properties for reports. Fix transaction_history and creative_performance missing fields and JSON schema issues.

## 0.0.2
  * Make `api_version` a default in client.py (and not a tap `config.json` parameter) [#1](https://github.com/singer-io/tap-pepperjam/pull/1)

## 0.0.1
  * Initial commit
