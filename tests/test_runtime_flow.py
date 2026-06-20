import json

from dorsey_as.engine.runtime import RuntimeEngine
from dorsey_as.strategy.strategy_engine import StrategyEngine


class HoldMarketDataProvider:
    def get_latest(self) -> list[dict]:
        return [{"symbol": "600519.SH", "price": 100.0}]


def test_runtime_run_once_executes_without_error(capsys) -> None:
    result = RuntimeEngine().run_once()
    captured = capsys.readouterr()
    printed = json.loads(captured.out)

    assert result["strategy_results"][0]["decision"] in {"BUY", "HOLD", "SELL"}
    assert printed["strategy_results"][0]["decision"] in {"BUY", "HOLD", "SELL"}
    assert result["portfolio"]["portfolio_mode"] == "mock"
    assert result["executions"][0]["status"] == "filled"
    assert result["executions"][0]["timestamp"] == "1970-01-01T00:00:00"


def test_runtime_execution_result_is_deterministic() -> None:
    first = RuntimeEngine().run_once(print_output=False)
    second = RuntimeEngine().run_once(print_output=False)

    assert first == second
    assert first["strategy_results"][0]["decision"] == "BUY"
    assert first["executions"][0]["fill_price"] == 101.0
    assert first["executions"][0]["filled_quantity"] == 1.0


def test_runtime_skips_execution_on_hold() -> None:
    result = RuntimeEngine(market_data_provider=HoldMarketDataProvider(), strategy_engine=StrategyEngine()).run_once(print_output=False)

    assert result["strategy_results"][0]["decision"] == "HOLD"
    assert result["executions"][0] == {"symbol": "600519.SH", "status": "skipped", "reason": "HOLD"}
