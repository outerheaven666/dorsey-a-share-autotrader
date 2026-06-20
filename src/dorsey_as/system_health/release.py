from __future__ import annotations

from pathlib import Path

from dorsey_as.config.models import AppConfig
from dorsey_as.system_health.checks import data_output_is_ignored
from dorsey_as.system_health.models import ReleaseChecklistItem, ReleaseNotesDraft, SystemHealthResult


SAFETY_BOUNDARY = (
    "Current system does not provide investment advice, does not guarantee returns, "
    "does not support real trading, has no real broker connection, has no real network data source connection, "
    "and is only for personal research, system development, paper trading, and backtest simulation. "
    "Mock provider is contract-test only. Real provider template is disabled-by-default and non-executable. "
    "Schema migration metadata is pre-integration metadata only. Pre-live safety gate blocks live trading, "
    "real broker, real order, and real network data. System health and release checklist generate local reports only; "
    "this release process does not publish, tag, push, or release automatically."
)


def build_release_checklist(config: AppConfig, health: SystemHealthResult, output_dir: Path, root: Path | None = None) -> list[ReleaseChecklistItem]:
    project_root = root or Path.cwd()
    health_blocking = len(health.blocking_issues)
    ignored = data_output_is_ignored(project_root)
    report_files = ["run_report.md", "run_report.html", "backtest_report.md", "backtest_report.html"]
    report_count = sum(1 for name in report_files if (output_dir / name).exists())
    items = [
        ReleaseChecklistItem("pytest", config.release_checklist.require_pytest_passed, "manual", False, "python -m pytest", "Run locally before final release tagging."),
        ReleaseChecklistItem("system health", config.release_checklist.require_health_check_passed, "pass" if health_blocking == 0 else "fail", health_blocking > 0, f"blocking={health_blocking}", "System health has no blocking issue." if health_blocking == 0 else "System health has blocking issues."),
        ReleaseChecklistItem("pre-live safety", config.release_checklist.require_pre_live_safety_passed, "pass" if (output_dir / "pre_live_safety_report.csv").exists() else "manual", False, "check-pre-live-safety", "Pre-live safety report should be inspected before release."),
        ReleaseChecklistItem("contract diff", config.release_checklist.require_contract_diff_passed, "pass" if (output_dir / "provider_contract_diff_report.csv").exists() else "manual", False, "diff-provider-contract", "Contract diff should be inspected before release."),
        ReleaseChecklistItem("schema migration", config.release_checklist.require_schema_migration_passed, "pass" if (output_dir / "schema_migration_report.csv").exists() else "manual", False, "validate-schema-migration", "Schema migration report should be inspected before release."),
        ReleaseChecklistItem("provider contract", config.release_checklist.require_provider_contract_passed, "pass" if (output_dir / "provider_contract_report.csv").exists() else "manual", False, "validate-provider-contract", "Mock provider contract should be inspected before release."),
        ReleaseChecklistItem("data quality", config.release_checklist.require_data_quality_passed, "pass" if (output_dir / "data_quality_report.csv").exists() else "manual", False, "check-data-quality", "Data quality output should be inspected before release."),
        ReleaseChecklistItem("backtest", config.release_checklist.require_backtest_passed, "pass" if (output_dir / "backtest_metrics.csv").exists() else "manual", False, "run-backtest", "Backtest output should be inspected before release."),
        ReleaseChecklistItem("reports generated", config.release_checklist.require_reports_generated, "pass" if report_count == len(report_files) else "manual", False, f"{report_count}/{len(report_files)} reports", "Generate Markdown and HTML reports before release."),
        ReleaseChecklistItem("no sensitive strings", config.release_checklist.require_no_sensitive_strings, "pass" if not any(item.check == "sensitive scan" and item.blocking for item in health.items) else "fail", any(item.check == "sensitive scan" and item.blocking for item in health.items), "sensitive scan", "Sensitive scan has no blocking findings."),
        ReleaseChecklistItem("data/output untracked", config.release_checklist.require_no_data_output_tracked, "pass" if ignored else "fail", not ignored, ".gitignore", "data/output remains ignored."),
    ]
    return items


def build_release_notes_draft(config: AppConfig) -> ReleaseNotesDraft:
    version = config.release_checklist.release_version
    content = "\n".join(
        [
            f"# {version}",
            "",
            "## Summary",
            "",
            "This is a research-only release candidate for the Dorsey A-share low-frequency fundamental quant system. It consolidates MVP 1-11 into a local, auditable, reproducible simulation stack.",
            "",
            "## MVP 1-11 Capability List",
            "",
            "- MVP 1: scoring, portfolio construction, paper broker, local CSV sample data.",
            "- MVP 2: quarterly backtest engine with A-share trading restrictions.",
            "- MVP 3: data quality checks and point-in-time disclosure protection.",
            "- MVP 4: configuration and Markdown reports.",
            "- MVP 5: HTML reports, SVG charts, dry-run notification summary, decision audit log.",
            "- MVP 6: point-in-time data layer, factor audit drilldown, local data source abstraction.",
            "- MVP 7: mock provider adapter contract tests.",
            "- MVP 8: schema versioning and contract diff.",
            "- MVP 9: schema migration metadata and contract diff visualization.",
            "- MVP 10: pre-live safety gate.",
            "- MVP 11: system health check, release checklist, sensitive scan, artifact manifest, release notes draft.",
            "",
            "## Validation Checklist",
            "",
            "- python -m pytest",
            "- python -m dorsey_as system-health --config config/default.yaml",
            "- python -m dorsey_as scan-sensitive-content --config config/default.yaml",
            "- python -m dorsey_as release-checklist --config config/default.yaml",
            "- python -m dorsey_as generate-release-notes --config config/default.yaml",
            "- Run the full local CLI validation sequence documented in README.md.",
            "",
            "## Generated Reports",
            "",
            "- data/output/system_health_summary.md",
            "- data/output/release_checklist.md",
            "- data/output/sensitive_scan_summary.md",
            "- data/output/output_artifact_manifest.md",
            "- data/output/run_report.md and data/output/run_report.html",
            "- data/output/backtest_report.md and data/output/backtest_report.html",
            "",
            "## Safety Boundary",
            "",
            SAFETY_BOUNDARY,
            "This release process does not publish, tag, push, or release automatically.",
            "",
            "## Explicit Non-Goals",
            "",
            "- No real broker connection.",
            "- No real order placement.",
            "- No real network data provider connection.",
            "- No automatic git tag, push, GitHub release, or publication.",
            "",
            "## Current Limitations",
            "",
            "- Local sample data and fixtures only.",
            "- Mock provider is not a market data source.",
            "- Reports are static local artifacts.",
            "- Health and release checks are local guardrails, not operational monitoring.",
            "",
            "## Next Step Suggestion",
            "",
            "Review all generated reports manually, keep the system research-only, and only plan real provider work after contract, schema, migration, point-in-time, and safety gates are expanded in a later explicitly approved milestone.",
        ]
    )
    return ReleaseNotesDraft(version, content)
