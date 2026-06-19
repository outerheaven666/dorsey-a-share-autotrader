# Dorsey A-Share Autotrader

A-share low-frequency rules-based automated trading system based on Pat Dorsey's fundamental investing framework.

Current phase: **MVP 5 / HTML Reports, Charts, Dry-Run Notifications, Audit Logs, Paper Trading, and Local Backtesting**.

This project does **not** perform real-money trading. It only reads local sample CSV files, checks data quality, builds scores and target portfolios, runs paper broker simulation, runs local quarterly backtests, generates reports, writes dry-run notification summaries, and records local audit logs.

## Safety Statement

This system is for personal research, system development, paper trading, and backtest simulation only.

It does not provide investment advice. It does not guarantee returns. It does not support real trading. It has no real broker connection, no QMT adapter, no PTrade adapter, no real broker credentials, and no live order placement path.

## Installation

Use Python 3.11 or higher.

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

## Configuration

Default configuration:

```text
config/default.yaml
```

Use it explicitly:

```bash
python -m dorsey_as run-backtest --config config/default.yaml
```

Key sections:

* `scoring`: composite score weights. Weights must be non-negative and sum to `1.0`.
* `portfolio`: max positions, max stock weight, max industry weight, and cash reserve.
* `transaction_cost`: commission, minimum commission, stamp duty, and slippage.
* `backtest`: initial cash, rebalance frequency, benchmark placeholder, and risk-free rate.
* `data_quality`: stale thresholds and blocking switches for missing fields, look-ahead bias, and severe outliers.
* `report`: enables Markdown/HTML output, equity curve chart, drawdown chart, trade table, holdings table, data quality table, and audit summary.
* `notify`: default `enabled: false`, `mode: dry_run`, `channel: feishu`, `webhook_url_env: FEISHU_WEBHOOK_URL`.
* `audit`: controls score, portfolio, backtest, rejected trade, and data quality audit logging.

No webhook URL, token, secret, account, or broker credential is stored in the repository. If notification sending is ever explicitly enabled, the Feishu webhook must come from the `FEISHU_WEBHOOK_URL` environment variable. MVP 5 still does not perform real network sending by default.

## Sample Data

The MVP reads local CSV files from `data/sample/`:

```text
stock_basic.csv
financial_snapshot.csv
market_snapshot.csv
historical_market_snapshot.csv
trading_calendar.csv
data_quality_cases.csv
```

Financial snapshots include `report_date` and `disclosure_date`. At any `as_of_date`, the system may only use rows where:

```text
disclosure_date <= as_of_date
```

This protects scoring and backtesting from look-ahead bias.

## CLI Usage

Check data quality:

```bash
python -m dorsey_as check-data-quality --config config/default.yaml
```

Generate stock scores:

```bash
python -m dorsey_as run-score --config config/default.yaml
```

Build a target portfolio:

```bash
python -m dorsey_as build-portfolio --config config/default.yaml
```

Run one paper rebalance:

```bash
python -m dorsey_as paper-rebalance --config config/default.yaml
```

Run the local quarterly backtest:

```bash
python -m dorsey_as run-backtest --config config/default.yaml
```

Generate Markdown and HTML reports from existing CSV outputs:

```bash
python -m dorsey_as generate-report --config config/default.yaml
```

Generate a dry-run notification summary:

```bash
python -m dorsey_as notify-summary --config config/default.yaml
```

Global data/output overrides:

```bash
python -m dorsey_as --data-dir data/sample --output-dir data/output run-backtest --config config/default.yaml
```

## Data Quality Layer

The data quality gate runs before scoring, portfolio construction, paper rebalance, and each backtest rebalance date.

Checks include:

* Data availability.
* Missing core fields.
* Look-ahead bias via `disclosure_date`.
* Stale financial data.
* Severe outliers such as non-positive prices, invalid market cap, invalid PB, negative revenue, negative assets, invalid gross margin, and extreme net margin.

Output:

```text
data/output/data_quality_report.csv
```

Backtest data-quality audit output:

```text
data/output/backtest_audit_log.csv
```

## Reports And Charts

MVP 5 generates both Markdown and static HTML reports:

```text
data/output/run_report.md
data/output/backtest_report.md
data/output/run_report.html
data/output/backtest_report.html
```

HTML reports use pure HTML/CSS/SVG. They do not depend on external CDNs or frontend frameworks.

`backtest_report.html` includes:

* Title and generated time.
* Safety statement.
* Config summary.
* Backtest range, initial cash, and ending equity.
* Total return, annualized return, max drawdown, Sharpe ratio, turnover, number of trades, and win rate.
* Equity curve SVG chart.
* Drawdown SVG chart.
* Trade summary table.
* Final holdings table.
* Data quality summary.
* Audit log summary.
* Current limitations.

If chart data is missing, the HTML report shows “Insufficient data, unable to generate chart” instead of crashing.

## Notification Summary

MVP 5 adds a local notification summary workflow:

```text
data/output/notify_payload.json
data/output/notify_summary.md
```

Default behavior:

* `notify.enabled` is `false`.
* `notify.mode` is `dry_run`.
* No real notification is sent.
* The system writes the payload and summary files for review.

If `notify.enabled=true` and `notify.mode=send` but `FEISHU_WEBHOOK_URL` is missing, the system refuses to send and reports the missing environment variable. No real webhook is stored in this repo.

The notification summary includes data quality counts, total return, max drawdown, Sharpe ratio, number of trades, report paths, and the safety statement.

## Decision Audit Log

MVP 5 adds a broader decision audit log:

```text
data/output/decision_audit_log.csv
```

Fields:

```text
run_id,timestamp,stage,as_of_date,symbol,decision_type,decision,reason,input_summary,output_summary,severity
```

Stages include data quality, scoring, portfolio, paper broker, backtest, reporting, and notify. The audit log records key decisions such as score generation, selected positions, skipped/rejected trades, report generation, and dry-run notifications.

Audit records are sanitized and must not contain webhook URLs, tokens, secrets, or credentials.

## Backtesting

The local backtest validates research and portfolio rules before any real trading work exists.

At each rebalance date, the engine:

1. Runs data quality and look-ahead checks.
2. Loads eligible point-in-time financial rows.
3. Runs the configured scoring engine.
4. Builds the configured target portfolio.
5. Generates simulated trades.
6. Applies A-share trading restrictions.
7. Deducts configured transaction costs.
8. Updates cash and holdings.
9. Marks positions to market.
10. Writes CSV outputs and reports.

Backtest outputs:

```text
data/output/backtest_equity_curve.csv
data/output/backtest_trades.csv
data/output/backtest_holdings.csv
data/output/backtest_metrics.csv
data/output/backtest_audit_log.csv
data/output/backtest_report.md
data/output/backtest_report.html
```

## Current Limitations

* Only local sample CSV data is supported.
* Config parsing supports the simple YAML shape used by `config/default.yaml`.
* HTML reports are static and intentionally simple.
* Charts are simple inline SVG charts without interaction.
* Notification is dry-run by default; MVP 5 does not send real network notifications.
* The backtest uses simple quarterly sample data, not a full daily A-share database.
* Rebalance-day valuation uses MVP proxy market assumptions for fields not present in the historical close-price file.
* No real broker integration exists.
* No live trading mode exists.

## Next Phase

Recommended Phase 6 work:

1. Add richer point-in-time valuation data.
2. Add optional HTML chart styling and report templates.
3. Add explicit, opt-in Feishu sending with integration tests using mocked network calls.
4. Add deeper score factor drilldowns in audit logs and reports.
5. Define broker adapter interfaces while keeping all live adapters disabled by default.

## Disclaimer

This project is for personal research and system development only.

It does not provide investment advice, does not guarantee returns, and does not support real-money trading.
