# Dorsey A-Share Autotrader

A-share low-frequency rules-based automated trading system based on Pat Dorsey's fundamental investing framework.

Current phase: **MVP 9 / Schema Migration Metadata and Contract Diff Visualization**.

This project does **not** perform real-money trading. It only reads local sample CSV files, local fixture CSV files, validates schemas, validates schema migration metadata, diffs provider contract YAML files, renders local static contract diff reports, builds point-in-time visible datasets, checks data quality, builds scores and target portfolios, runs paper broker simulation, runs local quarterly backtests, generates reports, writes dry-run notification summaries, and records local audit logs.

## Safety Statement

This system is for personal research, system development, paper trading, and backtest simulation only.

It does not provide investment advice. It does not guarantee returns. It does not support real trading. It has no real broker connection. It has no real network data source connection. It has no real broker credentials and no live order placement path.

`MockAShareProvider` is not an actual market data source. It reads fake local fixture CSV files and exists only to test future adapter contracts. The real provider template is disabled by default, non-executable, not registered, and will not connect to real providers. Schema migration metadata is used only for data-integration readiness checks and does not participate in trading decisions.

## Configuration

Default configuration:

```text
config/default.yaml
```

MVP 9 adds:

* `schema_migration`: current/target version, migration plan path, compatibility window, deprecation blocking, missing-plan blocking, pending deprecation warnings, and backward-compatible aliases.
* `contract_visualization`: static HTML/Markdown visualization settings for contract diff, field lifecycle, migration steps, and compatibility matrix.

Existing safety defaults remain:

* `data_source.mode` is `local_csv`.
* `adapter_contract.mode` is `mock_only`.
* `allow_network` is `false`.
* `allow_real_provider` is `false`.
* `provider_templates.real_provider_templates_enabled` is `false`.

No API token, password, secret, webhook, account, or paid data source credential is stored in the repository.

## Schema Migration Metadata

Default migration plan:

```text
config/schema_migrations/v1_to_v1_1.yaml
```

The migration plan contains:

```text
from_version
to_version
effective_date
compatibility_window_days
migration_summary
field_migrations
deprecated_fields
aliases
breaking_changes
additive_changes
required_actions
rollback_notes
safety_notes
```

Each field migration contains:

```text
dataset
old_field
new_field
change_type
status
effective_date
deprecation_date
removal_date
backward_compatible
migration_rule
reason
```

Supported lifecycle statuses:

```text
active
deprecated
pending_removal
removed
```

The default migration plan is intentionally non-blocking. Breaking migration examples live only in:

```text
data/fixtures/schema_migration_cases/
```

## Field Deprecation Lifecycle

The migration validator checks:

* Version pair consistency.
* Compatibility window.
* Missing migration rules.
* Pending deprecations.
* Expired deprecations.
* Backward-compatible aliases.
* Breaking changes without required actions.

`schema_migration.compatibility_window_days` defaults to `180`.

Expired deprecations are blocking by default. Pending deprecations are warnings by default.

## Validate Schema Migration

Run:

```bash
python -m dorsey_as validate-schema-migration --config config/default.yaml
```

Outputs:

```text
data/output/schema_migration_report.csv
data/output/schema_migration_summary.md
```

`schema_migration_report.csv` fields:

```text
from_version,to_version,dataset,field,check_type,status,severity,message
```

`schema_migration_summary.md` includes version pair, effective date, compatibility window, total migrations, deprecated fields, pending removals, expired deprecations, blocking decision, required actions, safety boundary, and limitations.

## Contract Diff Visualization

Run:

```bash
python -m dorsey_as generate-contract-diff-html --config config/default.yaml
```

Outputs:

```text
data/output/provider_contract_diff.html
data/output/provider_contract_diff_visual_summary.md
```

The HTML report is static, uses no external CDN, and includes:

* Baseline contract path.
* Candidate contract path.
* From/to migration versions.
* Total changes.
* Breaking/additive/compatible change counts.
* Dataset summary table.
* Field lifecycle table.
* Migration steps table.
* Compatibility matrix.
* Disabled provider template status.
* Safety boundary.

## Schema Versioning And Contract Diff

Provider contracts are local static YAML files:

```text
config/schemas/provider_contract_v1.yaml
config/schemas/provider_contract_candidate.yaml
```

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

Contract diff detects breaking, additive, and compatible changes. It is a data-adapter readiness check and does not participate in trading decisions.

## Adapter Contract Layer

The only implemented provider is:

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

It is disabled by default, non-executable, not registered, not reachable from CLI, and contains no real SDK import, endpoint, credential, or network path.

## Explain Provider

Run:

```bash
python -m dorsey_as explain-provider --config config/default.yaml
```

Output:

```text
data/output/provider_explanation.md
```

The explanation includes schema migration status, current/target version, migration plan path, compatibility window, field lifecycle rules, contract diff HTML capability, and the checks required before any future real provider can be considered.

## CLI Usage

```bash
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

## Reports

Markdown and HTML reports are written to:

```text
data/output/run_report.md
data/output/backtest_report.md
data/output/run_report.html
data/output/backtest_report.html
```

MVP 9 reports include:

* Schema migration summary.
* Current/target version.
* Migration plan path.
* Compatibility window.
* Deprecated and expired deprecation counts.
* Contract diff visualization status.
* Statement that migration metadata does not participate in trading decisions.
* Safety boundary.

## Audit Logs

Output:

```text
data/output/decision_audit_log.csv
```

MVP 9 adds stages:

* `schema_migration`
* `contract_visualization`
* `field_lifecycle`
* `compatibility_matrix`

MVP 9 adds decision types:

* `load_migration_plan`
* `validate_migration_plan`
* `detect_expired_deprecation`
* `detect_pending_deprecation`
* `validate_compatibility_window`
* `generate_contract_diff_html`
* `generate_compatibility_matrix`
* `block_schema_migration`

Audit logs are sanitized and must not contain tokens, secrets, passwords, credentials, webhook URLs, real account data, or real broker information.

## Why No Real Data Source Yet

Future real providers must first pass:

* `validate-provider-contract`
* `diff-provider-contract`
* `validate-schema-migration`
* `generate-contract-diff-html`
* point-in-time checks
* schema validation
* data quality checks
* factor audit checks

Even then, real providers remain disabled until a later explicitly approved milestone. No real trading path exists.

## Current Limitations

* Only local sample CSV data is used by scoring and backtesting.
* Mock provider reads fake local fixtures only.
* Contract diff and migration checks local YAML only.
* Migration metadata does not participate in trading decisions.
* No real network data source is implemented.
* No paid data source is implemented.
* No real broker integration exists.
* No live trading mode exists.
* Backtest data is quarterly sample data, not a full daily A-share database.

## Next Phase

Recommended Phase 10 work:

1. Add richer schema migration visual diffs by dataset.
2. Add migration timeline charts in static HTML.
3. Add provider contract compatibility scorecards.
4. Add point-in-time valuation migration metadata.
5. Add fixture coverage for restatements and corporate actions.

## Disclaimer

This project is for personal research and system development only.

It does not provide investment advice, does not guarantee returns, does not support real-money trading, has no real broker connection, has no real network data source connection, and only supports paper trading and backtest simulation. Mock provider is only used for contract testing and is not an actual market data source. Real provider template is disabled by default, non-executable, and will not connect to real providers. Schema migration metadata is used only for pre-integration checks and does not participate in trading decisions.
