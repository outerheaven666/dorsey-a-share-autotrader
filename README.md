# Dorsey A-Share Autotrader

A-share low-frequency rules-based automated trading system based on Pat Dorsey's fundamental investing framework.

Current phase: **MVP 2 / Research, Portfolio Construction, Paper Trading, and Local Backtesting**.

This project does **not** perform real-money trading. The current version only reads local sample CSV files, builds scores and a target portfolio, runs paper broker simulation, and runs a local quarterly backtest.

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
```

Run tests:

```bash
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
symbol,year,revenue,net_profit,operating_cash_flow,free_cash_flow,total_assets,total_liabilities,equity,accounts_receivable,inventory,goodwill,non_recurring_profit,roe,roic,gross_margin,net_margin,rd_expense,selling_expense
```

### `market_snapshot.csv`

```text
symbol,trade_date,close_price,market_cap,pe,pb,ev_to_fcf,fcf_yield,dividend_yield
```

### `historical_market_snapshot.csv`

Used by the quarterly backtest.

```text
symbol,trade_date,close_price,is_suspended,is_limit_up,is_limit_down
```

### `trading_calendar.csv`

Used to mark quarterly rebalance dates.

```text
trade_date,is_rebalance_date
```

## CLI Usage

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
python -m dorsey_as --data-dir data/sample --output-dir data/output run-score
python -m dorsey_as --data-dir data/sample --output-dir data/output build-portfolio
python -m dorsey_as --data-dir data/sample --output-dir data/output paper-rebalance --cash 1000000
python -m dorsey_as --data-dir data/sample --output-dir data/output run-backtest --cash 1000000
```

## Scoring Logic

Red flags can block a stock. If a stock is blocked, `composite_score` is always `0`.

```text
composite_score =
quality_score * 0.35
+ moat_score * 0.30
+ valuation_score * 0.25
+ risk_score * 0.10
```

Implemented red-flag rules:

* Block if at least two of the last three years have negative net profit.
* Block if at least two of the last three years have negative operating cash flow.
* Warn if average operating cash flow / net profit is below 0.6.
* Warn if accounts receivable growth exceeds revenue growth by more than 20 percentage points.
* Warn if inventory growth exceeds revenue growth by more than 20 percentage points.
* Warn if goodwill / equity exceeds 30%.
* Block if goodwill / equity exceeds 50%.
* Warn if non-recurring profit / net profit exceeds 30%.
* Block if non-recurring profit / net profit exceeds 50%.
* Block if debt-to-asset ratio exceeds 75%.
* Block ST stocks.
* Block suspended stocks.

Portfolio construction rules:

* Select top stocks by composite score, up to 20 positions.
* Exclude blocked stocks.
* Keep 5% cash reserve.
* Max single stock weight is 5%.
* Max single industry weight is 25%.

## Backtesting

The MVP 2 backtest is designed to validate the research and portfolio rules before any real trading work exists. It runs over local historical sample CSV data only.

At each rebalance date, the engine:

1. Loads sample fundamentals and historical market snapshots.
2. Runs the scoring engine.
3. Builds the target portfolio.
4. Compares current simulated holdings with target weights.
5. Generates simulated trades.
6. Applies A-share trading restrictions.
7. Deducts transaction costs.
8. Updates cash and holdings.
9. Marks positions to market.
10. Writes the equity curve, trades, holdings, and metrics.

Backtest outputs are written to `data/output/`, which is ignored by git:

```text
data/output/backtest_equity_curve.csv
data/output/backtest_trades.csv
data/output/backtest_holdings.csv
data/output/backtest_metrics.csv
```

### Transaction Cost Assumptions

Defaults:

* Commission rate: `0.0003`.
* Minimum commission: `5`.
* Stamp duty on sell orders: `0.0005`.
* Slippage rate: `0.001`.

### A-Share Trading Restrictions

The backtest applies these local simulation rules:

* Suspended stocks cannot be bought or sold.
* Limit-up stocks cannot be bought.
* Limit-down stocks cannot be sold.
* Unfilled trades are skipped and recorded with a reason.
* Short selling is not allowed.
* Cash cannot go below zero.
* Position quantities cannot go below zero.

### Backtest Metrics

Implemented metrics:

* Total return.
* Annualized return.
* Max drawdown.
* Sharpe ratio.
* Turnover.
* Number of trades.
* Win rate when sell trades exist.

## Safety Limits

The MVP cannot place real orders.

It contains no QMT adapter, no PTrade adapter, no real broker credentials, and no live trading mode. The only broker implementation is `PaperBroker`, which writes simulated orders to local CSV files. The backtest engine is also local simulation only.

The system refuses or skips simulated trading when:

* The target portfolio is empty.
* A required market price is missing or invalid.
* The paper account has insufficient simulated cash for generated buys.
* A simulated trade violates suspension, limit-up, limit-down, no-short, or no-negative-cash constraints.

## Project Structure

```text
src/
  dorsey_as/
    data/
    factors/
    moat/
    valuation/
    risk/
    portfolio/
    backtest/
    broker/
    notify/
    config/
    utils/

tests/

data/
  sample/
```

## Current Limitations

* Only local sample CSV data is supported.
* Factor formulas are deterministic MVP proxy rules, not optimized production models.
* The backtest uses simple quarterly sample data, not a full daily A-share dataset.
* Rebalance-day valuation uses MVP proxy market assumptions for fields not present in the historical close-price file.
* Win rate is only an MVP approximation.
* No Feishu notification is implemented yet.
* No real broker integration exists.
* No live trading mode exists.

## Next Phase

Recommended Phase 3 work:

1. Add stricter data validation and stale-data checks before paper rebalance and backtest.
2. Add richer historical valuation inputs so each rebalance date can use point-in-time valuation data.
3. Add Feishu paper trading reports, backtest summaries, and risk alerts.
4. Add daily report generation and system health checks.
5. Define broker adapter interfaces while keeping all live adapters disabled by default.

## Disclaimer

This project is for personal research and system development only.

It does not provide investment advice, does not guarantee returns, and does not support real-money trading in the MVP phase.
