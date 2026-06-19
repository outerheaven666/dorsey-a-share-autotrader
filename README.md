# Dorsey A-Share Autotrader

A-share low-frequency rules-based automated trading system based on Pat Dorsey's fundamental investing framework.

Current phase: **MVP 10 / Pre-Live Safety Gate**.

This project does **not** perform real-money trading. It only reads local sample CSV files, local fixture CSV files, validates schemas, validates adapter and schema migration contracts, renders local static reports, builds point-in-time visible datasets, checks data quality, builds scores and target portfolios, runs paper broker simulation, runs local quarterly backtests, generates reports, writes dry-run notification summaries, and records local audit logs.

## Safety Statement

This system is for personal research, system development, paper trading, and backtest simulation only.

It does not provide investment advice. It does not guarantee returns. It does not support real trading. It has no real broker connection. It has no real network data source connection. It has no real broker credentials and no live order placement path.

`MockAShareProvider` is not an actual market data source. It reads fake local fixture CSV files and exists only to test future adapter contracts. The real provider template is disabled by default, non-executable, not registered, and will not connect to real providers. Schema migration metadata is used only for data-integration readiness checks and does not participate in trading decisions. The pre-live safety gate blocks live trading, real broker access, real orders, and real network data by default.

## Configuration

Default configuration:

```text
config/default.yaml
```

MVP 10 adds:

* `pre_live_safety`: research-only default mode, allowed/forbidden modes, required pre-checks, manual acknowledgement phrase, and hard blockers for live trading, real broker, real order, and real network data.
* `execution_policy`: current execution mode and explicit allow flags for local CSV, mock provider, paper trading, backtest, dry-run notification, live trading, real broker, real orders, and real network data.

Critical defaults:

```text
execution_policy.mode = research_only
allow_live_trading = false
allow_real_broker = false
allow_real_orders = false
allow_real_network_data = false
pre_live_safety.block_live_trading = true
pre_live_safety.block_real_broker = true
pre_live_safety.block_real_network_provider = true
```

No API token, password, secret, webhook, account, or paid data source credential is stored in the repository.

## Pre-Live Safety Gate

Run:

```bash
python -m dorsey_as check-pre-live-safety --config config/default.yaml
```

Outputs:

```text
data/output/pre_live_safety_report.csv
data/output/pre_live_safety_summary.md
```

`pre_live_safety_report.csv` fields:

```text
gate,check_type,status,severity,blocking,message
```

The safety gate checks:

* execution policy mode
* live trading flag
* real broker flag
* real order flag
* real network data flag
* schema validation readiness
* provider contract validation readiness
* contract diff readiness
* schema migration readiness
* data quality readiness
* point-in-time readiness
* factor audit readiness
* backtest-before-paper policy
* paper-before-live policy
* safety acknowledgement phrase
* credential-like assignment strings

Default research-only configuration passes the safety gate while clearly showing that live trading is blocked.

## Execution Policy

Allowed in the current phase:

* local CSV
* mock provider contract tests
* paper trading simulation
* backtest simulation
* dry-run notification

Forbidden in the current phase:

* live trading
* real broker connections
* real order placement
* real network data providers

## Safety Acknowledgement

The configured acknowledgement phrase is:

```text
I understand this system is research-only and live trading is disabled
```

This is local metadata only. It does not enable live trading.

## Explain Safety

Run:

```bash
python -m dorsey_as explain-safety --config config/default.yaml
```

Output:

```text
data/output/safety_explanation.md
```

The explanation states why the system remains research-only, which features are allowed, which features are forbidden, why live trading and real data are blocked, the manual confirmation phrase, and which pre-checks would be required before any future real provider or broker review.

## Simulate Live Request

Run:

```bash
python -m dorsey_as simulate-live-request --config config/default.yaml
```

Outputs:

```text
data/output/simulated_live_request_report.csv
data/output/simulated_live_request_summary.md
```

`simulated_live_request_report.csv` fields:

```text
request_type,requested_mode,allowed,blocked,reason,safety_gate
```

This command simulates a live/real-broker/real-order request only. It creates no real order, connects to no broker, performs no network request, and is blocked by the safety gate.

## Schema Migration And Contract Diff

Existing MVP 8 commands remain:

```bash
python -m dorsey_as validate-schema-migration --config config/default.yaml
python -m dorsey_as diff-provider-contract --config config/default.yaml
python -m dorsey_as generate-contract-diff-html --config config/default.yaml
```

These checks validate local YAML metadata only. Schema migration metadata and contract diff visualization do not participate in trading decisions.

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

## CLI Usage

```bash
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

## Reports

Markdown and HTML reports are written to:

```text
data/output/run_report.md
data/output/backtest_report.md
data/output/run_report.html
data/output/backtest_report.html
```

MVP 10 reports include:

* pre-live safety summary
* execution policy mode
* live trading blocked status
* real broker blocked status
* real network data blocked status
* dry-run notification status
* paper/backtest status
* safety acknowledgement status
* statement that the system has no live trading, no real broker, no real orders, and no real network data

## Audit Logs

Output:

```text
data/output/decision_audit_log.csv
```

MVP 10 adds stages:

* `pre_live_safety`
* `execution_policy`
* `safety_acknowledgement`
* `simulated_live_request`

MVP 10 adds decision types:

* `evaluate_safety_gate`
* `block_live_trading`
* `block_real_broker`
* `block_real_order`
* `block_real_network_data`
* `validate_safety_ack`
* `simulate_live_request`
* `allow_research_only`
* `allow_paper_mode`
* `allow_backtest_mode`
* `allow_dry_run_notify`

Audit logs are sanitized and must not contain tokens, secrets, passwords, credentials, webhook URLs, real account data, or real broker information.

## Why No Real Data Source Or Broker Yet

Future real providers or brokers must first pass:

* pre-live safety gate
* validate-provider-contract
* diff-provider-contract
* validate-schema-migration
* generate-contract-diff-html
* point-in-time checks
* schema validation
* data quality checks
* factor audit checks
* backtest before paper
* paper before any future live review

Even then, real providers and real brokers remain disabled until a later explicitly approved milestone. No real trading path exists.

## Current Limitations

* Only local sample CSV data is used by scoring and backtesting.
* Mock provider reads fake local fixtures only.
* Contract diff, migration, and safety checks are local metadata checks.
* Pre-live safety gate is a local dry-run guard.
* No real network data source is implemented.
* No paid data source is implemented.
* No real broker integration exists.
* No live trading mode exists.
* Backtest data is quarterly sample data, not a full daily A-share database.

## Next Phase

Recommended Phase 11 work:

1. Add richer safety checklist dashboards.
2. Add immutable audit snapshots for release candidates.
3. Add manual review packet generation.
4. Add read-only provider dry-run harness with local fixtures only.
5. Add stronger reconciliation checks before any future broker design.

## Disclaimer

This project is for personal research and system development only.

It does not provide investment advice, does not guarantee returns, does not support real-money trading, has no real broker connection, has no real network data source connection, and only supports paper trading and backtest simulation. Mock provider is only used for contract testing and is not an actual market data source. Real provider template is disabled by default, non-executable, and will not connect to real providers. Schema migration metadata is used only for pre-integration checks and does not participate in trading decisions. Pre-live safety gate blocks live trading, real broker, real order, and real network data by default.
