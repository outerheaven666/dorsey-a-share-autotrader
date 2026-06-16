# Dorsey A-Share Autotrader

A-share low-frequency rules-based automated trading system based on Pat Dorsey's fundamental investing framework.

Current phase: **MVP 3 / Data Quality, Look-Ahead Protection, Paper Trading, and Local Backtesting**.

This project does **not** perform real-money trading. The current version only reads local sample CSV files, checks data quality, builds scores and a target portfolio, runs paper broker simulation, and runs a local quarterly backtest.

## Scope

The strategy converts Pat Dorsey's framework into deterministic, auditable rules:

1. Do your homework.
2. Find economic moats.
3. Require a margin of safety.
4. Hold for the long term.
5. Know when to sell.

The moat framework uses four proxy categories:

1. Intangible assets.
2. Switching costs.
3. Network effects.
4. Cost advantages.

This is a low-frequency fundamental quant system. It is not a short-term trading system, a technical-analysis strategy, or a high-frequency trading system.

## Installation

Use Python 3.11 or higher.

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

## Sample Data

The MVP reads local CSV files from `data/sample/`.

### `stock_basic.csv`

```text
symbol,name,industry,is_st,is_suspended
```

### `financial_snapshot.csv`

```text
symbol,year,revenue,net_profit,operating_cash_flow,free_cash_flow,total_assets,total_liabilities,equity,accounts_receivable,inventory,goodwill,non_recurring_profit,roe,roic,gross_margin,net_margin,rd_expense,selling_expense,report_date,disclosure_date
```

`report_date` is the accounting period end date. `disclosure_date` is the date when the financial data became available to the system.

### `market_snapshot.csv`

```text
symbol,trade_date,close_price,market_cap,pe,pb,ev_to_fcf,fcf_yield,dividend_yield
```

### `historical_market_snapshot.csv`

Used by the quarterly backtest.

```text
symbol,trade_date,close_price,is_suspended,is_limit_up,is_limit_down,volume,amount
```

### `trading_calendar.csv`

Used to mark quarterly rebalance dates.

```text
trade_date,is_rebalance_date
```

### `data_quality_cases.csv`

Documents sample data quality scenarios used by tests:

```text
case_name,symbol,as_of_date,expected_severity,expected_blocking,description
```

## CLI Usage

Check sample data quality:

```bash
python -m dorsey_as check-data-quality
```

Generate stock scores:

```bash
python -m dorsey_as run-score
```

Build a target portfolio:

```bash
python -m dorsey_as build-portfolio
```

Run one paper rebalance:

```bash
python -m dorsey_as paper-rebalance
```

Run the local quarterly backtest:

```bash
python -m dorsey_as run-backtest
```

Optional arguments:

```bash
python -m dorsey_as --data-dir data/sample --output-dir data/output check-data-quality
python -m dorsey_as --data-dir data/sample --output-dir data/output run-score
python -m dorsey_as --data-dir data/sample --output-dir data/output build-portfolio
python -m dorsey_as --data-dir data/sample --output-dir data/output paper-rebalance --cash 1000000
python -m dorsey_as --data-dir data/sample --output-dir data/output run-backtest --cash 1000000
```

## Data Quality Layer

MVP 3 adds a blocking data quality gate before scoring, portfolio construction, paper rebalance, and each backtest rebalance date.

The checks are:

* `DataAvailabilityCheck`: verifies required datasets are present.
* `LookAheadBiasCheck`: prevents use of financial data disclosed after `as_of_date`.
* `MissingValueCheck`: blocks missing core fields.
* `StaleDataCheck`: warns when the latest valid disclosure is older than the stale threshold.
* `OutlierCheck`: blocks invalid prices, market values, and severe financial anomalies.

If any blocking issue exists, the CLI stops before scoring or backtesting and writes:

```text
data/output/data_quality_report.csv
```

The backtest also writes:

```text
data/output/backtest_audit_log.csv
```

### Look-Ahead Protection

At any `as_of_date`, the system may only use financial rows where:

```text
disclosure_date <= as_of_date
```

If a financial row has an accounting `report_date` in the past but a `disclosure_date` later than `as_of_date`, it is treated as unavailable and recorded as a blocking look-ahead issue.

The scoring CLI uses the latest `market_snapshot.trade_date` as its default `as_of_date`. The backtest uses each rebalance date as the default `as_of_date`.

### Stale Data

Default stale threshold:

```text
450 days
```

Data older than this threshold produces a warning. Current MVP warnings do not block the flow unless they are also tied to a blocking availability, missing-value, look-ahead, or outlier issue.

### Outlier Rules

Blocking checks include:

* `close_price <= 0`
* `market_cap <= 0`
* `pb <= 0`
* `revenue < 0`
* `total_assets < 0`
* `total_liabilities < 0`
* gross margin outside the configured reasonable range
* extreme net margin

Negative PE is recorded as a warning because it can be explained by loss-making companies.

## Scoring Logic

Red flags can block a stock. If a stock is blocked, `composite_score` is always `0`.

```text
composite_score =
quality_score * 0.35
+ moat_score * 0.30
+ valuation_score * 0.25
+ risk_score * 0.10
```

Portfolio construction rules:

* Select top stocks by composite score, up to 20 positions.
* Exclude blocked stocks.
* Keep 5% cash reserve.
* Max single stock weight is 5%.
* Max single industry weight is 25%.

## Backtesting

The local backtest validates the research and portfolio rules before any real trading work exists.

At each rebalance date, the engine:

1. Runs data quality and look-ahead checks.
2. Loads eligible point-in-time financial rows using `disclosure_date <= as_of_date`.
3. Runs the scoring engine.
4. Builds the target portfolio.
5. Generates simulated trades.
6. Applies A-share trading restrictions.
7. Deducts transaction costs.
8. Updates cash and holdings.
9. Marks positions to market.
10. Writes equity curve, trades, holdings, metrics, data quality report, and audit log.

Backtest outputs:

```text
data/output/backtest_equity_curve.csv
data/output/backtest_trades.csv
data/output/backtest_holdings.csv
data/output/backtest_metrics.csv
data/output/backtest_audit_log.csv
```

## Transaction Cost Assumptions

Defaults:

* Commission rate: `0.0003`.
* Minimum commission: `5`.
* Stamp duty on sell orders: `0.0005`.
* Slippage rate: `0.001`.

## A-Share Trading Restrictions

The backtest applies these local simulation rules:

* Suspended stocks cannot be bought or sold.
* Limit-up stocks cannot be bought.
* Limit-down stocks cannot be sold.
* Unfilled trades are skipped and recorded with a reason.
* Short selling is not allowed.
* Cash cannot go below zero.
* Position quantities cannot go below zero.

## Safety Limits

The MVP cannot place real orders.

It contains no QMT adapter, no PTrade adapter, no real broker credentials, and no live trading mode. The only broker implementation is `PaperBroker`, which writes simulated orders to local CSV files. The backtest engine is also local simulation only.

## Current Limitations

* Only local sample CSV data is supported.
* Data quality rules are deterministic MVP guardrails, not a complete production data validation system.
* The backtest uses simple quarterly sample data, not a full daily A-share database.
* Rebalance-day valuation uses MVP proxy market assumptions for fields not present in the historical close-price file.
* Stale data currently warns but does not block by itself.
* No Feishu notification is implemented yet.
* No real broker integration exists.
* No live trading mode exists.

## Next Phase

Recommended Phase 4 work:

1. Add point-in-time valuation data to historical snapshots.
2. Add severity configuration for stale data and outlier checks.
3. Add Feishu data quality reports, backtest summaries, and risk alerts.
4. Add richer audit logs for every scoring, portfolio, risk, and simulated trade decision.
5. Define broker adapter interfaces while keeping all live adapters disabled by default.

## Disclaimer

This project is for personal research and system development only.

It does not provide investment advice, does not guarantee returns, and does not support real-money trading in the MVP phase.
