from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dorsey_as.adapters.execution import MockExecutionAdapter
from dorsey_as.ledger.replay import RuntimeReplayValidator
from dorsey_as.ledger.runtime_ledger import RuntimeLedger
from dorsey_as.portfolio.portfolio_engine import PortfolioEngine
from dorsey_as.reporting.runtime_report import RuntimeReportWriter
from dorsey_as.risk.risk_engine import RiskEngine
from dorsey_as.strategy.strategy_engine import StrategyEngine


class MockMarketDataProvider:
    """Deterministic local market data provider for runtime smoke tests."""

    def get_latest(self) -> list[dict[str, Any]]:
        return [
            {"symbol": "600519.SH", "price": 101.0},
            {"symbol": "000001.SZ", "price": 99.0},
            {"symbol": "300750.SZ", "price": 100.0},
        ]


class RuntimeEngine:
    """Orchestrates the mock-only runtime flow once."""

    def __init__(
        self,
        market_data_provider: MockMarketDataProvider | None = None,
        strategy_engine: StrategyEngine | None = None,
        portfolio_engine: PortfolioEngine | None = None,
        risk_engine: RiskEngine | None = None,
        execution_adapter: MockExecutionAdapter | None = None,
        runtime_ledger: RuntimeLedger | None = None,
        replay_validator: RuntimeReplayValidator | None = None,
        report_writer: RuntimeReportWriter | None = None,
        output_dir: str | Path = "data/output",
    ) -> None:
        self.market_data_provider = market_data_provider or MockMarketDataProvider()
        self.strategy_engine = strategy_engine or StrategyEngine()
        self.portfolio_engine = portfolio_engine or PortfolioEngine()
        self.risk_engine = risk_engine or RiskEngine()
        self.execution_adapter = execution_adapter or MockExecutionAdapter()
        self.runtime_ledger = runtime_ledger or RuntimeLedger()
        self.replay_validator = replay_validator or RuntimeReplayValidator()
        self.report_writer = report_writer or RuntimeReportWriter()
        self.output_dir = output_dir

    def run_once(self, print_output: bool = True) -> dict[str, Any]:
        market_data = self.market_data_provider.get_latest()
        strategy_results = [self._evaluate_symbol(row) for row in market_data]
        portfolio = self.portfolio_engine.evaluate(strategy_results)
        risk = self.risk_engine.evaluate(portfolio)
        executions = self._execute_if_approved(risk, strategy_results, market_data)
        result = {
            "market_data": market_data,
            "strategy_results": strategy_results,
            "portfolio": portfolio,
            "risk": risk,
            "executions": executions,
        }
        ledger_paths = self.runtime_ledger.record(result, output_dir=self.output_dir)
        replay = self.replay_validator.validate(
            json_path=ledger_paths["json_path"],
            csv_path=ledger_paths["csv_path"],
        )
        result["ledger"] = ledger_paths
        result["replay"] = {
            "valid": replay["valid"],
            "summary": replay["summary"],
        }
        result["report"] = self.report_writer.write(result, output_dir=self.output_dir)
        if print_output:
            print(json.dumps(result, ensure_ascii=False))
        return result

    def _evaluate_symbol(self, market_data: dict[str, Any]) -> dict[str, Any]:
        strategy_result = self.strategy_engine.evaluate(market_data)
        return {
            "symbol": market_data["symbol"],
            "strategies": strategy_result["strategies"],
            "final_score": strategy_result["final_score"],
            "decision": strategy_result["decision"],
        }

    def _execute_if_approved(
        self,
        risk: dict[str, Any],
        strategy_results: list[dict[str, Any]],
        market_data: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not risk.get("approved"):
            return []
        return [self._execute_decision(row, market) for row, market in zip(strategy_results, market_data)]

    def _execute_decision(self, strategy_result: dict[str, Any], market_data: dict[str, Any]) -> dict[str, Any]:
        decision = strategy_result.get("decision")
        if decision == "HOLD":
            return {
                "symbol": strategy_result["symbol"],
                "status": "skipped",
                "reason": "HOLD",
            }
        order = self._decision_to_order(decision, market_data)
        execution = self.execution_adapter.fill_order(order)
        return {
            "symbol": strategy_result["symbol"],
            "side": order["side"],
            **execution,
        }

    def _decision_to_order(self, decision: str, market_data: dict[str, Any]) -> dict[str, Any]:
        side = "buy" if decision == "BUY" else "sell"
        return {
            "symbol": market_data["symbol"],
            "side": side,
            "quantity": 1.0,
            "price": float(market_data.get("price", 0.0)),
        }
