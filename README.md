# Dorsey A-Share Autotrader

A-share low-frequency rules-based automated trading system based on Pat Dorsey's fundamental investing framework.

Current phase: **MVP 6 / Point-in-Time Data, Factor Audit Drilldown, Local Data Source Preparation, Reports, Paper Trading, and Local Backtesting**.

This project does **not** perform real-money trading. It only reads local sample CSV files, validates schemas, builds point-in-time visible datasets, checks data quality, builds scores and target portfolios, runs paper broker simulation, runs local quarterly backtests, generates reports, writes dry-run notification summaries, and records local audit logs.

## Safety Statement

This system is for personal research, system development, paper trading, and backtest simulation only.

It does not provide investment advice. It does not guarantee returns. It does not support real trading. It has no real broker connection. It has no real network data source connection. It has no QMT adapter, no PTrade adapter, no real broker credentials, and no live order placement path.

## Configuration

Default configuration:

```text
config/default.yaml
```

MVP 6 adds these sections:

* `data_source`: local CSV paths and provider metadata. Default mode is `local_csv`, provider is `sample_csv`, and `allow_network` is `false`.
* `point_in_time`: `as_of_date`, disclosure-date filtering, future-disclosure blocking, and maximum financial lag.
* `factor_audit`: controls component score, raw input, red flag, moat proxy, and valuation explanations.
* `schema_validation`: controls required column, numeric field, duplicate key, and extra column checks.

No API token, password, secret, webhook, account, or paid data source credential is stored in the repository.

## Local Data Source Layer

The current data source abstraction is preparation for future A-share data integration. MVP 6 implements only:

```text
LocalCsvDataSource
```

It validates local files and writes:

```text
data/output/data_source_manifest.csv
data/output/schema_validation_report.csv
```

No network download is allowed. No real market-data provider is implemented.

## Schema Validation

Run:

```bash
python -m dorsey_as validate-schema --config config/default.yaml
```

The report fields are:

```text
file,check_type,status,severity,message
```

Validation covers:

* Required columns.
* Numeric field parsing.
* Duplicate keys.
* Extra column warnings.

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

MVP 6 writes:

```text
data/output/factor_audit_log.csv
```

Fields:

```text
run_id,timestamp,as_of_date,symbol,factor_group,factor_name,raw_value,normalized_value,component_score,weight,weighted_score,reason,severity
```

Groups include:

* `quality`
* `moat`
* `valuation`
* `risk`
* `composite`

The audit log explains why a stock scored well, scored poorly, or was blocked by red flags.

## Explain Score

Run:

```bash
python -m dorsey_as explain-score --symbol 600519.SH --config config/default.yaml
```

This reads `scores.csv` and `factor_audit_log.csv` and writes:

```text
data/output/explain_600519.SH.md
```

The explanation includes composite score, component scores, red flag status, top positive factors, top negative factors, valuation notes, moat proxy notes, limitations, and the safety statement.

## CLI Usage

```bash
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

MVP 6 reports include:

* Data source summary.
* Schema validation summary.
* Point-in-time data summary.
* Future disclosure exclusion counts.
* Factor audit summary.
* Top score tables.
* Excluded or blocked stock reasons where available.
* Backtest metrics and charts.
* Safety statement.

## Notifications

Notification summary remains dry-run by default:

```text
data/output/notify_payload.json
data/output/notify_summary.md
```

No real notification is sent unless explicitly configured in a later phase. If real sending is ever enabled, webhook values must come from environment variables and must not be committed.

## Audit Logs

MVP 6 writes:

```text
data/output/decision_audit_log.csv
```

New stages include:

* `data_source`
* `schema_validation`
* `point_in_time`
* `factor_audit`
* `explain_score`

New decision types include:

* `validate_schema`
* `build_point_in_time`
* `exclude_future_disclosure`
* `explain_factor`
* `generate_factor_audit`

Audit logs are sanitized and must not contain tokens, secrets, passwords, credentials, webhook URLs, real account data, or real broker information.

## Current Limitations

* Only local sample CSV data is supported.
* No real network data source is implemented.
* No paid data source is implemented.
* No real broker integration exists.
* No live trading mode exists.
* HTML reports are static.
* Backtest data is quarterly sample data, not a full daily A-share database.
* Rebalance-day valuation still uses MVP proxy assumptions where point-in-time valuation fields are not present.

## Next Phase

Recommended Phase 7 work:

1. Add richer point-in-time valuation snapshots.
2. Add data-source adapter interfaces with mocked providers only.
3. Add factor drilldown charts in HTML reports.
4. Add stronger schema versioning and migration checks.
5. Add explicit integration-test harnesses that mock any future network provider.

## Disclaimer

This project is for personal research and system development only.

It does not provide investment advice, does not guarantee returns, does not support real-money trading, has no real broker connection, and has no real network data source connection.
