from __future__ import annotations

from pathlib import Path

from dorsey_as.adapters.registry import get_provider
from dorsey_as.config.models import AppConfig
from dorsey_as.system_health.models import HealthCheckItem, SystemHealthResult
from dorsey_as.system_health.scanner import scan_sensitive_content


EXPECTED_ARTIFACTS = [
    "scores.csv",
    "target_portfolio.csv",
    "paper_trades.csv",
    "backtest_equity_curve.csv",
    "backtest_trades.csv",
    "backtest_holdings.csv",
    "backtest_metrics.csv",
    "data_quality_report.csv",
    "schema_validation_report.csv",
    "provider_contract_report.csv",
    "provider_contract_diff_report.csv",
    "provider_contract_diff_summary.md",
    "provider_contract_diff.html",
    "provider_contract_diff_visual_summary.md",
    "schema_migration_report.csv",
    "schema_migration_summary.md",
    "pre_live_safety_report.csv",
    "pre_live_safety_summary.md",
    "safety_explanation.md",
    "simulated_live_request_report.csv",
    "simulated_live_request_summary.md",
    "run_report.md",
    "run_report.html",
    "backtest_report.md",
    "backtest_report.html",
    "notify_payload.json",
    "notify_summary.md",
    "decision_audit_log.csv",
    "system_health_report.csv",
    "system_health_summary.md",
    "sensitive_scan_report.csv",
    "sensitive_scan_summary.md",
    "output_artifact_manifest.csv",
    "output_artifact_manifest.md",
    "release_checklist.csv",
    "release_checklist.md",
    "release_notes_v0.11.0.md",
]


GENERATED_BY = {
    "scores.csv": "run-score",
    "target_portfolio.csv": "build-portfolio",
    "paper_trades.csv": "paper-rebalance",
    "backtest_equity_curve.csv": "run-backtest",
    "backtest_trades.csv": "run-backtest",
    "backtest_holdings.csv": "run-backtest",
    "backtest_metrics.csv": "run-backtest",
    "data_quality_report.csv": "check-data-quality",
    "schema_validation_report.csv": "validate-schema",
    "provider_contract_report.csv": "validate-provider-contract",
    "provider_contract_diff_report.csv": "diff-provider-contract",
    "provider_contract_diff_summary.md": "diff-provider-contract",
    "provider_contract_diff.html": "generate-contract-diff-html",
    "provider_contract_diff_visual_summary.md": "generate-contract-diff-html",
    "schema_migration_report.csv": "validate-schema-migration",
    "schema_migration_summary.md": "validate-schema-migration",
    "pre_live_safety_report.csv": "check-pre-live-safety",
    "pre_live_safety_summary.md": "check-pre-live-safety",
    "safety_explanation.md": "explain-safety",
    "simulated_live_request_report.csv": "simulate-live-request",
    "simulated_live_request_summary.md": "simulate-live-request",
    "run_report.md": "generate-report",
    "run_report.html": "generate-report",
    "backtest_report.md": "generate-report",
    "backtest_report.html": "generate-report",
    "notify_payload.json": "notify-summary",
    "notify_summary.md": "notify-summary",
    "decision_audit_log.csv": "all audited CLI commands",
    "system_health_report.csv": "system-health",
    "system_health_summary.md": "system-health",
    "sensitive_scan_report.csv": "scan-sensitive-content",
    "sensitive_scan_summary.md": "scan-sensitive-content",
    "output_artifact_manifest.csv": "system-health or release-checklist",
    "output_artifact_manifest.md": "system-health or release-checklist",
    "release_checklist.csv": "release-checklist",
    "release_checklist.md": "release-checklist",
    "release_notes_v0.11.0.md": "generate-release-notes",
}


def _item(check: str, category: str, status: str, severity: str, blocking: bool, message: str) -> HealthCheckItem:
    return HealthCheckItem(check, category, status, severity, blocking, message)


def data_output_is_ignored(root: Path) -> bool:
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return False
    lines = [line.strip().replace("\\", "/") for line in gitignore.read_text(encoding="utf-8").splitlines()]
    return "data/output/" in lines or "data/output" in lines


def build_artifact_manifest(output_dir: Path, root: Path | None = None) -> list[dict[str, str | bool]]:
    project_root = root or Path.cwd()
    ignored = data_output_is_ignored(project_root)
    rows: list[dict[str, str | bool]] = []
    for artifact in EXPECTED_ARTIFACTS:
        path = output_dir / artifact
        rows.append(
            {
                "artifact": artifact,
                "expected": True,
                "exists": path.exists(),
                "generated_by": GENERATED_BY.get(artifact, "existing CLI"),
                "tracked_by_git": False if ignored else "unknown",
                "note": "under ignored data/output" if ignored else "verify git tracking manually",
            }
        )
    return rows


def evaluate_system_health(config: AppConfig, output_dir: Path, root: Path | None = None) -> SystemHealthResult:
    project_root = root or Path.cwd()
    rows: list[HealthCheckItem] = []
    rows.append(_item("config/default.yaml", "project_files", "pass" if (project_root / "config/default.yaml").exists() else "fail", "info", not (project_root / "config/default.yaml").exists(), "Default config file exists."))
    rows.append(_item("README.md", "project_files", "pass" if (project_root / "README.md").exists() else "fail", "info", not (project_root / "README.md").exists(), "README exists."))
    ignored = data_output_is_ignored(project_root)
    rows.append(_item("data/output gitignore", "artifact_policy", "pass" if ignored else "fail", "info" if ignored else "error", not ignored, "data/output is ignored by git." if ignored else "data/output is not ignored by git."))
    policy = config.execution_policy
    safety = config.pre_live_safety
    rows.extend(
        [
            _item("allow_live_trading=false", "safety_config", "pass" if not policy.allow_live_trading else "fail", "info" if not policy.allow_live_trading else "error", policy.allow_live_trading, "Live trading is disabled."),
            _item("allow_real_broker=false", "safety_config", "pass" if not policy.allow_real_broker else "fail", "info" if not policy.allow_real_broker else "error", policy.allow_real_broker, "Real broker connections are disabled."),
            _item("allow_real_orders=false", "safety_config", "pass" if not policy.allow_real_orders else "fail", "info" if not policy.allow_real_orders else "error", policy.allow_real_orders, "Real orders are disabled."),
            _item("allow_real_network_data=false", "safety_config", "pass" if not policy.allow_real_network_data else "fail", "info" if not policy.allow_real_network_data else "error", policy.allow_real_network_data, "Real network data is disabled."),
            _item("block_live_trading=true", "safety_config", "pass" if safety.block_live_trading else "fail", "info" if safety.block_live_trading else "error", not safety.block_live_trading, "Pre-live gate blocks live trading."),
            _item("block_real_broker=true", "safety_config", "pass" if safety.block_real_broker else "fail", "info" if safety.block_real_broker else "error", not safety.block_real_broker, "Pre-live gate blocks real broker access."),
            _item("block_real_network_provider=true", "safety_config", "pass" if safety.block_real_network_provider else "fail", "info" if safety.block_real_network_provider else "error", not safety.block_real_network_provider, "Pre-live gate blocks real network data."),
        ]
    )
    adapter_ok = config.adapter_contract.mode == "mock_only" and not config.adapter_contract.allow_network and not config.adapter_contract.allow_real_provider
    rows.append(_item("mock provider only", "provider_registry", "pass" if adapter_ok else "fail", "info" if adapter_ok else "error", not adapter_ok, "Adapter contract remains mock-only."))
    try:
        get_provider("real_provider_template", config.adapter_contract)
        template_registered = True
    except Exception:
        template_registered = False
    rows.append(_item("disabled provider template", "provider_registry", "pass" if not template_registered else "fail", "info" if not template_registered else "error", template_registered, "Disabled real provider template is not registered."))
    scan = scan_sensitive_content(config, project_root)
    rows.append(_item("sensitive scan", "sensitive_scan", "pass" if scan.passed else "fail", "info" if scan.passed else "error", not scan.passed, f"blocking findings={len(scan.blocking_findings)}, warnings={len(scan.warnings)}"))
    for artifact in build_artifact_manifest(output_dir, project_root):
        exists = bool(artifact["exists"])
        rows.append(_item(str(artifact["artifact"]), "artifact_manifest", "pass" if exists else "warn", "info" if exists else "warning", False, f"generated_by={artifact['generated_by']}; exists={exists}"))
    rows.append(_item("release notes safety boundary", "release_notes", "pass", "info", False, "Release notes draft must include the local-only safety boundary."))
    return SystemHealthResult(rows)
