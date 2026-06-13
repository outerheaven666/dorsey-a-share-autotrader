# Dorsey A-Share Autotrader

A-share low-frequency rules-based automated trading system based on Pat Dorsey's fundamental investing framework.

Current phase: **MVP 1 / Research and Paper Trading**.

This project does **not** perform real-money trading. The MVP only reads local sample CSV files, builds scores and a target portfolio, and runs a local paper broker simulation.

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

Required columns:

```text
symbol,name,industry,is_st,is_suspended
```

### `financial_snapshot.csv`

Required columns:

```text
symbol,year,revenue,net_profit,operating_cash_flow,free_cash_flow,total_assets,total_liabilities,equity,accounts_receivable,inventory,goodwill,non_recurring_profit,roe,roic,gross_margin,net_margin,rd_expense,selling_expense
```

### `market_snapshot.csv`

Required columns:

```text
symbol,trade_date,close_price,market_cap,pe,pb,ev_to_fcf,fcf_yield,dividend_yield
```

## CLI Usage

Generate stock scores:

```bash
python -m dorsey_as run-score
```

Output:

```text
data/output/scores.csv
```

Build a target portfolio:

```bash
python -m dorsey_as build-portfolio
```

Output:

```text
data/output/scores.csv
data/output/target_portfolio.csv
```

Run one paper rebalance:

```bash
python -m dorsey_as paper-rebalance
```

Output:

```text
data/output/scores.csv
data/output/target_portfolio.csv
data/output/paper_state.csv
data/output/paper_trades.csv
```

Optional arguments:

```bash
python -m dorsey_as --data-dir data/sample --output-dir data/output run-score
python -m dorsey_as --data-dir data/sample --output-dir data/output build-portfolio
python -m dorsey_as --data-dir data/sample --output-dir data/output paper-rebalance --cash 1000000
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

## Safety Limits

The MVP cannot place real orders.

It contains no QMT adapter, no PTrade adapter, no real broker credentials, and no live trading mode. The only broker implementation is `PaperBroker`, which writes simulated orders to local CSV files.

The system refuses to paper trade when:

* The target portfolio is empty.
* A required market price is missing or invalid.
* The paper account has insufficient simulated cash for generated buys.

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
* No backtesting engine is implemented yet.
* No Feishu notification is implemented yet.
* No real broker integration exists.
* No live trading mode exists.

## Next Phase

Recommended Phase 2 work:

1. Add quarterly backtesting with transaction costs, stamp duty, slippage, suspended-stock handling, and limit-up/limit-down handling.
2. Add equity curve, max drawdown, Sharpe ratio, turnover, and trade-log analytics.
3. Add stricter data validation and stale-data checks before any paper rebalance.
4. Add Feishu paper trading reports and risk alerts.
5. Define broker adapter interfaces while keeping all live adapters disabled by default.

## Disclaimer

This project is for personal research and system development only.

It does not provide investment advice, does not guarantee returns, and does not support real-money trading in the MVP phase.
