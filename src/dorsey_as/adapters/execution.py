from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ExecutionAdapter(ABC):
    """Interface for execution adapters.

    The current system is mock-only. Implementations must not connect to a
    broker, place real orders, or make network calls.
    """

    @abstractmethod
    def fill_order(self, order: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class MockExecutionAdapter(ExecutionAdapter):
    """Deterministic local order fill simulator."""

    name = "mock_execution"
    fixed_timestamp = "1970-01-01T00:00:00"

    def __init__(self, default_price: float = 0.0) -> None:
        self.default_price = float(default_price)

    def fill_order(self, order: dict[str, Any]) -> dict[str, Any]:
        symbol = str(order.get("symbol", "")).strip()
        side = str(order.get("side", "")).lower()
        if not symbol:
            raise ValueError("order.symbol is required")
        if side not in {"buy", "sell"}:
            raise ValueError("order.side must be buy or sell")

        quantity = float(order.get("quantity", 0.0))
        if quantity <= 0:
            raise ValueError("order.quantity must be positive")

        fill_price = float(order.get("price", self.default_price))
        if fill_price < 0:
            raise ValueError("order.price must be non-negative")

        return {
            "status": "filled",
            "fill_price": fill_price,
            "filled_quantity": quantity,
            "timestamp": self.fixed_timestamp,
        }
