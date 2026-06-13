from dorsey_as.models import FinancialSnapshot, StockBasic
from dorsey_as.risk.engine import evaluate_red_flags


def snapshot(year: int, net_profit: float, operating_cash_flow: float) -> FinancialSnapshot:
    return FinancialSnapshot(
        symbol="000001.SZ",
        year=year,
        revenue=100.0,
        net_profit=net_profit,
        operating_cash_flow=operating_cash_flow,
        free_cash_flow=8.0,
        total_assets=200.0,
        total_liabilities=80.0,
        equity=120.0,
        accounts_receivable=10.0,
        inventory=12.0,
        goodwill=10.0,
        non_recurring_profit=1.0,
        roe=0.12,
        roic=0.1,
        gross_margin=0.35,
        net_margin=0.12,
        rd_expense=5.0,
        selling_expense=8.0,
    )


def test_blocks_when_two_of_last_three_years_have_negative_profit() -> None:
    stock = StockBasic("000001.SZ", "Bad Profit", "Manufacturing")
    result = evaluate_red_flags(
        stock,
        [
            snapshot(2022, 10.0, 8.0),
            snapshot(2023, -1.0, 7.0),
            snapshot(2024, -2.0, 6.0),
        ],
    )

    assert result.blocked is True
    assert "negative_net_profit_2_of_3" in result.reasons
    assert result.risk_score == 0


def test_warns_on_cash_conversion_and_working_capital_growth() -> None:
    stock = StockBasic("000002.SZ", "Warning Co", "Consumer")
    rows = [
        snapshot(2022, 10.0, 7.0),
        snapshot(2023, 10.0, 5.0),
        snapshot(2024, 10.0, 4.0),
    ]
    rows[0].revenue = 100
    rows[1].revenue = 110
    rows[2].revenue = 120
    rows[0].accounts_receivable = 10
    rows[2].accounts_receivable = 18
    rows[0].inventory = 10
    rows[2].inventory = 18

    result = evaluate_red_flags(stock, rows)

    assert result.blocked is False
    assert "low_cash_conversion" in result.warnings
    assert "receivables_growth_too_fast" in result.warnings
    assert "inventory_growth_too_fast" in result.warnings
    assert 0 < result.risk_score < 100


def test_blocks_st_suspended_high_debt_and_excessive_goodwill() -> None:
    stock = StockBasic("000003.SZ", "ST Danger", "Finance", is_st=True, is_suspended=True)
    rows = [snapshot(2024, 10.0, 8.0)]
    rows[0].total_liabilities = 180.0
    rows[0].total_assets = 200.0
    rows[0].goodwill = 70.0
    rows[0].equity = 100.0

    result = evaluate_red_flags(stock, rows)

    assert result.blocked is True
    assert "st_stock" in result.reasons
    assert "suspended_stock" in result.reasons
    assert "debt_to_asset_too_high" in result.reasons
    assert "goodwill_to_equity_too_high" in result.reasons
