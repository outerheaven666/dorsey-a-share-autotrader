# Dorsey A-Share Autotrader

A-share low-frequency rules-based automated trading system based on Pat Dorsey's fundamental investing framework.

Current phase: **MVP 8 / Schema Versioning and Provider Contract Diff**.

This project does **not** perform real-money trading. It only reads local sample CSV files, local fixture CSV files, validates schemas, diffs provider contract YAML files, builds point-in-time visible datasets, checks data quality, builds scores and target portfolios, runs paper broker simulation, runs local quarterly backtests, generates reports, writes dry-run notification summaries, and records local audit logs.

## Safety Statement

This system is for personal research, system development, paper trading, and backtest simulation only.

It does not provide investment advice. It does not guarantee returns. It does not support real trading. It has no real broker connection. It has no real network data source connection. It has no real broker credentials, and no live order placement path.

`MockAShareProvider` is not an actual market data source. It reads fake local fixture CSV files and exists only to test future adapter contracts. The real provider template is disabled by default, non-executable, not registered, and will not connect to real providers.

## Configuration

Default configuration:

```text
config/default.yaml
```

Important sections:

* `data_source`: production path for local CSV sample data. Default mode is `local_csv`, provider is `sample_csv`, and `allow_network` is `false`.
* `adapter_contract`: contract-test-only adapter settings. Default mode is `mock_only`, provider is `mock_a_share`, `allow_network` is `false`, and `allow_real_provider` is `false`.
* `schema_versioning`: contract version settings. Default current version is `v1`, baseline contract is `config/schemas/provider_contract_v1.yaml`, candidate contract is `config/schemas/provider_contract_candidate.yaml`, and breaking changes block by default.
* `contract_diff`: controls comparison of dataset presence, required fields, field types, date fields, numeric fields, and boolean fields.
* `provider_templates`: keeps real provider templates disabled and non-executable.
* `field_mapping`, `schema_validation`, `point_in_time`, `factor_audit`, `data_quality`, `report`, `notify`, and `audit`: retain previous MVP behavior.

No API token, password, secret, webhook, account, or paid data source credential is stored in the repository.

## Schema Versioning

Provider contracts are local static YAML files:

```text
config/schemas/provider_contract_v1.yaml
config/schemas/provider_contract_candidate.yaml
```

Each dataset contract defines:

```text
required_fields
optional_fields
field_types
date_fields
numeric_fields
boolean_fields
primary_key
version
description
```

Covered datasets:

```text
stock_basic
financial_snapshot
market_snapshot
historical_market_snapshot
trading_calendar
```

## Contract Diff

Run:

```bash
python -m dorsey_as diff-provider-contract --config config/default.yaml
```

Outputs:

```text
data/output/provider_contract_diff_report.csv
data/output/provider_contract_diff_summary.md
```

`provider_contract_diff_report.csv` fields:

```text
dataset,field,change_type,severity,baseline_value,candidate_value,breaking,message
```

Change categories:

* Breaking change: deleted required field, required field type change, primary key change, deleted dataset, date/numeric/boolean field category regression.
* Additive change: new optional field, new dataset, documented extra field.
* Compatible change: no detected breaking change and no required contract regression.

If `schema_versioning.block_on_breaking_change` is `true`, breaking changes produce a blocking decision. The default candidate contract is compatible/additive only, so the standard validation flow can run through. Breaking fixtures are stored under:

```text
data/fixtures/contract_diff_cases/
```

## Adapter Contract Layer

The adapter contract defines a `DataProvider` interface with:

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

It reads fake local fixtures from:

```text
data/fixtures/mock_provider/
```

`MockAShareProvider` is not used by `run-score` or `run-backtest`. It is only used by `validate-provider-contract`.

## Disabled Real Provider Template

The template lives at:

```text
src/dorsey_as/adapters/templates/real_provider_template.py
```

It is disabled by default, non-executable, not registered, not reachable from CLI, and contains no real SDK import, endpoint, credential, or network path. It exists only as documentation-oriented scaffolding for a later approved milestone.

## Provider Contract Validation

Run:

```bash
python -m dorsey_as validate-provider-contract --config config/default.yaml
```

Outputs:

```text
data/output/provider_contract_report.csv
data/output/provider_contract_summary.md
data/output/adapter_mapped_preview.csv
```

This command only validates the mock provider fixtures, field mapping, schema compatibility, duplicate keys, numeric parsing, and point-in-time compatibility.

## Explain Provider

Run:

```bash
python -m dorsey_as explain-provider --config config/default.yaml
```

Output:

```text
data/output/provider_explanation.md
```

The explanation includes the current data source mode, adapter mode, provider, schema contract version, baseline and candidate contract paths, contract diff status, disabled template status, why no real provider exists now, and what future providers must satisfy.

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

## Point-In-Time Data

Financial snapshots include `report_date` and `disclosure_date`. At any `as_of_date`, the system may only use rows where:

```text
disclosure_date <= as_of_date
```

Output:

```text
data/output/point_in_time_snapshot.csv
```

## Factor Audit Drilldown

Output:

```text
data/output/factor_audit_log.csv
```

Fields:

```text
run_id,timestamp,as_of_date,symbol,factor_group,factor_name,raw_value,normalized_value,component_score,weight,weighted_score,reason,severity
```

## CLI Usage

```bash
python -m dorsey_as diff-provider-contract --config config/default.yaml
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

MVP 8 reports include:

* Data source summary.
* Adapter contract summary.
* Schema versioning summary.
* Current contract version.
* Contract diff status.
* Breaking and additive change counts.
* Disabled provider template status.
* Real data source status: not enabled.
* Network data source status: disabled.
* Backtest statement that contract diff does not participate in trading decisions.
* Safety statement.

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

MVP 8 adds stages:

* `schema_versioning`
* `contract_diff`
* `provider_template`

MVP 8 adds decision types:

* `load_schema_contract`
* `diff_schema_contract`
* `detect_breaking_change`
* `detect_additive_change`
* `reject_real_provider_template`
* `block_contract_change`

Audit logs are sanitized and must not contain tokens, secrets, passwords, credentials, webhook URLs, real account data, or real broker information.

## Future Real Provider Requirements

A future real data provider must satisfy all of these before it can be considered:

* Implement the `DataProvider` contract.
* Pass provider contract validation.
* Pass schema versioning and contract diff checks.
* Map all required fields into the internal schema.
* Provide point-in-time compatible `disclosure_date`.
* Pass schema validation, data quality checks, duplicate-key checks, and numeric parsing checks.
* Stay disabled by default until a later explicitly approved milestone.
* Keep all credentials outside the repository.

## Current Limitations

* Only local sample CSV data is used by scoring and backtesting.
* Mock provider reads fake local fixtures only.
* Contract diff checks local YAML files only.
* No real network data source is implemented.
* No paid data source is implemented.
* No real broker integration exists.
* No live trading mode exists.
* Backtest data is quarterly sample data, not a full daily A-share database.

## Next Phase

Recommended Phase 9 work:

1. Add schema migration metadata and version compatibility windows.
2. Add richer corporate-action and financial-restatement fixtures.
3. Add provider contract diff visualization in HTML reports.
4. Add disabled-by-default provider adapter scaffolding tests.
5. Add point-in-time valuation snapshot contract coverage.

## Disclaimer

This project is for personal research and system development only.

It does not provide investment advice, does not guarantee returns, does not support real-money trading, has no real broker connection, has no real network data source connection, and only supports paper trading and backtest simulation. Mock provider is only used for contract testing and is not an actual market data source. Real provider template is disabled by default, non-executable, and will not connect to real providers.
