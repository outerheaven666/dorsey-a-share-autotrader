from __future__ import annotations

from dorsey_as.models import FactorResult, FinancialSnapshot, StockBasic
from dorsey_as.utils.math import average, clamp, safe_div, score_ratio


def calculate_quality(stock: StockBasic, financials: list[FinancialSnapshot]) -> FactorResult:
    rows = sorted(financials, key=lambda item: item.year, reverse=True)[:5]
    if not rows:
        return FactorResult(stock.symbol, {}, 0.0)

    current = rows[0]
    avg_roe = average([row.roe for row in rows])
    avg_roic = average([row.roic for row in rows])
    ocf_to_net_profit = average([safe_div(row.operating_cash_flow, row.net_profit, 0.0) for row in rows if row.net_profit != 0])
    fcf_to_revenue = average([safe_div(row.free_cash_flow, row.revenue, 0.0) for row in rows if row.revenue != 0])
    debt_to_asset = safe_div(current.total_liabilities, current.total_assets, 1.0)
    debt_safety = clamp((1.0 - debt_to_asset) / 0.75 * 100.0)

    components = {
        "avg_roe_5y": score_ratio(avg_roe, 0.20),
        "avg_roic_5y": score_ratio(avg_roic, 0.15),
        "gross_margin": score_ratio(current.gross_margin, 0.50),
        "net_margin": score_ratio(current.net_margin, 0.20),
        "ocf_to_net_profit": score_ratio(ocf_to_net_profit, 1.0),
        "fcf_to_revenue": score_ratio(fcf_to_revenue, 0.15),
        "debt_safety": debt_safety,
    }
    return FactorResult(stock.symbol, components, average(list(components.values())))
