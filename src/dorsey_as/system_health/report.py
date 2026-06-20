from __future__ import annotations

import csv
from pathlib import Path

from dorsey_as.config.models import AppConfig
from dorsey_as.system_health.checks import build_artifact_manifest
from dorsey_as.system_health.models import ReleaseChecklistItem, ReleaseNotesDraft, SensitiveScanResult, SystemHealthResult
from dorsey_as.system_health.release import SAFETY_BOUNDARY


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_system_health_report(result: SystemHealthResult, output_dir: Path) -> Path:
    return _write_csv(
        output_dir / "system_health_report.csv",
        ["check", "category", "status", "severity", "blocking", "message"],
        [item.__dict__ for item in result.items],
    )


def write_system_health_summary(result: SystemHealthResult, config: AppConfig, output_dir: Path) -> Path:
    path = output_dir / "system_health_summary.md"
    total = len(result.items)
    passed = sum(1 for item in result.items if item.status == "pass")
    warnings = len(result.warnings)
    blocking = len(result.blocking_issues)
    lines = [
        "# System Health Summary",
        "",
        f"- release_version: {config.system_health.release_version}",
        f"- total checks: {total}",
        f"- passed checks: {passed}",
        f"- warnings: {warnings}",
        f"- blocking issues: {blocking}",
        f"- sensitive scan result: {'pass' if not any(item.check == 'sensitive scan' and item.blocking for item in result.items) else 'blocking'}",
        f"- safety config result: {'pass' if not any(item.category == 'safety_config' and item.blocking for item in result.items) else 'blocking'}",
        f"- provider registry result: {'pass' if not any(item.category == 'provider_registry' and item.blocking for item in result.items) else 'blocking'}",
        "- output artifact policy: data/output is expected to be ignored by git",
        "",
        "## Current Safety Boundary",
        "",
        SAFETY_BOUNDARY,
        "",
        "## Current Limitations",
        "",
        "- Local checks only.",
        "- No automatic commit, tag, push, or release.",
        "- Artifact existence checks are report-oriented and do not execute the full validation sequence.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_sensitive_scan_report(result: SensitiveScanResult, output_dir: Path) -> Path:
    return _write_csv(
        output_dir / "sensitive_scan_report.csv",
        ["path", "line", "pattern", "severity", "blocking", "context"],
        [finding.__dict__ for finding in result.findings],
    )


def write_sensitive_scan_summary(result: SensitiveScanResult, config: AppConfig, output_dir: Path) -> Path:
    path = output_dir / "sensitive_scan_summary.md"
    lines = [
        "# Sensitive Scan Summary",
        "",
        f"- release_version: {config.system_health.release_version}",
        f"- scanned paths: {', '.join(config.sensitive_scan.scan_paths)}",
        f"- findings: {len(result.findings)}",
        f"- warnings: {len(result.warnings)}",
        f"- blocking findings: {len(result.blocking_findings)}",
        "",
        "Documentation-only mentions of provider names are allowed when they explain the disabled local-only safety boundary. Credential-like assignments and real SDK imports remain blocking.",
        "",
        "## Safety Boundary",
        "",
        SAFETY_BOUNDARY,
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_artifact_manifest(output_dir: Path, root: Path | None = None) -> tuple[Path, Path]:
    rows = build_artifact_manifest(output_dir, root)
    csv_path = _write_csv(
        output_dir / "output_artifact_manifest.csv",
        ["artifact", "expected", "exists", "generated_by", "tracked_by_git", "note"],
        rows,
    )
    md_path = output_dir / "output_artifact_manifest.md"
    lines = [
        "# Output Artifact Manifest",
        "",
        "| artifact | expected | exists | generated_by | tracked_by_git | note |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    lines.extend(
        f"| {row['artifact']} | {row['expected']} | {row['exists']} | {row['generated_by']} | {row['tracked_by_git']} | {row['note']} |"
        for row in rows
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return csv_path, md_path


def write_release_checklist(items: list[ReleaseChecklistItem], config: AppConfig, output_dir: Path) -> tuple[Path, Path]:
    csv_path = _write_csv(
        output_dir / "release_checklist.csv",
        ["item", "required", "status", "blocking", "evidence", "message"],
        [item.__dict__ for item in items],
    )
    md_path = output_dir / "release_checklist.md"
    blocking = sum(1 for item in items if item.blocking)
    lines = [
        "# Release Checklist",
        "",
        f"- release_version: {config.release_checklist.release_version}",
        f"- blocking issues: {blocking}",
        "",
        "## MVP Coverage Summary",
        "",
        "MVP 1-11 are covered by local scoring, portfolio, paper broker, backtest, data quality, point-in-time, factor audit, adapter contract, schema versioning, schema migration, pre-live safety, system health, and release checklist layers.",
        "",
        "## Validation Commands Checklist",
        "",
        "- python -m pytest",
        "- python -m dorsey_as system-health --config config/default.yaml",
        "- python -m dorsey_as scan-sensitive-content --config config/default.yaml",
        "- python -m dorsey_as release-checklist --config config/default.yaml",
        "- python -m dorsey_as generate-release-notes --config config/default.yaml",
        "",
        "## Required Output Files Checklist",
        "",
        "| item | required | status | blocking | evidence | message |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    lines.extend(
        f"| {item.item} | {item.required} | {item.status} | {item.blocking} | {item.evidence} | {item.message} |"
        for item in items
    )
    lines.extend(
        [
            "",
            "## Safety Boundary Checklist",
            "",
            SAFETY_BOUNDARY,
            "",
            "## Manual Release Steps",
            "",
            "- Run validation commands.",
            "- Inspect git status.",
            "- Create PR.",
            "- Merge PR.",
            "- Pull main.",
            "- Run final validation.",
            f"- git tag {config.release_checklist.release_version}",
            f"- git push origin {config.release_checklist.release_version}",
            "",
            "This command does not commit, tag, push, or publish anything automatically.",
            "",
            "## Current Limitations",
            "",
            "- Local release checklist only.",
            "- Manual review is required before any tag or PR action.",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return csv_path, md_path


def write_release_notes(draft: ReleaseNotesDraft, output_dir: Path) -> Path:
    path = output_dir / f"release_notes_{draft.release_version}.md"
    path.write_text(draft.content + "\n", encoding="utf-8")
    return path
