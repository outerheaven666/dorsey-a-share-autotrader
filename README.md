# Dorsey A-Share Autotrader

A-share low-frequency rules-based automated trading system based on Pat Dorsey's fundamental investing framework.

Current phase: **MVP 4 / Configurable Research, Reporting, Paper Trading, and Local Backtesting**.

This project does **not** perform real-money trading. It only reads local sample CSV files, checks data quality, builds scores and target portfolios, runs paper broker simulation, runs local quarterly backtests, and generates Markdown reports.

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

Default configuration lives at:

```text
config/default.yaml
```

All CLI commands use this file when `--config` is not supplied. You can pass a custom config:

```bash
python -m dorsey_as run-backtest --config config/default.yaml
```

### Config Sections

`scoring` controls composite score weights:

```yaml
scoring:
  quality_weight: 0.35
  moat_weight: 0.30
  valuation_weight: 0.25
  risk_weight: 0.10
```

Weights must be non-negative and sum to `1.0`.

`portfolio` controls target portfolio constraints:

```yaml
portfolio:
  max_positions: 20
  max_stock_weight: 0.05
  max_industry_weight: 0.25
  cash_reserve: 0.05
```

`transaction_cost` controls simulated trade costs:

```yaml
transaction_cost:
  commission_rate: 0.0003
  minimum_commission: 5
  stamp_duty_rate: 0.0005
  slippage_rate: 0.001
```

`backtest` controls simulation assumptions:

```yaml
backtest:
  initial_cash: 1000000
  rebalance_frequency: quarterly
  benchmark_symbol: ""
  risk_free_rate: 0.0
```

`data_quality` controls validation behavior:

```yaml
data_quality:
  stale_days_threshold: 450
  severe_stale_days_threshold: 900
  allow_stale_warning: true
  block_on_missing_core_fields: true
  block_on_lookahead_bias: true
  block_on_severe_outlier: true
```

`report` controls Markdown report sections:

```yaml
report:
  output_format: markdown
  include_data_quality_summary: true
  include_top_scores: true
  include_trade_summary: true
  include_backtest_metrics: true
  include_holdings_snapshot: true
```

Invalid configs, such as missing files, negative fees, negative weights, or scoring weights that do not sum to `1.0`, are rejected before running.

## Sample Data

The MVP reads local CSV files from `data/sample/`.

```text
stock_basic.csv
financial_snapshot.csv
market_snapshot.csv
historical_market_snapshot.csv
trading_calendar.csv
data_quality_cases.csv
```

Financial snapshots include `report_date` and `disclosure_date`. At any `as_of_date`, the system may only use financial rows where:

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

Generate Markdown reports from existing CSV outputs:

```bash
python -m dorsey_as generate-report --config config/default.yaml
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

The backtest also writes:

```text
data/output/backtest_audit_log.csv
```

## Reports

MVP 4 generates readable Markdown reports in `data/output/`.

`run_report.md` includes:

* Run time.
* Config path.
* Data quality summary.
* Blocking issue status.
* Score row count.
* Top 10 stock score summary.
* Target portfolio summary.
* PaperBroker simulated trade summary.
* Safety statement.

`backtest_report.md` includes:

* Backtest date range.
* Rebalance count.
* Initial cash and ending equity.
* Total return, annualized return, max drawdown, Sharpe ratio, turnover, number of trades, and win rate.
* Data quality warning and blocking issue counts.
* Trading restriction summary.
* Final holdings.
* Safety statement.

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
10. Writes CSV outputs and Markdown report.

Backtest outputs:

```text
data/output/backtest_equity_curve.csv
data/output/backtest_trades.csv
data/output/backtest_holdings.csv
data/output/backtest_metrics.csv
data/output/backtest_audit_log.csv
data/output/backtest_report.md
```

## Current Limitations

* Only local sample CSV data is supported.
* Config parsing supports the simple YAML shape used by `config/default.yaml`.
* Reports are Markdown only.
* The backtest uses simple quarterly sample data, not a full daily A-share database.
* Rebalance-day valuation uses MVP proxy market assumptions for fields not present in the historical close-price file.
* No Feishu notification is implemented yet.
* No real broker integration exists.
* No live trading mode exists.

## Next Phase

Recommended Phase 5 work:

1. Add richer point-in-time valuation data.
2. Add HTML report export and charts.
3. Add Feishu report delivery for paper and backtest summaries.
4. Add deeper audit logs for every score, portfolio, risk, and simulated trade decision.
5. Define broker adapter interfaces while keeping all live adapters disabled by default.

## Disclaimer

This project is for personal research and system development only.

It does not provide investment advice, does not guarantee returns, and does not support real-money trading.
