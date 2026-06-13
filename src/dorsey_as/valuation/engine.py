from __future__ import annotations

from dorsey_as.models import FactorResult, MarketSnapshot
from dorsey_as.utils.math import average, clamp, safe_div, score_ratio


def _lower_is_better(value: float, expensive: float) -> float:
    if value <= 0:
        return 0.0
    return clamp(100.0 - value / expensive * 100.0)


def calculate_valuation(market: MarketSnapshot, roe: float = 0.0) -> FactorResult:
    pb_roe_value = safe_div(roe, market.pb, 0.0)
    components = {
        "pe_percentile": _lower_is_better(market.pe, 50.0),
        "pb_roe": score_ratio(pb_roe_value, 0.08),
        "ev_fcf": _lower_is_better(market.ev_to_fcf, 35.0),
        "fcf_yield": score_ratio(market.fcf_yield, 0.08),
        "dividend_yield": score_ratio(market.dividend_yield, 0.04),
    }
    return FactorResult(market.symbol, components, average(list(components.values())))
