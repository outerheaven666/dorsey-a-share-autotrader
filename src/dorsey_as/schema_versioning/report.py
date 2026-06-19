from __future__ import annotations

import csv
from pathlib import Path

from dorsey_as.schema_versioning.models import ContractDiffReport


SAFETY_BOUNDARY = (
    "No real-money trading is supported. No real broker connection exists. "
    "No real network data source connection exists. Mock provider is only used for contract testing and is not an actual market data source. "
    "Real provider template is disabled by default, non-executable, and will not connect to real providers."
)


def write_contract_diff_report(report: ContractDiffReport, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "provider_contract_diff_report.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["dataset", "field", "change_type", "severity", "baseline_value", "candidate_value", "breaking", "message"],
        )
        writer.writeheader()
        for row in report.rows:
            writer.writerow(row.__dict__)
    return path


def write_contract_diff_summary(report: ContractDiffReport, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "provider_contract_diff_summary.md"
    lines = [
        "# Provider Contract Diff Summary",
        "",
        f"- Baseline contract: {report.baseline_path}",
        f"- Candidate contract: {report.candidate_path}",
        f"- Total changes: {len(report.rows)}",
        f"- Breaking changes: {report.breaking_count}",
        f"- Additive changes: {report.additive_count}",
        f"- Compatible changes: {report.compatible_count}",
        f"- Blocking decision: {report.blocking_decision}",
        "",
        "## Safety Boundary",
        "",
        SAFETY_BOUNDARY,
        "",
        "## Current Limitations",
        "",
        "- Contract diff checks local YAML files only.",
        "- Contract diff does not participate in trading decisions.",
        "- No real network data source is enabled.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
