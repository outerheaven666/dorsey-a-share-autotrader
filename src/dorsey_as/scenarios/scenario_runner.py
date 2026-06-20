from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from dorsey_as.engine.runtime import RuntimeEngine
from dorsey_as.scenarios.runtime_scenarios import RUNTIME_SCENARIOS


class RuntimeScenarioRunner:
    """Runs deterministic mock runtime scenarios against the existing runtime flow."""

    def run_all(self, output_dir: str | Path = "data/output") -> dict[str, Any]:
        scenario_results = []
        for scenario in RUNTIME_SCENARIOS:
            runtime_result = RuntimeEngine(output_dir=output_dir).run_once(
                optional_market_data=scenario["market_data"],
                print_output=False,
            )
            checks = self._checks_for(scenario["name"], runtime_result)
            scenario_results.append(
                {
                    "name": scenario["name"],
                    "passed": all(check["passed"] for check in checks),
                    "checks": checks,
                    "runtime_result": runtime_result,
                }
            )

        passed = sum(1 for row in scenario_results if row["passed"])
        total = len(scenario_results)
        return {
            "scenario_results": scenario_results,
            "summary": {
                "total": total,
                "passed": passed,
                "failed": total - passed,
                "mode": "mock",
            },
        }

    def _checks_for(self, name: str, runtime_result: dict[str, Any]) -> list[dict[str, Any]]:
        checks: dict[str, Callable[[dict[str, Any]], list[dict[str, Any]]]] = {
            "baseline_mixed": self._baseline_mixed_checks,
            "all_hold": self._all_hold_checks,
            "buy_single_cap": self._buy_single_cap_checks,
            "sell_path": self._sell_path_checks,
        }
        return checks[name](runtime_result)

    def _baseline_mixed_checks(self, runtime_result: dict[str, Any]) -> list[dict[str, Any]]:
        decisions = {row.get("decision") for row in runtime_result.get("strategy_results", [])}
        return [
            self._check("includes_buy_sell_hold", decisions == {"BUY", "SELL", "HOLD"}, f"decisions={sorted(decisions)}"),
            self._check("risk_approved", runtime_result.get("risk", {}).get("approved") is True, "risk approved is true"),
            self._check("ledger_generated", bool(runtime_result.get("ledger")), "ledger paths exist in runtime output"),
            self._check("replay_valid", runtime_result.get("replay", {}).get("valid") is True, "replay valid is true"),
            self._check("report_generated", bool(runtime_result.get("report")), "report paths exist in runtime output"),
        ]

    def _all_hold_checks(self, runtime_result: dict[str, Any]) -> list[dict[str, Any]]:
        decisions = [row.get("decision") for row in runtime_result.get("strategy_results", [])]
        filled_buy_sell = [
            row
            for row in runtime_result.get("executions", [])
            if row.get("status") == "filled" and row.get("side") in {"buy", "sell"}
        ]
        return [
            self._check("all_decisions_hold", decisions != [] and set(decisions) == {"HOLD"}, f"decisions={decisions}"),
            self._check("no_filled_buy_sell_execution", not filled_buy_sell, f"filled_buy_sell={len(filled_buy_sell)}"),
            self._check("cash_weight_full", runtime_result.get("portfolio", {}).get("cash_weight") == 1.0, "cash weight is 1.0"),
            self._check("risk_approved", runtime_result.get("risk", {}).get("approved") is True, "risk approved is true"),
        ]

    def _buy_single_cap_checks(self, runtime_result: dict[str, Any]) -> list[dict[str, Any]]:
        risk = runtime_result.get("risk", {})
        adjusted_positions = risk.get("adjusted_portfolio", {}).get("positions", [])
        flags = risk.get("risk_flags", [])
        decision = self._first(runtime_result.get("strategy_results", []), "decision")
        capped_weight = self._first(adjusted_positions, "target_weight")
        return [
            self._check("buy_decision", decision == "BUY", f"decision={decision}"),
            self._check("target_weight_capped_to_0_6", capped_weight == 0.6, f"adjusted_weight={capped_weight}"),
            self._check("risk_warning_exists", any(flag.get("severity") == "WARNING" for flag in flags), f"flags={len(flags)}"),
            self._check("risk_approved", risk.get("approved") is True, "risk approved is true"),
        ]

    def _sell_path_checks(self, runtime_result: dict[str, Any]) -> list[dict[str, Any]]:
        positions = runtime_result.get("portfolio", {}).get("positions", [])
        executions = runtime_result.get("executions", [])
        decision = self._first(runtime_result.get("strategy_results", []), "decision")
        return [
            self._check("sell_decision", decision == "SELL", f"decision={decision}"),
            self._check("target_weight_zero", self._first(positions, "target_weight") == 0.0, "target weight is 0.0"),
            self._check(
                "mock_sell_execution_exists",
                any(row.get("side") == "sell" and row.get("status") == "filled" for row in executions),
                f"executions={len(executions)}",
            ),
        ]

    def _first(self, rows: list[dict[str, Any]], key: str) -> Any:
        if not rows:
            return None
        return rows[0].get(key)

    def _check(self, name: str, passed: bool, message: str) -> dict[str, Any]:
        return {
            "name": name,
            "passed": passed,
            "message": message,
        }
