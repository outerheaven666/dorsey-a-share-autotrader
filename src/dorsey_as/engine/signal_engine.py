from __future__ import annotations

from typing import Any


class SignalEngine:
    """Deterministic mock signal engine."""

    def generate_signal(self, market_data: dict[str, Any]) -> dict[str, Any]:
        symbol = str(market_data.get("symbol", "")).strip()
        price = float(market_data.get("price", 0.0))
        action = "BUY" if price > 100 else "HOLD"
        confidence = 0.8 if action == "BUY" else 0.5
        return {
            "symbol": symbol,
            "action": action,
            "confidence": confidence,
        }

