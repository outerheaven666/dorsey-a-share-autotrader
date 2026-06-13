import csv

from dorsey_as.broker.paper import PaperBroker
from dorsey_as.models import FinancialSnapshot, MarketSnapshot, PortfolioPosition, ScoreResult, StockBasic, TargetPortfolio
from dorsey_as.portfolio.constructor import build_target_portfolio
from dorsey_as.scoring import calculate_score


def financial_rows(symbol: str, net_profit: float = 20.0) -> list[FinancialSnapshot]:
    return [
        FinancialSnapshot(
            symbol=symbol,
            year=year,
            revenue=100.0,
            net_profit=net_profit,
            operating_cash_flow=24.0,
            free_cash_flow=18.0,
            total_assets=180.0,
            total_liabilities=50.0,
            equity=130.0,
            accounts_receivable=5.0,
            inventory=8.0,
            goodwill=5.0,
            non_recurring_profit=1.0,
            roe=0.18,
            roic=0.16,
            gross_margin=0.45,
            net_margin=0.2,
            rd_expense=4.0,
            selling_expense=7.0,
        )
        for year in range(2020, 2025)
    ]


def market(symbol: str) -> MarketSnapshot:
    return MarketSnapshot(
        symbol=symbol,
        trade_date="2026-06-14",
        close_price=10.0,
        market_cap=1000.0,
        pe=18.0,
        pb=2.0,
        ev_to_fcf=14.0,
        fcf_yield=0.07,
        dividend_yield=0.025,
    )


def test_composite_score_is_zero_when_red_flags_block_stock() -> None:
    stock = StockBasic("000001.SZ", "Blocked Co", "Manufacturing")
    rows = financial_rows("000001.SZ")
    rows[-1].net_profit = -10.0
    rows[-2].net_profit = -8.0

    result = calculate_score(stock, rows, market("000001.SZ"))

    assert result.blocked is True
    assert result.composite_score == 0


def test_portfolio_respects_stock_cash_and_industry_constraints() -> None:
    stocks = {
        f"0000{i:02d}.SZ": StockBasic(f"0000{i:02d}.SZ", f"Stock {i}", "Tech" if i <= 8 else "Consumer")
        for i in range(1, 31)
    }
    scores = [
        ScoreResult(
            symbol=symbol,
            quality_score=80,
            moat_score=75,
            valuation_score=70,
            risk_score=100,
            composite_score=100 - i,
            blocked=False,
            reasons=[],
            warnings=[],
        )
        for i, symbol in enumerate(stocks, start=1)
    ]

    portfolio = build_target_portfolio(scores, stocks)

    assert portfolio.cash_weight == 0.05
    assert len(portfolio.positions) <= 20
    assert all(position.target_weight <= 0.05 for position in portfolio.positions)
    tech_weight = sum(p.target_weight for p in portfolio.positions if p.industry == "Tech")
    assert tech_weight <= 0.25
    assert round(sum(p.target_weight for p in portfolio.positions) + portfolio.cash_weight, 6) <= 1.0


def test_paper_broker_rebalances_and_writes_trade_log(tmp_path) -> None:
    log_path = tmp_path / "paper_trades.csv"
    broker = PaperBroker(cash=100_000.0, positions={}, trade_log_path=log_path)
    target = TargetPortfolio(
        positions=[
            PortfolioPosition("000001.SZ", "One", "Tech", 0.05, 90.0),
            PortfolioPosition("000002.SZ", "Two", "Consumer", 0.05, 88.0),
        ],
        cash_weight=0.90,
    )

    orders = broker.rebalance(target, {"000001.SZ": 10.0, "000002.SZ": 20.0})

    assert [order.side for order in orders] == ["BUY", "BUY"]
    assert broker.positions["000001.SZ"] > 0
    assert broker.cash < 100_000.0
    with log_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 2
    assert rows[0]["mode"] == "paper"
