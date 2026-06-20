from __future__ import annotations

from pathlib import Path
from typing import Any

from dorsey_as.ledger.replay import RuntimeReplayValidator


class RuntimeArtifactValidator:
    """Validates local mock runtime artifacts written by the runtime pipeline."""

    REQUIRED_MARKDOWN_SECTIONS = [
        "Runtime Mode",
        "Strategy Decisions",
        "Risk Check",
        "Replay Validation",
    ]

    def __init__(self, replay_validator: RuntimeReplayValidator | None = None) -> None:
        self.replay_validator = replay_validator or RuntimeReplayValidator()

    def validate(self, output_dir: str | Path = "data/output") -> dict[str, Any]:
        output_path = Path(output_dir)
        ledger_json = output_path / "runtime_ledger_latest.json"
        ledger_csv = output_path / "runtime_ledger_latest.csv"
        report_markdown = output_path / "runtime_report_latest.md"
        report_csv = output_path / "runtime_report_summary.csv"

        checks: list[dict[str, Any]] = []
        self._add_check(checks, "runtime_ledger_json_exists", ledger_json.exists(), f"Ledger JSON: {ledger_json}")
        self._add_check(checks, "runtime_ledger_csv_exists", ledger_csv.exists(), f"Ledger CSV: {ledger_csv}")
        self._add_check(
            checks,
            "runtime_report_markdown_exists",
            report_markdown.exists(),
            f"Runtime report Markdown: {report_markdown}",
        )
        self._add_check(checks, "runtime_report_csv_exists", report_csv.exists(), f"Runtime report CSV: {report_csv}")

        replay = self.replay_validator.validate(json_path=ledger_json, csv_path=ledger_csv)
        self._add_check(
            checks,
            "replay_validation_passes",
            bool(replay["valid"]),
            "Runtime replay validation passed." if replay["valid"] else "Runtime replay validation failed.",
        )

        markdown = report_markdown.read_text(encoding="utf-8") if report_markdown.exists() else ""
        for section in self.REQUIRED_MARKDOWN_SECTIONS:
            self._add_check(
                checks,
                f"report_contains_{section.lower().replace(' ', '_')}",
                section in markdown,
                f"Runtime report contains {section}.",
            )

        return {
            "valid": all(check["passed"] for check in checks),
            "checks": checks,
        }

    def _add_check(self, checks: list[dict[str, Any]], name: str, passed: bool, message: str) -> None:
        checks.append(
            {
                "name": name,
                "passed": passed,
                "message": message,
            }
        )
