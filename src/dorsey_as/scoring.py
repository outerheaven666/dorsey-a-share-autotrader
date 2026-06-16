from __future__ import annotations

from dorsey_as.config.models import ScoringConfig
from dorsey_as.factors.quality import calculate_quality
from dorsey_as.moat.engine import calculate_moat
from dorsey_as.models import FinancialSnapshot, MarketSnapshot, ScoreResult, StockBasic
from dorsey_as.risk.engine import evaluate_red_flags
from dorsey_as.utils.math import average
from dorsey_as.valuation.engine import calculate_valuation


def calculate_score(
    stock: StockBasic,
    financials: list[FinancialSnapshot],
    market: MarketSnapshot,
    scoring_config: ScoringConfig | None = None,
) -> ScoreResult:
    config = scoring_config or ScoringConfig()
    risk = evaluate_red_flags(stock, financials)
    quality = calculate_quality(stock, financials)
    moat = calculate_moat(stock, financials)
    roe = average([row.roe for row in financials[-5:]])
    valuation = calculate_valuation(market, roe=roe)
    composite = (
        quality.score * config.quality_weight
        + moat.score * config.moat_weight
        + valuation.score * config.valuation_weight
        + risk.risk_score * config.risk_weight
    )
    if risk.blocked:
        composite = 0.0
    return ScoreResult(
        symbol=stock.symbol,
        quality_score=round(quality.score, 4),
        moat_score=round(moat.score, 4),
        valuation_score=round(valuation.score, 4),
        risk_score=round(risk.risk_score, 4),
        composite_score=round(composite, 4),
        blocked=risk.blocked,
        reasons=risk.reasons,
        warnings=risk.warnings,
    )


def calculate_scores(
    stocks: dict[str, StockBasic],
    financials: dict[str, list[FinancialSnapshot]],
    markets: dict[str, MarketSnapshot],
    scoring_config: ScoringConfig | None = None,
) -> list[ScoreResult]:
    results: list[ScoreResult] = []
    for symbol, stock in stocks.items():
        if symbol not in financials or symbol not in markets:
            continue
        results.append(calculate_score(stock, financials[symbol], markets[symbol], scoring_config=scoring_config))
    return sorted(results, key=lambda item: item.composite_score, reverse=True)
