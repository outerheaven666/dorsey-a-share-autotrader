from __future__ import annotations

import csv
from pathlib import Path

from dorsey_as.schema_migration.models import MigrationValidationReport
from dorsey_as.schema_migration.validator import build_compatibility_matrix
from dorsey_as.schema_versioning.report import SAFETY_BOUNDARY


def write_schema_migration_report(report: MigrationValidationReport, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "schema_migration_report.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["from_version", "to_version", "dataset", "field", "check_type", "status", "severity", "message"])
        writer.writeheader()
        for row in report.rows:
            writer.writerow(row.__dict__)
    return path


def write_schema_migration_summary(report: MigrationValidationReport, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    plan = report.plan
    matrix = build_compatibility_matrix(plan)
    path = output_dir / "schema_migration_summary.md"
    lines = [
        "# Schema Migration Summary",
        "",
        f"- From version: {plan.from_version}",
        f"- To version: {plan.to_version}",
        f"- Effective date: {plan.effective_date}",
        f"- Compatibility window days: {plan.compatibility_window_days}",
        f"- Total migrations: {len(plan.field_migrations)}",
        f"- Deprecated fields: {len(plan.deprecated_fields)}",
        f"- Pending removals: {report.pending_deprecation_count}",
        f"- Expired deprecations: {report.expired_deprecation_count}",
        f"- Blocking decision: {report.blocking_decision}",
        f"- Compatibility matrix rows: {len(matrix)}",
        "",
        "## Required Actions",
        "",
        *(f"- {item}" for item in plan.required_actions),
        "",
        "## Safety Boundary",
        "",
        SAFETY_BOUNDARY + " Schema migration metadata is used only for pre-integration checks and does not participate in trading decisions.",
        "",
        "## Current Limitations",
        "",
        "- Migration metadata validates local YAML only.",
        "- Migration metadata does not participate in trading decisions.",
        "- No real network data source is enabled.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path

