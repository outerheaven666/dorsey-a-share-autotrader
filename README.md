# Dorsey A-Share Autotrader

Research-only A-share low-frequency fundamental quant system inspired by Pat Dorsey's moat framework.

This project is not an investment advisory product. It does not guarantee returns. It does not support real trading. It has no real broker connection and no real network data source connection. It is only for personal research, system development, local CSV scoring, paper trading simulation, backtest simulation, dry-run notification, and adapter contract testing.

Mock provider is only used for contract tests and is not an actual market data source. The real provider template is disabled by default, non-executable, and never connects to external systems. Schema migration metadata is only for data integration readiness checks and does not participate in trading decisions. Pre-live safety gate blocks live trading, real broker, real order, and real network data by default. System health and release checklist only generate local reports; they do not commit, tag, push, publish, or create releases automatically.

## Architecture Review

- [v0.11.0 Architecture Review](docs/architecture/v0.11.0_architecture_review.md)
- [v0.11.0 Capability Map](docs/architecture/v0.11.0_capability_map.md)
- [v0.11.0 Pre-Real-Data Gap Analysis](docs/architecture/v0.11.0_pre_real_data_gap_analysis.md)
- [v0.11.0 Stop Doing List](docs/architecture/v0.11.0_stop_doing_list.md)

## Install

```bash
python -m pip install -e .
python -m pip install pytest
```

Python 3.11 or higher is expected.

## Sample Data

Default local CSV files live under `data/sample/`:

- `stock_basic.csv`
- `financial_snapshot.csv`
- `market_snapshot.csv`
- `historical_market_snapshot.csv`
- `trading_calendar.csv`
- `data_quality_cases.csv`

Backtest, paper trading, report, health, and release outputs are written to `data/output/`, which is ignored by git.

## Configuration

Default config:

```bash
config/default.yaml
```

Key sections:

- `scoring`: quality, moat, valuation, and risk weights.
- `portfolio`: max positions, single-stock weight, industry cap, cash reserve.
- `transaction_cost`: commission, minimum commission, stamp duty, slippage.
- `backtest`: initial cash, frequency, benchmark placeholder, risk-free rate.
- `data_quality`: stale data and blocking behavior.
- `data_source`: local CSV paths; `mode` is `local_csv` and network is disabled.
- `point_in_time`: as-of-date and disclosure-date rules.
- `adapter_contract`: mock-only provider contract tests.
- `schema_versioning`: contract versioning and baseline/candidate diff paths.
- `schema_migration`: migration metadata, deprecation lifecycle, compatibility window.
- `pre_live_safety`: safety gate and acknowledgement controls.
- `execution_policy`: research-only execution permissions.
- `system_health`: v0.11.0 health check settings.
- `release_checklist`: local release candidate checklist settings.
- `sensitive_scan`: credential-like string and forbidden SDK import scanning.

All commands accept:

```bash
--config config/default.yaml
```

## Core CLI

```bash
python -m dorsey_as validate-schema --config config/default.yaml
python -m dorsey_as check-data-quality --config config/default.yaml
python -m dorsey_as run-score --config config/default.yaml
python -m dorsey_as build-portfolio --config config/default.yaml
python -m dorsey_as paper-rebalance --config config/default.yaml
python -m dorsey_as run-backtest --config config/default.yaml
python -m dorsey_as generate-report --config config/default.yaml
python -m dorsey_as notify-summary --config config/default.yaml
```

`notify-summary` is dry-run by default. It writes local summary files and does not send network notifications unless a later explicitly approved milestone changes that boundary.

## Point-in-Time And Data Quality

Financial data must respect `disclosure_date <= as_of_date`. If a report belongs to the past but was disclosed after the current `as_of_date`, it is not visible at that point in time and must not be used for scoring or backtesting.

Useful commands:

```bash
python -m dorsey_as validate-schema --config config/default.yaml
python -m dorsey_as check-data-quality --config config/default.yaml
```

Outputs:

- `data/output/schema_validation_report.csv`
- `data/output/data_quality_report.csv`
- `data/output/point_in_time_snapshot.csv`

## Factor Audit And Explain Score

Scoring writes factor-level audit data so composite score decisions can be traced back to quality, moat, valuation, risk, and red-flag reasons.

```bash
python -m dorsey_as run-score --config config/default.yaml
python -m dorsey_as explain-score --symbol 600519.SH --config config/default.yaml
```

Outputs:

- `data/output/scores.csv`
- `data/output/factor_audit_log.csv`
- `data/output/explain_600519.SH.md`

## Adapter Contract Layer

MVP 7 added a mock-only adapter contract layer for future A-share data provider readiness. It defines the provider contract, fixture mapping, field normalization, schema validation, and point-in-time compatibility checks.

Current provider status:

- Local CSV sample path is the default production path.
- `MockAShareProvider` only reads fake local fixtures.
- Real network data sources such as AkShare, Tushare, Wind, Choice, JQData, Tonghuashun, JoinQuant, QMT, and PTrade are not connected.
- Real provider names are rejected by the registry.

Commands:

```bash
python -m dorsey_as validate-provider-contract --config config/default.yaml
python -m dorsey_as explain-provider --config config/default.yaml
```

Outputs:

- `data/output/provider_contract_report.csv`
- `data/output/provider_contract_summary.md`
- `data/output/adapter_mapped_preview.csv`
- `data/output/provider_explanation.md`

## Schema Versioning And Contract Diff

MVP 8 added schema contract YAML files and diff reporting:

- `config/schemas/provider_contract_v1.yaml`
- `config/schemas/provider_contract_candidate.yaml`

Change classes:

- Breaking: required field deletion, required field type change, primary key change, dataset deletion, date/numeric/boolean semantic break.
- Additive: new optional field, documented extra field, non-breaking dataset addition.
- Compatible: optional metadata or compatible alias changes that do not block current readers.

Command:

```bash
python -m dorsey_as diff-provider-contract --config config/default.yaml
```

Outputs:

- `data/output/provider_contract_diff_report.csv`
- `data/output/provider_contract_diff_summary.md`

## Schema Migration Metadata

MVP 9 added schema migration metadata, deprecation lifecycle, compatibility windows, and static contract diff visualization.

Default migration plan:

```bash
config/schema_migrations/v1_to_v1_1.yaml
```

Commands:

```bash
python -m dorsey_as validate-schema-migration --config config/default.yaml
python -m dorsey_as generate-contract-diff-html --config config/default.yaml
```

Outputs:

- `data/output/schema_migration_report.csv`
- `data/output/schema_migration_summary.md`
- `data/output/provider_contract_diff.html`
- `data/output/provider_contract_diff_visual_summary.md`

Migration metadata is explanatory and pre-integration oriented. It does not participate in trading decisions.

## Pre-Live Safety Gate

MVP 10 added a pre-live safety gate. Default execution mode is `research_only`.

Allowed by default:

- local CSV
- mock provider contract tests
- backtest simulation
- paper trading simulation
- dry-run notification

Blocked by default:

- live trading
- real broker
- real orders
- real network data

Commands:

```bash
python -m dorsey_as check-pre-live-safety --config config/default.yaml
python -m dorsey_as explain-safety --config config/default.yaml
python -m dorsey_as simulate-live-request --config config/default.yaml
```

Outputs:

- `data/output/pre_live_safety_report.csv`
- `data/output/pre_live_safety_summary.md`
- `data/output/safety_explanation.md`
- `data/output/simulated_live_request_report.csv`
- `data/output/simulated_live_request_summary.md`

The simulated live request is intentionally blocked and never creates a real order.

## MVP 11 System Health Check

MVP 11 fixes the project as a v0.11.0 release candidate with local system health checks, sensitive content scanning, artifact manifest generation, release checklist, and release notes draft.

System health checks:

- `config/default.yaml` exists.
- `README.md` exists.
- `data/output/` is ignored by git.
- execution policy disables live trading, real broker, real orders, and real network data.
- pre-live safety blocks live trading, real broker, and real network provider.
- adapter contract remains mock-only.
- disabled provider template is not registered.
- no credential-like assignment is present.
- no real provider SDK import is present.
- required output artifacts are listed in the artifact manifest.
- release notes include the safety boundary.

Sensitive scan checks:

- credential-like assignments such as token, secret, password, webhook URL, credential, broker password, access key, and API key patterns.
- forbidden real provider SDK imports.
- documentation-only mentions of provider names are allowed when used to explain disabled boundaries.

Commands:

```bash
python -m dorsey_as system-health --config config/default.yaml
python -m dorsey_as scan-sensitive-content --config config/default.yaml
python -m dorsey_as release-checklist --config config/default.yaml
python -m dorsey_as generate-release-notes --config config/default.yaml
```

Outputs:

- `data/output/system_health_report.csv`
- `data/output/system_health_summary.md`
- `data/output/sensitive_scan_report.csv`
- `data/output/sensitive_scan_summary.md`
- `data/output/output_artifact_manifest.csv`
- `data/output/output_artifact_manifest.md`
- `data/output/release_checklist.csv`
- `data/output/release_checklist.md`
- `data/output/release_notes_v0.11.0.md`

Output artifact manifest fields:

- `artifact`
- `expected`
- `exists`
- `generated_by`
- `tracked_by_git`
- `note`

Release checklist fields:

- `item`
- `required`
- `status`
- `blocking`
- `evidence`
- `message`

## Reports

Markdown and HTML reports:

```bash
python -m dorsey_as generate-report --config config/default.yaml
```

Outputs:

- `data/output/run_report.md`
- `data/output/run_report.html`
- `data/output/backtest_report.md`
- `data/output/backtest_report.html`

Reports include strategy summaries, backtest summaries, safety statements, data quality summaries, point-in-time summaries, factor audit summaries, schema migration summaries, contract diff summaries, pre-live safety summaries, and MVP 11 system health/release checklist summaries.

## Validation

Full local validation sequence:

```bash
python -m pytest
python -m dorsey_as system-health --config config/default.yaml
python -m dorsey_as scan-sensitive-content --config config/default.yaml
python -m dorsey_as release-checklist --config config/default.yaml
python -m dorsey_as generate-release-notes --config config/default.yaml
python -m dorsey_as check-pre-live-safety --config config/default.yaml
python -m dorsey_as explain-safety --config config/default.yaml
python -m dorsey_as simulate-live-request --config config/default.yaml
python -m dorsey_as validate-schema-migration --config config/default.yaml
python -m dorsey_as diff-provider-contract --config config/default.yaml
python -m dorsey_as generate-contract-diff-html --config config/default.yaml
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

## v0.11.0 Release Candidate Flow

Manual release steps:

1. Run validation commands.
2. Inspect git status.
3. Create PR.
4. Merge PR.
5. Pull main.
6. Run final validation.
7. `git tag v0.11.0`
8. `git push origin v0.11.0`

The project CLI does not perform these git or GitHub actions automatically.

## Current Limitations

- Local sample CSV and fake fixtures only.
- No real broker credentials.
- No real broker connection.
- No real order path.
- No real network data source.
- No live trading mode.
- Mock provider is only for adapter contract tests.
- Reports are static local files.
- Health and release checklist are local pre-release guardrails, not production monitoring.
- Strategy logic is deterministic and intentionally simple.

## Next Stage Suggestions

- Add richer fixture coverage for data vendor schema drift.
- Add CI workflow that runs the validation command set without secrets.
- Add signed artifact checksums for `data/output/` reports.
- Add benchmark comparison while keeping local-only sample data.
- Only consider real provider design after contract, schema, migration, point-in-time, data quality, factor audit, pre-live safety, and release health gates are fully reviewed in a later explicitly approved milestone.
