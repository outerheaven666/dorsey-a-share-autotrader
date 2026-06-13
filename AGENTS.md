# AGENTS.md

## Project Name

Dorsey A-Share Autotrader

## Project Goal

This project is an A-share low-frequency rules-based automated trading system based on Pat Dorsey's fundamental investing framework.

The system converts Dorsey's theory into fixed quantitative rules:

1. Do your homework.
2. Find economic moats.
3. Require a margin of safety.
4. Hold for the long term.
5. Know when to sell.

The moat framework follows four moat sources from Pat Dorsey's later framework:

1. Intangible assets.
2. Switching costs.
3. Network effects.
4. Cost advantages.

## Product Definition

This is not a short-term trading or technical analysis system.

This is a low-frequency fundamental quant system for A-share stocks.

The system should eventually support:

* A-share universe construction.
* Fundamental data ingestion.
* Financial red-flag filtering.
* Moat proxy factor calculation.
* Quality factor calculation.
* Valuation and margin-of-safety scoring.
* Portfolio construction.
* Quarterly rebalancing.
* Backtesting.
* Paper trading.
* Feishu notifications.
* Future broker adapter support for QMT or PTrade.

## Safety Rules

Do not implement real-money trading in early phases.

The first phase must use only:

* Local CSV sample data.
* Mock data.
* Paper trading.
* No real broker credentials.
* No real order placement.

Any broker adapter must be behind an explicit interface and disabled by default.

The default trading mode must always be paper trading.

If live trading mode is requested but no valid broker configuration exists, the system must refuse to start.

If data is missing, invalid, stale, or inconsistent, the system must not trade.

If risk checks fail, the system must not trade.

If target portfolio is empty, the system must not trade.

If account state and internal portfolio state do not match, the system must not trade.

## Engineering Principles

* Use Python 3.11 or higher.
* Use clear modular architecture.
* Use type hints.
* Use unit tests.
* Do not hardcode secrets.
* Use environment variables for credentials.
* Log every signal, order, portfolio decision, and risk decision.
* Keep the code testable.
* Keep business rules explicit and easy to audit.
* Avoid hidden magic.
* Prefer simple deterministic rules over complex black-box logic.
* Do not overfit strategy parameters.
* Do not connect to real broker APIs unless explicitly requested in a later milestone.

## Suggested Project Structure

Use this structure:

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

## Core Modules

### data

Responsible for:

* Loading stock basic data.
* Loading financial snapshots.
* Loading market snapshots.
* Loading sample CSV data.
* Later supporting real A-share data sources.

### risk

Responsible for hard red-flag rules.

Examples:

* Negative net profit in at least 2 of the last 3 years.
* Negative operating cash flow in at least 2 of the last 3 years.
* Operating cash flow / net profit too low.
* Accounts receivable growth much faster than revenue growth.
* Inventory growth much faster than revenue growth.
* Goodwill too high relative to equity.
* Non-recurring profit too high relative to net profit.
* Debt-to-asset ratio too high.
* ST stock.
* Suspended stock.

### factors

Responsible for quality factors:

* ROE.
* ROIC.
* Gross margin.
* Net margin.
* Operating cash flow / net profit.
* Free cash flow / revenue.
* Debt safety score.

### moat

Responsible for moat proxy factors.

The four moat categories are:

1. Intangible assets.
2. Switching costs.
3. Network effects.
4. Cost advantages.

Each category should produce a score from 0 to 100.

The system should also calculate an overall moat score.

### valuation

Responsible for valuation and margin-of-safety factors:

* PE percentile score.
* PB/ROE score.
* EV/FCF score.
* FCF yield score.
* Dividend yield score.

The system should calculate a valuation score from 0 to 100.

### portfolio

Responsible for portfolio construction.

Initial rules:

* Select top 20 stocks by composite score.
* Equal weight.
* Max single stock weight: 5%.
* Max single industry weight: 25%.
* Keep 5% cash reserve.
* Exclude blocked stocks.

### broker

Responsible for trading interface.

Initial implementation:

* Paper broker only.

Future implementations:

* QMT broker adapter.
* PTrade broker adapter.

Live broker adapters must be disabled by default.

### notify

Responsible for Feishu notifications.

Initial implementation can be a placeholder.

Future implementation should send:

* Daily report.
* Portfolio report.
* Risk alert.
* Order report.
* Error alert.

## Composite Score

Initial formula:

composite_score =
quality_score * 0.35

* moat_score * 0.30
* valuation_score * 0.25
* risk_score * 0.10

If a stock is blocked by red flags, composite_score must be 0.

## First Milestone

The first milestone is not live trading.

The first milestone is:

1. Create the project skeleton.
2. Define data schemas.
3. Implement sample CSV data loading.
4. Implement red-flag rules.
5. Implement quality factors.
6. Implement moat proxy factors.
7. Implement valuation factors.
8. Generate a ranked stock list from sample CSV data.
9. Generate a target portfolio.
10. Implement a paper broker.
11. Add CLI commands.
12. Add unit tests.
13. Update README with usage instructions.

## CLI Commands

The first version should support:

python -m dorsey_as run-score

python -m dorsey_as build-portfolio

python -m dorsey_as paper-rebalance

## Testing

Use pytest.

Tests should cover:

* Red flag engine.
* Quality factor calculation.
* Moat proxy calculation.
* Valuation score.
* Composite score.
* Portfolio constraints.
* Paper broker.

## Current Scope

The current scope is research, scoring, portfolio construction, and paper trading.

Do not implement real broker trading yet.
