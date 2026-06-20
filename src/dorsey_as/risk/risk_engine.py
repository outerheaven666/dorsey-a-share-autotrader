from __future__ import annotations

from copy import deepcopy
from typing import Any


class RiskEngine:
    """Deterministic mock portfolio risk guard."""

    max_single_position_weight = 0.6
    max_total_invested_weight = 1.0

    def evaluate(self, portfolio: dict[str, Any]) -> dict[str, Any]:
        adjusted = deepcopy(portfolio)
        flags: list[dict[str, str]] = []

        for position in adjusted.get("positions", []):
            weight = float(position.get("target_weight", 0.0))
            if weight < 0:
                flags.append(
                    {
                        "code": "NEGATIVE_POSITION_WEIGHT",
                        "message": f"{position.get('symbol', '')} has negative target weight.",
                        "severity": "BLOCKING",
                    }
                )
            if weight > self.max_single_position_weight:
                position["target_weight"] = self.max_single_position_weight
                flags.append(
                    {
                        "code": "MAX_SINGLE_POSITION_CAPPED",
                        "message": f"{position.get('symbol', '')} target weight capped to 0.6.",
                        "severity": "WARNING",
                    }
                )

        cash_weight = float(adjusted.get("cash_weight", 0.0))
        if cash_weight < 0:
            adjusted["cash_weight"] = 0.0
            flags.append(
                {
                    "code": "NEGATIVE_CASH_WEIGHT",
                    "message": "cash_weight cannot be negative.",
                    "severity": "BLOCKING",
                }
            )

        total_invested = sum(float(position.get("target_weight", 0.0)) for position in adjusted.get("positions", []))
        if total_invested > self.max_total_invested_weight:
            flags.append(
                {
                    "code": "TOTAL_INVESTED_WEIGHT_EXCEEDED",
                    "message": "Total invested weight exceeds 1.0.",
                    "severity": "BLOCKING",
                }
            )
        else:
            adjusted["cash_weight"] = max(0.0, 1.0 - total_invested)

        blocking = any(flag["severity"] == "BLOCKING" for flag in flags)
        if not flags:
            flags.append(
                {
                    "code": "RISK_CHECK_PASSED",
                    "message": "Mock portfolio risk check passed.",
                    "severity": "INFO",
                }
            )
        return {
            "approved": not blocking,
            "risk_flags": flags,
            "adjusted_portfolio": adjusted,
        }
