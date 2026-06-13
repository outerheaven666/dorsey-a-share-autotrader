from __future__ import annotations

from dorsey_as.models import PortfolioPosition, ScoreResult, StockBasic, TargetPortfolio


def build_target_portfolio(
    scores: list[ScoreResult],
    stocks: dict[str, StockBasic],
    max_positions: int = 20,
    max_stock_weight: float = 0.05,
    max_industry_weight: float = 0.25,
    cash_reserve: float = 0.05,
) -> TargetPortfolio:
    candidates = [
        score
        for score in sorted(scores, key=lambda item: item.composite_score, reverse=True)
        if not score.blocked and score.composite_score > 0 and score.symbol in stocks
    ]
    if not candidates:
        return TargetPortfolio([], cash_reserve)

    investable_weight = 1.0 - cash_reserve
    per_stock_weight = min(max_stock_weight, investable_weight / min(max_positions, len(candidates)))
    positions: list[PortfolioPosition] = []
    industry_weights: dict[str, float] = {}

    for score in candidates:
        if len(positions) >= max_positions:
            break
        stock = stocks[score.symbol]
        current_industry_weight = industry_weights.get(stock.industry, 0.0)
        if current_industry_weight + per_stock_weight > max_industry_weight + 1e-12:
            continue
        positions.append(
            PortfolioPosition(
                symbol=stock.symbol,
                name=stock.name,
                industry=stock.industry,
                target_weight=round(per_stock_weight, 6),
                score=score.composite_score,
            )
        )
        industry_weights[stock.industry] = current_industry_weight + per_stock_weight

    return TargetPortfolio(positions, cash_reserve)
