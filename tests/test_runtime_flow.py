import json

from dorsey_as.engine.runtime import RuntimeEngine
from dorsey_as.engine.signal_engine import SignalEngine


def test_signal_engine_generates_buy_or_hold() -> None:
    engine = SignalEngine()

    buy_signal = engine.generate_signal({"symbol": "600519.SH", "price": 101.0})
    hold_signal = engine.generate_signal({"symbol": "600519.SH", "price": 100.0})

    assert buy_signal["action"] == "BUY"
    assert hold_signal["action"] == "HOLD"
    assert 0.0 <= buy_signal["confidence"] <= 1.0


def test_runtime_run_once_executes_without_error(capsys) -> None:
    result = RuntimeEngine().run_once()
    captured = capsys.readouterr()
    printed = json.loads(captured.out)

    assert result["signal"]["action"] in {"BUY", "HOLD"}
    assert printed["signal"]["action"] in {"BUY", "HOLD"}
    assert result["execution"]["status"] == "filled"
    assert result["execution"]["timestamp"] == "1970-01-01T00:00:00"


def test_runtime_execution_result_is_deterministic() -> None:
    first = RuntimeEngine().run_once(print_output=False)
    second = RuntimeEngine().run_once(print_output=False)

    assert first == second
    assert first["execution"]["fill_price"] == 101.0
    assert first["execution"]["filled_quantity"] == 1.0
