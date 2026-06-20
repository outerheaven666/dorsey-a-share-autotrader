from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


class RuntimeReplayValidator:
    """Validates saved mock runtime ledger files for deterministic replay checks."""

    REQUIRED_RUNTIME_KEYS = ["market_data", "strategy_results", "portfolio", "risk", "executions"]
    REQUIRED_CSV_FIELDS = [
        "run_id",
        "symbol",
        "price",
        "decision",
        "final_score",
        "target_weight",
        "risk_approved",
        "execution_status",
    ]

    def validate(
        self,
        json_path: str | Path = "data/output/runtime_ledger_latest.json",
        csv_path: str | Path = "data/output/runtime_ledger_latest.csv",
    ) -> dict[str, Any]:
        json_file = Path(json_path)
        csv_file = Path(csv_path)
        checks: list[dict[str, Any]] = []
        payload: dict[str, Any] = {}
        runtime_result: dict[str, Any] = {}
        csv_rows: list[dict[str, str]] = []
        csv_fields: list[str] = []

        self._add_check(checks, "json_file_exists", json_file.exists(), f"JSON ledger file: {json_file}")
        self._add_check(checks, "csv_file_exists", csv_file.exists(), f"CSV ledger file: {csv_file}")

        if json_file.exists():
            try:
                payload = json.loads(json_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                self._add_check(checks, "json_parseable", False, f"JSON ledger is not parseable: {exc}")
            else:
                self._add_check(checks, "json_parseable", True, "JSON ledger is parseable.")

        if csv_file.exists():
            with csv_file.open(newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                csv_fields = list(reader.fieldnames or [])
                csv_rows = list(reader)

        if payload:
            runtime_result = payload.get("runtime_result", {})
            self._add_check(checks, "json_has_run_id", bool(payload.get("run_id")), "JSON ledger has run_id.")
            self._add_check(checks, "json_mode_is_mock", payload.get("mode") == "mock", "JSON ledger mode is mock.")
            self._add_check(
                checks,
                "json_has_runtime_result",
                isinstance(runtime_result, dict) and bool(runtime_result),
                "JSON ledger has runtime_result.",
            )
            for key in self.REQUIRED_RUNTIME_KEYS:
                self._add_check(
                    checks,
                    f"runtime_result_has_{key}",
                    key in runtime_result,
                    f"runtime_result includes {key}.",
                )

        if csv_file.exists():
            missing_fields = [field for field in self.REQUIRED_CSV_FIELDS if field not in csv_fields]
            self._add_check(
                checks,
                "csv_has_required_fields",
                not missing_fields,
                "CSV ledger contains required fields."
                if not missing_fields
                else f"CSV ledger missing fields: {', '.join(missing_fields)}.",
            )

        market_data = runtime_result.get("market_data", []) if isinstance(runtime_result, dict) else []
        executions = runtime_result.get("executions", []) if isinstance(runtime_result, dict) else []
        if csv_file.exists() and market_data:
            self._add_check(
                checks,
                "csv_one_row_per_symbol",
                len(csv_rows) == len(market_data),
                f"CSV rows: {len(csv_rows)}; market symbols: {len(market_data)}.",
            )

        return {
            "valid": all(check["passed"] for check in checks),
            "checks": checks,
            "summary": {
                "symbols_checked": len(market_data) if isinstance(market_data, list) else 0,
                "executions_checked": len(executions) if isinstance(executions, list) else 0,
                "mode": "mock",
            },
        }

    def _add_check(self, checks: list[dict[str, Any]], name: str, passed: bool, message: str) -> None:
        checks.append(
            {
                "name": name,
                "passed": passed,
                "message": message,
            }
        )
