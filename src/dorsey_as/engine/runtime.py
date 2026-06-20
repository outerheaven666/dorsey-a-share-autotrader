from __future__ import annotations

import json
from typing import Any

from dorsey_as.adapters.execution import MockExecutionAdapter
from dorsey_as.strategy.strategy_engine import StrategyEngine


class MockMarketDataProvider:
    """Deterministic local market data provider for runtime smoke tests."""

    def get_latest(self) -> dict[str, Any]:
        return {
            "symbol": "600519.SH",
            "price": 101.0,
        }


class RuntimeEngine:
    """Orchestrates the mock-only runtime flow once."""

    def __init__(
        self,
        market_data_provider: MockMarketDataProvider | None = None,
        strategy_engine: StrategyEngine | None = None,
        execution_adapter: MockExecutionAdapter | None = None,
    ) -> None:
        self.market_data_provider = market_data_provider or MockMarketDataProvider()
        self.strategy_engine = strategy_engine or StrategyEngine()
        self.execution_adapter = execution_adapter or MockExecutionAdapter()

    def run_once(self, print_output: bool = True) -> dict[str, Any]:
        market_data = self.market_data_provider.get_latest()
        strategy_result = self.strategy_engine.evaluate(market_data)
        execution_result = self._execute_decision(strategy_result, market_data)
        result = {
            "market_data": market_data,
            "strategies": strategy_result["strategies"],
            "decision": strategy_result["decision"],
            "execution": execution_result,
        }
        if print_output:
            print(json.dumps(result, ensure_ascii=False))
        return result

    def _execute_decision(self, strategy_result: dict[str, Any], market_data: dict[str, Any]) -> dict[str, Any]:
        decision = strategy_result.get("decision")
        if decision == "HOLD":
            return {
                "status": "skipped",
                "reason": "HOLD",
            }
        order = self._decision_to_order(decision, market_data)
        return self.execution_adapter.fill_order(order)

    def _decision_to_order(self, decision: str, market_data: dict[str, Any]) -> dict[str, Any]:
        side = "buy" if decision == "BUY" else "sell"
        return {
            "symbol": market_data["symbol"],
            "side": side,
            "quantity": 1.0,
            "price": float(market_data.get("price", 0.0)),
        }
