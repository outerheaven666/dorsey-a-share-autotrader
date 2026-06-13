from dorsey_as.factors.quality import calculate_quality
from dorsey_as.models import FinancialSnapshot, MarketSnapshot, StockBasic
from dorsey_as.moat.engine import calculate_moat
from dorsey_as.valuation.engine import calculate_valuation


def financials() -> list[FinancialSnapshot]:
    return [
        FinancialSnapshot(
            symbol="600519.SH",
            year=year,
            revenue=100.0 + year - 2020,
            net_profit=24.0,
            operating_cash_flow=28.0,
            free_cash_flow=22.0,
            total_assets=200.0,
            total_liabilities=40.0,
            equity=160.0,
            accounts_receivable=4.0,
            inventory=8.0,
            goodwill=0.0,
            non_recurring_profit=1.0,
            roe=0.25,
            roic=0.22,
            gross_margin=0.62,
            net_margin=0.24,
            rd_expense=6.0,
            selling_expense=9.0,
        )
        for year in range(2020, 2025)
    ]


def test_quality_score_uses_profitability_cash_flow_and_debt_safety() -> None:
    result = calculate_quality(StockBasic("600519.SH", "Quality Co", "Consumer"), financials())

    assert result.symbol == "600519.SH"
    assert set(result.components) >= {
        "avg_roe_5y",
        "avg_roic_5y",
        "gross_margin",
        "net_margin",
        "ocf_to_net_profit",
        "fcf_to_revenue",
        "debt_safety",
    }
    assert 0 <= result.score <= 100
    assert result.score > 70


def test_moat_score_returns_four_dorsey_categories() -> None:
    result = calculate_moat(StockBasic("600519.SH", "Moat Co", "Consumer"), financials())

    assert set(result.components) == {
        "intangible_assets",
        "switching_costs",
        "network_effects",
        "cost_advantages",
    }
    assert all(0 <= value <= 100 for value in result.components.values())
    assert 0 <= result.score <= 100


def test_valuation_score_rewards_lower_multiples_and_cash_yield() -> None:
    result = calculate_valuation(
        MarketSnapshot(
            symbol="600519.SH",
            trade_date="2026-06-14",
            close_price=100.0,
            market_cap=1000.0,
            pe=15.0,
            pb=2.0,
            ev_to_fcf=12.0,
            fcf_yield=0.08,
            dividend_yield=0.03,
        ),
        roe=0.2,
    )

    assert set(result.components) == {
        "pe_percentile",
        "pb_roe",
        "ev_fcf",
        "fcf_yield",
        "dividend_yield",
    }
    assert 0 <= result.score <= 100
    assert result.score > 60
