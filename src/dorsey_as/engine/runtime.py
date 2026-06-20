from __future__ import annotations

import json
from typing import Any

from dorsey_as.adapters.execution import MockExecutionAdapter
from dorsey_as.engine.signal_engine import SignalEngine


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
        signal_engine: SignalEngine | None = None,
        execution_adapter: MockExecutionAdapter | None = None,
    ) -> None:
        self.market_data_provider = market_data_provider or MockMarketDataProvider()
        self.signal_engine = signal_engine or SignalEngine()
        self.execution_adapter = execution_adapter or MockExecutionAdapter()

    def run_once(self, print_output: bool = True) -> dict[str, Any]:
        market_data = self.market_data_provider.get_latest()
        signal = self.signal_engine.generate_signal(market_data)
        order = self._signal_to_order(signal, market_data)
        execution_result = self.execution_adapter.fill_order(order)
        result = {
            "market_data": market_data,
            "signal": signal,
            "execution": execution_result,
        }
        if print_output:
            print(json.dumps(result, ensure_ascii=False))
        return result

    def _signal_to_order(self, signal: dict[str, Any], market_data: dict[str, Any]) -> dict[str, Any]:
        side = "buy" if signal.get("action") == "BUY" else "sell"
        return {
            "symbol": signal["symbol"],
            "side": side,
            "quantity": 1.0,
            "price": float(market_data.get("price", 0.0)),
        }
