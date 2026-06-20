from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


class ScenarioReportWriter:
    """Writes deterministic local reports for the mock runtime scenario matrix."""

    CSV_FIELDS = [
        "scenario_name",
        "passed",
        "checks_total",
        "checks_passed",
        "checks_failed",
        "mode",
    ]

    def write(self, scenario_results: dict[str, Any], output_dir: str | Path = "data/output") -> dict[str, str]:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        markdown_path = output_path / "runtime_scenario_report_latest.md"
        csv_path = output_path / "runtime_scenario_summary.csv"

        markdown_path.write_text(self._markdown(scenario_results), encoding="utf-8")
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=self.CSV_FIELDS)
            writer.writeheader()
            writer.writerows(self._rows(scenario_results))

        return {
            "markdown_path": str(markdown_path),
            "csv_path": str(csv_path),
        }

    def _markdown(self, scenario_results: dict[str, Any]) -> str:
        summary = scenario_results.get("summary", {})
        scenario_rows = scenario_results.get("scenario_results", [])
        lines = [
            "# Runtime Scenario Matrix Report",
            "",
            "## Scenario Matrix Summary",
            "",
            f"- Total Scenarios: {summary.get('total', 0)}",
            f"- Passed: {summary.get('passed', 0)}",
            f"- Failed: {summary.get('failed', 0)}",
            f"- Mode: {summary.get('mode', 'mock')}",
            "",
            "## Per Scenario Results",
            "",
            "| Scenario | Passed | Checks Passed | Checks Failed |",
            "| --- | --- | ---: | ---: |",
        ]
        for row in scenario_rows if isinstance(scenario_rows, list) else []:
            total, passed, failed = self._check_counts(row)
            lines.append(f"| {row.get('name', '')} | {row.get('passed', False)} | {passed} | {failed} |")

        lines.extend(["", "## Checks", ""])
        for row in scenario_rows if isinstance(scenario_rows, list) else []:
            lines.append(f"### {row.get('name', '')}")
            checks = row.get("checks", [])
            if not checks:
                lines.append("- No checks recorded.")
            for check in checks if isinstance(checks, list) else []:
                status = "PASS" if check.get("passed") else "FAIL"
                lines.append(f"- {status}: {check.get('name', '')} - {check.get('message', '')}")
            lines.append("")

        lines.extend(
            [
                "## Runtime Safety Note",
                "",
                "This report is generated from deterministic mock-only runtime scenarios and local artifacts.",
                "It is intended for runtime regression validation and does not add any external execution path.",
                "",
            ]
        )
        return "\n".join(lines)

    def _rows(self, scenario_results: dict[str, Any]) -> list[dict[str, Any]]:
        summary = scenario_results.get("summary", {})
        mode = summary.get("mode", "mock")
        scenario_rows = scenario_results.get("scenario_results", [])
        rows: list[dict[str, Any]] = []
        for row in scenario_rows if isinstance(scenario_rows, list) else []:
            total, passed, failed = self._check_counts(row)
            rows.append(
                {
                    "scenario_name": row.get("name", ""),
                    "passed": row.get("passed", False),
                    "checks_total": total,
                    "checks_passed": passed,
                    "checks_failed": failed,
                    "mode": mode,
                }
            )
        return rows

    def _check_counts(self, scenario_row: dict[str, Any]) -> tuple[int, int, int]:
        checks = scenario_row.get("checks", [])
        if not isinstance(checks, list):
            return 0, 0, 0
        total = len(checks)
        passed = sum(1 for check in checks if check.get("passed"))
        return total, passed, total - passed
