# Dorsey A-Share Autotrader

A-share low-frequency rules-based automated trading system based on Pat Dorsey's fundamental investing framework.

This project converts Pat Dorsey's investing theory into fixed quantitative rules for A-share stock screening, scoring, portfolio construction, paper trading, and future automated execution.

## Project Status

Current phase: **MVP / Research and Paper Trading**

This project does **not** perform real-money trading yet.

The first version focuses on:

* Local sample data
* Fundamental factor calculation
* Financial red-flag filtering
* Moat proxy scoring
* Valuation scoring
* Composite stock ranking
* Target portfolio construction
* Paper trading
* Unit tests

Live trading adapters for QMT or PTrade will be added only after the research, backtest, and paper trading layers are stable.

## Core Theory

The system is based on Pat Dorsey's five rules:

1. Do your homework.
2. Find economic moats.
3. Require a margin of safety.
4. Hold for the long term.
5. Know when to sell.

The moat framework follows four moat sources:

1. Intangible assets
2. Switching costs
3. Network effects
4. Cost advantages

## Product Definition

This is not a short-term trading system.

This is not a technical-analysis strategy.

This is not a high-frequency trading system.

This is a low-frequency fundamental quant system designed for A-share stocks.

The system aims to answer:

* Which companies pass basic financial red-flag checks?
* Which companies show signs of durable competitive advantage?
* Which companies have strong quality factors?
* Which companies are reasonably valued?
* Which companies should enter the target portfolio?
* Which positions should be removed because the original investment logic is broken?

## Initial Strategy Logic

The first version uses the following composite score:

```text
composite_score =
quality_score * 0.35
+ moat_score * 0.30
+ valuation_score * 0.25
+ risk_score * 0.10
```

If a stock is blocked by red flags, its composite score must be zero.

## First Version Portfolio Rules

* Select top 20 stocks by composite score.
* Equal weight.
* Max single stock weight: 5%.
* Max single industry weight: 25%.
* Keep 5% cash reserve.
* Exclude blocked stocks.
* Default trading mode: paper trading only.

## Planned Project Structure

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

## Planned CLI Commands

```bash
python -m dorsey_as run-score
python -m dorsey_as build-portfolio
python -m dorsey_as paper-rebalance
```

## Safety Rules

* No real broker connection in the MVP phase.
* No real-money trading in the MVP phase.
* No hardcoded secrets.
* Default mode must always be paper trading.
* If data is missing, invalid, stale, or inconsistent, the system must not trade.
* If risk checks fail, the system must not trade.
* If target portfolio is empty, the system must not trade.
* Live broker adapters must be disabled by default.

## Future Roadmap

### Phase 1: MVP

* Project skeleton
* Data schemas
* Sample CSV data
* Red-flag engine
* Quality factor engine
* Moat proxy engine
* Valuation engine
* Composite score engine
* Portfolio builder
* Paper broker
* CLI commands
* Unit tests

### Phase 2: Backtesting

* Quarterly rebalancing
* Transaction costs
* Stamp duty
* Slippage
* Suspended stock handling
* Limit-up and limit-down handling
* Equity curve
* Max drawdown
* Sharpe ratio
* Turnover
* Trade log

### Phase 3: Monitoring

* Feishu notification
* Daily report
* Risk alerts
* Paper trading report
* System health check

### Phase 4: Live Trading Preparation

* Broker adapter interface
* QMT placeholder
* PTrade placeholder
* Live trading disabled by default
* Manual confirmation mode
* Kill switch

### Phase 5: Small-Capital Live Testing

* QMT or PTrade integration
* Small-capital test
* Full trade logging
* Risk control
* Manual override

## Disclaimer

This project is for personal research and system development only.

It does not provide investment advice.

It does not guarantee investment returns.

Live trading should only be enabled after sufficient backtesting, paper trading, and risk validation.
