from __future__ import annotations

from dorsey_as.models import FinancialSnapshot, RedFlagResult, StockBasic
from dorsey_as.utils.math import average, safe_div


def _latest(rows: list[FinancialSnapshot], count: int | None = None) -> list[FinancialSnapshot]:
    ordered = sorted(rows, key=lambda item: item.year, reverse=True)
    return ordered if count is None else ordered[:count]


def _growth(first: float, last: float) -> float:
    return safe_div(last - first, abs(first), 0.0)


def evaluate_red_flags(stock: StockBasic, financials: list[FinancialSnapshot]) -> RedFlagResult:
    reasons: list[str] = []
    warnings: list[str] = []
    latest_three = _latest(financials, 3)

    if stock.is_st:
        reasons.append("st_stock")
    if stock.is_suspended:
        reasons.append("suspended_stock")

    if sum(1 for row in latest_three if row.net_profit < 0) >= 2:
        reasons.append("negative_net_profit_2_of_3")
    if sum(1 for row in latest_three if row.operating_cash_flow < 0) >= 2:
        reasons.append("negative_operating_cash_flow_2_of_3")

    cash_ratios = [safe_div(row.operating_cash_flow, row.net_profit, 0.0) for row in latest_three if row.net_profit != 0]
    if cash_ratios and average(cash_ratios) < 0.6:
        warnings.append("low_cash_conversion")

    chronological = sorted(latest_three, key=lambda item: item.year)
    if len(chronological) >= 2:
        first, last = chronological[0], chronological[-1]
        revenue_growth = _growth(first.revenue, last.revenue)
        if _growth(first.accounts_receivable, last.accounts_receivable) > revenue_growth + 0.20:
            warnings.append("receivables_growth_too_fast")
        if _growth(first.inventory, last.inventory) > revenue_growth + 0.20:
            warnings.append("inventory_growth_too_fast")

    if financials:
        current = _latest(financials, 1)[0]
        goodwill_to_equity = safe_div(current.goodwill, current.equity, 0.0)
        non_recurring_to_profit = safe_div(abs(current.non_recurring_profit), abs(current.net_profit), 0.0)
        debt_to_asset = safe_div(current.total_liabilities, current.total_assets, 0.0)

        if goodwill_to_equity > 0.50:
            reasons.append("goodwill_to_equity_too_high")
        elif goodwill_to_equity > 0.30:
            warnings.append("goodwill_to_equity_high")

        if non_recurring_to_profit > 0.50:
            reasons.append("non_recurring_profit_too_high")
        elif non_recurring_to_profit > 0.30:
            warnings.append("non_recurring_profit_high")

        if debt_to_asset > 0.75:
            reasons.append("debt_to_asset_too_high")

    blocked = bool(reasons)
    risk_score = 0.0 if blocked else max(40.0, 100.0 - len(warnings) * 10.0)
    return RedFlagResult(stock.symbol, blocked, reasons, warnings, risk_score)
