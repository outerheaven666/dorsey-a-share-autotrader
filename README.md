# Dorsey A-Share Autotrader

A-share low-frequency rules-based automated trading system based on Pat Dorsey's fundamental investing framework.

Current phase: **MVP 7 / Adapter Contract Tests Before Real Data Integration**.

This project does **not** perform real-money trading. It only reads local sample CSV files, local fixture CSV files, validates schemas, builds point-in-time visible datasets, checks data quality, builds scores and target portfolios, runs paper broker simulation, runs local quarterly backtests, generates reports, writes dry-run notification summaries, and records local audit logs.

## Safety Statement

This system is for personal research, system development, paper trading, and backtest simulation only.

It does not provide investment advice. It does not guarantee returns. It does not support real trading. It has no real broker connection. It has no real network data source connection. It has no QMT adapter, no PTrade adapter, no real broker credentials, and no live order placement path.

MVP 7 adds a mock adapter contract test layer only. `MockAShareProvider` is not an actual market data source. It reads fake local fixture CSV files and exists only to test future adapter contracts.

## Configuration

Default configuration:

```text
config/default.yaml
```

Important sections:

* `data_source`: production path for local CSV sample data. Default mode is `local_csv`, provider is `sample_csv`, and `allow_network` is `false`.
* `point_in_time`: `as_of_date`, disclosure-date filtering, future-disclosure blocking, and maximum financial lag.
* `factor_audit`: controls component score, raw input, red flag, moat proxy, and valuation explanations.
* `schema_validation`: controls required column, numeric field, duplicate key, and extra column checks.
* `adapter_contract`: contract-test-only adapter settings. Default mode is `mock_only`, provider is `mock_a_share`, `allow_network` is `false`, and `allow_real_provider` is `false`.
* `field_mapping`: controls external-field to internal-field mapping, symbol normalization, date normalization, and extra-field handling.
* `provider_tests`: controls which mock provider datasets are required and whether contract failures block.

No API token, password, secret, webhook, account, or paid data source credential is stored in the repository.

## Adapter Contract Layer

MVP 7 prepares for future A-share data integration without connecting to any external system.

The adapter contract defines a `DataProvider` interface with these methods:

```text
get_stock_basic()
get_financial_snapshot()
get_market_snapshot()
get_historical_market_snapshot()
get_trading_calendar()
```

Current implementation:

```text
MockAShareProvider
```

It reads fake fixture files from:

```text
data/fixtures/mock_provider/
```

Fixture files:

```text
stock_basic_raw.csv
financial_snapshot_raw.csv
market_snapshot_raw.csv
historical_market_snapshot_raw.csv
trading_calendar_raw.csv
```

These raw files intentionally use provider-like field names such as `ts_code`, `ann_date`, `end_date`, `close`, `total_mv`, `st_flag`, and `date`. The mapping layer converts them into the internal standard schema.

No real provider is implemented. Real network providers, paid data sources, broker APIs, and live trading paths are disabled.

## Field Mapping

The mapping layer handles:

* External field name to internal standard field name.
* Symbol normalization, such as `600519SH` to `600519.SH`.
* Date normalization to `YYYY-MM-DD`.
* Numeric value normalization.
* Boolean value normalization.
* Extra source-field warnings.
* Missing required-field failures.

Output:

```text
data/output/adapter_mapped_preview.csv
```

Fields:

```text
provider,dataset,source_field,target_field,status,message
```

## Provider Contract Validation

Run:

```bash
python -m dorsey_as validate-provider-contract --config config/default.yaml
```

This command only runs the mock provider. It loads fixture raw CSV files, maps fields, validates internal schema compatibility, checks duplicate keys and numeric fields, checks point-in-time compatibility, and writes a contract report.

Outputs:

```text
data/output/provider_contract_report.csv
data/output/provider_contract_summary.md
data/output/adapter_mapped_preview.csv
```

`provider_contract_report.csv` fields:

```text
provider,dataset,check_type,status,severity,message
```

`provider_contract_summary.md` includes provider name, contract version, checked datasets, passed checks, warnings, blocking failures, safety boundary, and current limitations.

## Explain Provider

Run:

```bash
python -m dorsey_as explain-provider --config config/default.yaml
```

Output:

```text
data/output/provider_explanation.md
```

The explanation includes current `data_source.mode`, adapter mode, provider, network status, real-provider status, why no real provider exists now, future provider contract requirements, and the safety statement.

## Local Data Source Layer

The default scoring, portfolio, paper broker, and backtest paths still use:

```text
LocalCsvDataSource
```

Local CSV sample outputs:

```text
data/output/data_source_manifest.csv
data/output/schema_validation_report.csv
```

`MockAShareProvider` is not used by `run-score` or `run-backtest`. It is only used by `validate-provider-contract`.

## Schema Validation

Run:

```bash
python -m dorsey_as validate-schema --config config/default.yaml
```

The report fields are:

```text
file,check_type,status,severity,message
```

Validation covers required columns, numeric field parsing, duplicate keys, and extra column warnings.

## Point-In-Time Data

Financial snapshots include `report_date` and `disclosure_date`. At any `as_of_date`, the system may only use rows where:

```text
disclosure_date <= as_of_date
```

If a report period is in the past but `disclosure_date` is later than `as_of_date`, that row is excluded as future disclosure. This protects scoring and backtesting from look-ahead bias.

Output:

```text
data/output/point_in_time_snapshot.csv
```

Fields:

```text
as_of_date,symbol,year,report_date,disclosure_date,visible,reason
```

`run-score` and each backtest rebalance date use point-in-time visible financials.

## Factor Audit Drilldown

Output:

```text
data/output/factor_audit_log.csv
```

Fields:

```text
run_id,timestamp,as_of_date,symbol,factor_group,factor_name,raw_value,normalized_value,component_score,weight,weighted_score,reason,severity
```

Groups include `quality`, `moat`, `valuation`, `risk`, and `composite`.

## Explain Score

Run:

```bash
python -m dorsey_as explain-score --symbol 600519.SH --config config/default.yaml
```

Output:

```text
data/output/explain_600519.SH.md
```

## CLI Usage

```bash
python -m dorsey_as validate-provider-contract --config config/default.yaml
python -m dorsey_as explain-provider --config config/default.yaml
python -m dorsey_as validate-schema --config config/default.yaml
python -m dorsey_as check-data-quality --config config/default.yaml
python -m dorsey_as run-score --config config/default.yaml
python -m dorsey_as explain-score --symbol 600519.SH --config config/default.yaml
python -m dorsey_as run-backtest --config config/default.yaml
python -m dorsey_as generate-report --config config/default.yaml
python -m dorsey_as notify-summary --config config/default.yaml
```

## Reports

Markdown and HTML reports are written to:

```text
data/output/run_report.md
data/output/backtest_report.md
data/output/run_report.html
data/output/backtest_report.html
```

MVP 7 reports include:

* Data source summary.
* Adapter contract summary.
* Provider contract validation summary.
* Mock provider status.
* Real data source status: not enabled.
* Network data source status: disabled.
* Schema validation summary.
* Point-in-time data summary.
* Future disclosure exclusion counts.
* Factor audit summary.
* Top score tables.
* Backtest metrics and charts.
* Safety statement.

Backtest reports explicitly state that backtests still use local CSV sample data and that the mock provider is only for contract testing.

## Notifications

Notification summary remains dry-run by default:

```text
data/output/notify_payload.json
data/output/notify_summary.md
```

No real notification is sent unless explicitly configured in a later phase. If real sending is ever enabled, webhook values must come from environment variables and must not be committed.

## Audit Logs

Output:

```text
data/output/decision_audit_log.csv
```

MVP 7 adds stages:

* `adapter_contract`
* `provider_registry`
* `field_mapping`
* `mock_provider`

MVP 7 adds decision types:

* `validate_provider_contract`
* `map_fields`
* `normalize_symbol`
* `normalize_date`
* `reject_real_provider`
* `reject_network_access`

Audit logs are sanitized and must not contain tokens, secrets, passwords, credentials, webhook URLs, real account data, or real broker information.

## Future Real Provider Requirements

A future real data provider must satisfy all of these before it can be considered:

* It must implement the `DataProvider` contract.
* It must pass provider contract validation.
* It must map all required fields into the internal schema.
* It must provide point-in-time compatible `disclosure_date`.
* It must pass schema validation, data quality checks, duplicate-key checks, and numeric parsing checks.
* It must not be enabled by default.
* It must not store secrets in the repository.
* It must have explicit network and credential handling rules in a later approved milestone.

## Current Limitations

* Only local sample CSV data is used by scoring and backtesting.
* Mock provider reads fake local fixtures only.
* No real network data source is implemented.
* No paid data source is implemented.
* No real broker integration exists.
* No live trading mode exists.
* HTML reports are static.
* Backtest data is quarterly sample data, not a full daily A-share database.
* Rebalance-day valuation still uses MVP proxy assumptions where point-in-time valuation fields are not present.

## Next Phase

Recommended Phase 8 work:

1. Add schema versioning and migration checks for provider contracts.
2. Add richer fixture variants for corporate actions, delisting, suspended stocks, and revised financial disclosures.
3. Add provider contract diff reports across schema versions.
4. Add point-in-time valuation snapshot fixtures.
5. Add a disabled-by-default provider adapter template with no network implementation.

## Disclaimer

This project is for personal research and system development only.

It does not provide investment advice, does not guarantee returns, does not support real-money trading, has no real broker connection, has no real network data source connection, and only supports paper trading and backtest simulation. Mock provider is only used for contract testing and is not an actual market data source.
