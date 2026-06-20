from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


class RuntimeLedger:
    """Writes a deterministic mock-only runtime trace ledger."""

    RUN_ID = "mock-runtime-run"
    MODE = "mock"
    CSV_FIELDS = [
        "run_id",
        "symbol",
        "price",
        "decision",
        "final_score",
        "target_weight",
        "risk_approved",
        "execution_status",
    ]

    def record(self, run_result: dict[str, Any], output_dir: str | Path = "data/output") -> dict[str, str]:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        json_path = output_path / "runtime_ledger_latest.json"
        csv_path = output_path / "runtime_ledger_latest.csv"

        payload = {
            "run_id": self.RUN_ID,
            "mode": self.MODE,
            "runtime_result": run_result,
        }
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=self.CSV_FIELDS)
            writer.writeheader()
            writer.writerows(self._rows(run_result))

        return {
            "json_path": str(json_path),
            "csv_path": str(csv_path),
        }

    def _rows(self, run_result: dict[str, Any]) -> list[dict[str, Any]]:
        market_data = run_result.get("market_data", [])
        strategies = {row.get("symbol"): row for row in run_result.get("strategy_results", [])}
        positions = {row.get("symbol"): row for row in run_result.get("portfolio", {}).get("positions", [])}
        executions = {row.get("symbol"): row for row in run_result.get("executions", [])}
        risk_approved = run_result.get("risk", {}).get("approved", False)

        rows: list[dict[str, Any]] = []
        for market_row in market_data:
            symbol = market_row.get("symbol", "")
            strategy = strategies.get(symbol, {})
            position = positions.get(symbol, {})
            execution = executions.get(symbol, {})
            rows.append(
                {
                    "run_id": self.RUN_ID,
                    "symbol": symbol,
                    "price": market_row.get("price", ""),
                    "decision": strategy.get("decision", position.get("decision", "")),
                    "final_score": strategy.get("final_score", ""),
                    "target_weight": position.get("target_weight", ""),
                    "risk_approved": risk_approved,
                    "execution_status": execution.get("status", "blocked" if not risk_approved else "not_executed"),
                }
            )
        return rows
