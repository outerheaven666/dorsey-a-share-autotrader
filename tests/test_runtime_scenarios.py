from pathlib import Path

from dorsey_as.scenarios.scenario_runner import RuntimeScenarioRunner


def _scenario_by_name(results: dict, name: str) -> dict:
    return next(row for row in results["scenario_results"] if row["name"] == name)


def test_runtime_scenario_runner_passes_all_predefined_scenarios(tmp_path: Path) -> None:
    results = RuntimeScenarioRunner().run_all(output_dir=tmp_path)

    assert results["summary"] == {
        "total": 4,
        "passed": 4,
        "failed": 0,
        "mode": "mock",
    }
    assert {row["name"] for row in results["scenario_results"]} == {
        "baseline_mixed",
        "all_hold",
        "buy_single_cap",
        "sell_path",
    }
    assert all(row["passed"] for row in results["scenario_results"])


def test_baseline_mixed_scenario_covers_buy_sell_hold_and_artifacts(tmp_path: Path) -> None:
    results = RuntimeScenarioRunner().run_all(output_dir=tmp_path)
    scenario = _scenario_by_name(results, "baseline_mixed")

    decisions = {row["decision"] for row in scenario["runtime_result"]["strategy_results"]}
    assert decisions == {"BUY", "SELL", "HOLD"}
    assert scenario["runtime_result"]["risk"]["approved"] is True
    assert scenario["runtime_result"]["replay"]["valid"] is True
    assert scenario["runtime_result"]["ledger"]
    assert scenario["runtime_result"]["report"]


def test_all_hold_scenario_has_full_cash_and_no_filled_trade(tmp_path: Path) -> None:
    results = RuntimeScenarioRunner().run_all(output_dir=tmp_path)
    scenario = _scenario_by_name(results, "all_hold")
    runtime_result = scenario["runtime_result"]

    assert {row["decision"] for row in runtime_result["strategy_results"]} == {"HOLD"}
    assert runtime_result["portfolio"]["cash_weight"] == 1.0
    assert runtime_result["risk"]["approved"] is True
    assert all(row["status"] != "filled" for row in runtime_result["executions"])


def test_buy_single_cap_scenario_has_risk_cap_warning(tmp_path: Path) -> None:
    results = RuntimeScenarioRunner().run_all(output_dir=tmp_path)
    scenario = _scenario_by_name(results, "buy_single_cap")
    risk = scenario["runtime_result"]["risk"]

    assert scenario["runtime_result"]["strategy_results"][0]["decision"] == "BUY"
    assert risk["approved"] is True
    assert risk["adjusted_portfolio"]["positions"][0]["target_weight"] == 0.6
    assert any(flag["severity"] == "WARNING" for flag in risk["risk_flags"])


def test_sell_path_scenario_has_mock_sell_execution(tmp_path: Path) -> None:
    results = RuntimeScenarioRunner().run_all(output_dir=tmp_path)
    scenario = _scenario_by_name(results, "sell_path")
    runtime_result = scenario["runtime_result"]

    assert runtime_result["strategy_results"][0]["decision"] == "SELL"
    assert runtime_result["portfolio"]["positions"][0]["target_weight"] == 0.0
    assert runtime_result["executions"][0]["side"] == "sell"
    assert runtime_result["executions"][0]["status"] == "filled"
