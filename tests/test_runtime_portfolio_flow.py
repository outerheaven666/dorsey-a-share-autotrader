import json

from dorsey_as.engine.runtime import RuntimeEngine


def test_runtime_output_contains_portfolio_flow_sections(capsys) -> None:
    result = RuntimeEngine().run_once()
    printed = json.loads(capsys.readouterr().out)

    for key in ["market_data", "strategy_results", "portfolio", "risk", "executions"]:
        assert key in result
        assert key in printed
    assert len(result["market_data"]) == 3
    assert len(result["strategy_results"]) == 3
    assert result["portfolio"]["portfolio_mode"] == "mock"


def test_runtime_portfolio_flow_is_deterministic() -> None:
    first = RuntimeEngine().run_once(print_output=False)
    second = RuntimeEngine().run_once(print_output=False)

    assert first == second
    assert first["portfolio"]["positions"][0]["symbol"] == "600519.SH"
    assert first["portfolio"]["positions"][0]["target_weight"] == 1.0
    assert first["portfolio"]["cash_weight"] == 0.0
    assert first["risk"]["adjusted_portfolio"]["positions"][0]["target_weight"] == 0.6
    assert first["risk"]["adjusted_portfolio"]["cash_weight"] == 0.4


def test_runtime_executes_buy_sell_and_skips_hold() -> None:
    result = RuntimeEngine().run_once(print_output=False)
    executions = {row["symbol"]: row for row in result["executions"]}

    assert executions["600519.SH"]["status"] == "filled"
    assert executions["600519.SH"]["side"] == "buy"
    assert executions["000001.SZ"]["status"] == "filled"
    assert executions["000001.SZ"]["side"] == "sell"
    assert executions["300750.SZ"] == {"symbol": "300750.SZ", "status": "skipped", "reason": "HOLD"}
