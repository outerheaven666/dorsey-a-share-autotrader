from __future__ import annotations

import csv
from html import escape
from pathlib import Path

from dorsey_as.config.models import AppConfig
from dorsey_as.schema_migration.models import MigrationPlan, MigrationValidationReport
from dorsey_as.schema_migration.validator import build_compatibility_matrix
from dorsey_as.schema_versioning.report import SAFETY_BOUNDARY


STYLE = """
body{font-family:Arial,Helvetica,sans-serif;margin:0;background:#f7f8fa;color:#1f2937}
main{max-width:1100px;margin:0 auto;padding:32px}
section{background:#fff;border:1px solid #d8dee9;border-radius:8px;padding:18px;margin:18px 0}
table{width:100%;border-collapse:collapse;font-size:14px}th,td{border-bottom:1px solid #e5e7eb;padding:8px;text-align:left}
.metric-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}.metric{background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:12px}
.notice{border-left:4px solid #d1242f}
"""


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def _table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "<p>No data available.</p>"
    head = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body = "".join("<tr>" + "".join(f"<td>{escape(str(value))}</td>" for value in row) + "</tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_No data available._"
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(str(value) for value in row) + " |" for row in rows)
    return "\n".join(lines)


def generate_contract_diff_visualization(output_dir: Path, config: AppConfig, plan: MigrationPlan, migration_report: MigrationValidationReport) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    diff_rows = _read_csv(output_dir / "provider_contract_diff_report.csv")
    matrix = build_compatibility_matrix(plan)
    breaking_rows = [row for row in diff_rows if row.get("breaking") == "True"]
    additive_rows = [row for row in diff_rows if row.get("change_type", "").startswith("additive")]
    dataset_counts: dict[str, int] = {}
    for row in diff_rows:
        dataset_counts[row.get("dataset", "")] = dataset_counts.get(row.get("dataset", ""), 0) + 1

    html = "\n".join(
        [
            "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><title>Provider Contract Diff</title>",
            f"<style>{STYLE}</style></head><body><main>",
            "<h1>Provider Contract Diff Visualization</h1>",
            f"<section class=\"notice\"><h2>Safety Boundary</h2><p>{escape(SAFETY_BOUNDARY)} Schema migration metadata is used only for pre-integration checks and does not participate in trading decisions.</p></section>",
            "<section><h2>Summary</h2><div class=\"metric-grid\">"
            + "".join(
                f"<div class=\"metric\"><strong>{escape(label)}</strong><div>{escape(value)}</div></div>"
                for label, value in [
                    ("Baseline contract path", config.schema_versioning.baseline_contract),
                    ("Candidate contract path", config.schema_versioning.candidate_contract),
                    ("From version", plan.from_version),
                    ("To version", plan.to_version),
                    ("Total changes", str(len(diff_rows))),
                    ("Breaking changes", str(len(breaking_rows))),
                    ("Additive changes", str(len(additive_rows))),
                    ("Compatible changes", str(sum(1 for row in diff_rows if row.get("change_type", "").startswith("compatible")))),
                    ("Disabled provider template", "disabled and non-executable"),
                ]
            )
            + "</div></section>",
            "<section><h2>Dataset Summary</h2>" + _table(["dataset", "change_count"], [[dataset, str(count)] for dataset, count in sorted(dataset_counts.items())]) + "</section>",
            "<section><h2>Field Lifecycle</h2>"
            + _table(["dataset", "field", "canonical", "status", "backward_compatible", "valid_until"], [[row["dataset"], row["field"], row["canonical_field"], row["status"], row["backward_compatible"], row["valid_until"]] for row in matrix])
            + "</section>",
            "<section><h2>Migration Steps</h2>"
            + _table(["dataset", "old_field", "new_field", "change_type", "status", "rule"], [[m.dataset, m.old_field, m.new_field, m.change_type, m.status, m.migration_rule] for m in plan.field_migrations])
            + "</section>",
            "<section><h2>Breaking Change Table</h2>" + _table(["dataset", "field", "message"], [[row.get("dataset", ""), row.get("field", ""), row.get("message", "")] for row in breaking_rows]) + "</section>",
            "<section><h2>Additive Change Table</h2>" + _table(["dataset", "field", "message"], [[row.get("dataset", ""), row.get("field", ""), row.get("message", "")] for row in additive_rows]) + "</section>",
            "<section><h2>Compatibility Matrix</h2>"
            + _table(["dataset", "field", "status", "backward_compatible", "valid_until"], [[row["dataset"], row["field"], row["status"], row["backward_compatible"], row["valid_until"]] for row in matrix])
            + "</section>",
            "</main></body></html>",
        ]
    )
    html_path = output_dir / "provider_contract_diff.html"
    html_path.write_text(html, encoding="utf-8")

    summary_path = output_dir / "provider_contract_diff_visual_summary.md"
    summary_lines = [
        "# Provider Contract Diff Visual Summary",
        "",
        f"- Baseline contract path: {config.schema_versioning.baseline_contract}",
        f"- Candidate contract path: {config.schema_versioning.candidate_contract}",
        f"- From version: {plan.from_version}",
        f"- To version: {plan.to_version}",
        f"- Total changes: {len(diff_rows)}",
        f"- Breaking changes: {len(breaking_rows)}",
        f"- Additive changes: {len(additive_rows)}",
        f"- Migration blocking decision: {migration_report.blocking_decision}",
        f"- Disabled provider template status: disabled and non-executable",
        "",
        "## Compatibility Matrix",
        "",
        _markdown_table(["dataset", "field", "status", "backward_compatible", "valid_until"], [[row["dataset"], row["field"], row["status"], row["backward_compatible"], row["valid_until"]] for row in matrix]),
        "",
        "## Safety Boundary",
        "",
        SAFETY_BOUNDARY + " Schema migration metadata is used only for pre-integration checks and does not participate in trading decisions.",
    ]
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    return html_path, summary_path
