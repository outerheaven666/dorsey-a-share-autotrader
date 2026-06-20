from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


class RuntimeReportWriter:
    """Writes deterministic human-readable reports for a mock runtime result."""

    CSV_FIELDS = [
        "symbol",
        "price",
        "decision",
        "final_score",
        "target_weight",
        "risk_approved",
        "execution_status",
    ]

    def write(self, runtime_result: dict[str, Any], output_dir: str | Path = "data/output") -> dict[str, str]:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        markdown_path = output_path / "runtime_report_latest.md"
        csv_path = output_path / "runtime_report_summary.csv"

        markdown_path.write_text(self._markdown(runtime_result), encoding="utf-8")
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=self.CSV_FIELDS)
            writer.writeheader()
            writer.writerows(self._summary_rows(runtime_result))

        return {
            "markdown_path": str(markdown_path),
            "csv_path": str(csv_path),
        }

    def _markdown(self, runtime_result: dict[str, Any]) -> str:
        replay = runtime_result.get("replay", {})
        replay_summary = replay.get("summary", {})
        ledger = runtime_result.get("ledger", {})
        risk = runtime_result.get("risk", {})

        sections = [
            "# Runtime Report",
            "",
            "## Runtime Mode",
            "",
            f"- Mode: {replay_summary.get('mode', 'mock')}",
            "",
            "## Market Data Summary",
            "",
            self._market_data_table(runtime_result),
            "",
            "## Strategy Decisions",
            "",
            self._strategy_table(runtime_result),
            "",
            "## Portfolio Allocation",
            "",
            self._portfolio_table(runtime_result),
            "",
            "## Risk Check",
            "",
            f"- Approved: {risk.get('approved', '')}",
            f"- Flags: {len(risk.get('risk_flags', [])) if isinstance(risk.get('risk_flags', []), list) else 0}",
            "",
            "## Executions",
            "",
            self._execution_table(runtime_result),
            "",
            "## Ledger Paths",
            "",
            f"- JSON: {ledger.get('json_path', '')}",
            f"- CSV: {ledger.get('csv_path', '')}",
            "",
            "## Replay Validation",
            "",
            f"- Valid: {replay.get('valid', '')}",
            f"- Symbols checked: {replay_summary.get('symbols_checked', 0)}",
            f"- Executions checked: {replay_summary.get('executions_checked', 0)}",
            "",
        ]
        return "\n".join(sections)

    def _summary_rows(self, runtime_result: dict[str, Any]) -> list[dict[str, Any]]:
        market_data = runtime_result.get("market_data", [])
        strategies = {row.get("symbol"): row for row in runtime_result.get("strategy_results", [])}
        positions = {row.get("symbol"): row for row in runtime_result.get("portfolio", {}).get("positions", [])}
        executions = {row.get("symbol"): row for row in runtime_result.get("executions", [])}
        risk_approved = runtime_result.get("risk", {}).get("approved", False)

        rows: list[dict[str, Any]] = []
        for market_row in market_data if isinstance(market_data, list) else []:
            symbol = market_row.get("symbol", "")
            strategy = strategies.get(symbol, {})
            position = positions.get(symbol, {})
            execution = executions.get(symbol, {})
            rows.append(
                {
                    "symbol": symbol,
                    "price": market_row.get("price", ""),
                    "decision": strategy.get("decision", position.get("decision", "")),
                    "final_score": strategy.get("final_score", ""),
                    "target_weight": position.get("target_weight", ""),
                    "risk_approved": risk_approved,
                    "execution_status": execution.get("status", "not_executed"),
                }
            )
        return rows

    def _market_data_table(self, runtime_result: dict[str, Any]) -> str:
        rows = runtime_result.get("market_data", [])
        if not rows:
            return "No market data."
        lines = ["| Symbol | Price |", "| --- | ---: |"]
        lines.extend(f"| {row.get('symbol', '')} | {row.get('price', '')} |" for row in rows)
        return "\n".join(lines)

    def _strategy_table(self, runtime_result: dict[str, Any]) -> str:
        rows = runtime_result.get("strategy_results", [])
        if not rows:
            return "No strategy decisions."
        lines = ["| Symbol | Decision | Final Score |", "| --- | --- | ---: |"]
        lines.extend(
            f"| {row.get('symbol', '')} | {row.get('decision', '')} | {row.get('final_score', '')} |"
            for row in rows
        )
        return "\n".join(lines)

    def _portfolio_table(self, runtime_result: dict[str, Any]) -> str:
        positions = runtime_result.get("portfolio", {}).get("positions", [])
        if not positions:
            return "No portfolio positions."
        lines = ["| Symbol | Decision | Target Weight |", "| --- | --- | ---: |"]
        lines.extend(
            f"| {row.get('symbol', '')} | {row.get('decision', '')} | {row.get('target_weight', '')} |"
            for row in positions
        )
        return "\n".join(lines)

    def _execution_table(self, runtime_result: dict[str, Any]) -> str:
        rows = runtime_result.get("executions", [])
        if not rows:
            return "No executions."
        lines = ["| Symbol | Status | Side |", "| --- | --- | --- |"]
        lines.extend(
            f"| {row.get('symbol', '')} | {row.get('status', '')} | {row.get('side', '')} |" for row in rows
        )
        return "\n".join(lines)
