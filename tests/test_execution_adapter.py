from dorsey_as.adapters import execution
from dorsey_as.adapters.execution import MockExecutionAdapter
from dorsey_as.adapters.plugin_registry import AdapterPluginRegistry


def test_mock_execution_adapter_fills_order_deterministically() -> None:
    adapter = MockExecutionAdapter()
    order = {"symbol": "600519.SH", "side": "buy", "quantity": 100.0, "price": 1688.5}

    fill = adapter.fill_order(order)

    assert fill["status"] == "filled"
    assert fill["fill_price"] == 1688.5
    assert fill["filled_quantity"] == 100.0
    assert fill["timestamp"] == "1970-01-01T00:00:00"


def test_mock_execution_adapter_uses_default_price_when_missing() -> None:
    adapter = MockExecutionAdapter(default_price=1.0)

    fill = adapter.fill_order({"symbol": "600519.SH", "side": "sell", "quantity": 10.0})

    assert fill["status"] == "filled"
    assert fill["fill_price"] == 1.0
    assert fill["filled_quantity"] == 10.0


def test_execution_adapter_is_auto_discoverable() -> None:
    registry = AdapterPluginRegistry()

    registry.auto_discover(execution)

    assert registry.get("MockExecutionAdapter") is MockExecutionAdapter
