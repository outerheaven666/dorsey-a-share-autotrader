from __future__ import annotations

from typing import Any


class PortfolioEngine:
    """Deterministic mock portfolio target generator."""

    def evaluate(self, strategy_results: list[dict[str, Any]]) -> dict[str, Any]:
        buy_symbols = [row["symbol"] for row in strategy_results if row.get("decision") == "BUY"]
        target_weight = 1.0 / len(buy_symbols) if buy_symbols else 0.0
        positions = []
        invested_weight = 0.0
        for row in strategy_results:
            weight = target_weight if row.get("decision") == "BUY" else 0.0
            invested_weight += weight
            positions.append(
                {
                    "symbol": row["symbol"],
                    "target_weight": weight,
                    "decision": row.get("decision", "HOLD"),
                }
            )
        cash_weight = max(0.0, 1.0 - invested_weight)
        return {
            "positions": positions,
            "cash_weight": cash_weight,
            "portfolio_mode": "mock",
        }
