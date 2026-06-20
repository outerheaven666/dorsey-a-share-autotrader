from __future__ import annotations

from typing import Any


class StrategyEngine:
    """Deterministic mock multi-strategy engine."""

    def evaluate(self, market_data: dict[str, Any]) -> dict[str, Any]:
        price = float(market_data.get("price", 0.0))
        if price > 100:
            mean_reversion = -0.2
            momentum = 1.0
        elif price < 100:
            mean_reversion = 0.2
            momentum = -1.0
        else:
            mean_reversion = 0.0
            momentum = 0.0

        strategies = [
            {"name": "mean_reversion", "score": mean_reversion},
            {"name": "momentum", "score": momentum},
        ]
        final_score = sum(row["score"] for row in strategies) / len(strategies)
        if final_score > 0.3:
            decision = "BUY"
        elif final_score < -0.3:
            decision = "SELL"
        else:
            decision = "HOLD"
        return {
            "strategies": strategies,
            "final_score": final_score,
            "decision": decision,
        }
