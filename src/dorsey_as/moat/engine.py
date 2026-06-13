from __future__ import annotations

from dorsey_as.models import FactorResult, FinancialSnapshot, StockBasic
from dorsey_as.utils.math import average, safe_div, score_ratio


def _latest(rows: list[FinancialSnapshot]) -> FinancialSnapshot | None:
    if not rows:
        return None
    return sorted(rows, key=lambda item: item.year, reverse=True)[0]


def calculate_moat(stock: StockBasic, financials: list[FinancialSnapshot]) -> FactorResult:
    current = _latest(financials)
    if current is None:
        return FactorResult(stock.symbol, {}, 0.0)

    rows = sorted(financials, key=lambda item: item.year, reverse=True)[:5]
    avg_roic = average([row.roic for row in rows])
    avg_gross_margin = average([row.gross_margin for row in rows])
    avg_net_margin = average([row.net_margin for row in rows])
    avg_ocf_conversion = average([safe_div(row.operating_cash_flow, row.net_profit, 0.0) for row in rows if row.net_profit != 0])
    rd_ratio = safe_div(current.rd_expense, current.revenue, 0.0)
    selling_ratio = safe_div(current.selling_expense, current.revenue, 0.0)
    debt_to_asset = safe_div(current.total_liabilities, current.total_assets, 1.0)

    components = {
        "intangible_assets": average(
            [score_ratio(avg_gross_margin, 0.50), score_ratio(rd_ratio, 0.08), score_ratio(selling_ratio, 0.12)]
        ),
        "switching_costs": average([score_ratio(avg_ocf_conversion, 1.0), score_ratio(avg_net_margin, 0.20)]),
        "network_effects": average([score_ratio(avg_net_margin, 0.25), score_ratio(avg_roic, 0.18)]),
        "cost_advantages": average([score_ratio(avg_gross_margin, 0.45), score_ratio(avg_roic, 0.15), score_ratio(1 - debt_to_asset, 0.75)]),
    }
    return FactorResult(stock.symbol, components, average(list(components.values())))
