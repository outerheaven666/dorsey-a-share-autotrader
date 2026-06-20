from __future__ import annotations

import csv
from pathlib import Path

from dorsey_as.config.models import AppConfig
from dorsey_as.safety.models import SafetyGateResult


SAFETY_BOUNDARY = (
    "Current system does not provide investment advice, does not guarantee returns, does not support real trading, "
    "has no real broker connection, has no real network data source connection, and is only for personal research, "
    "system development, paper/backtest simulation, and dry-run notification. Mock provider is only for contract tests. "
    "Real provider template is disabled-by-default and non-executable. Schema migration metadata is only for pre-integration checks. "
    "Pre-live safety gate blocks live trading, real broker, real order, and real network data by default. "
    "System health and release checklist only generate local reports and never commit, tag, push, or publish automatically."
)


def write_pre_live_safety_report(result: SafetyGateResult, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "pre_live_safety_report.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["gate", "check_type", "status", "severity", "blocking", "message"])
        writer.writeheader()
        for row in result.rows:
            writer.writerow(row.__dict__)
    return path


def write_pre_live_safety_summary(result: SafetyGateResult, config: AppConfig, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "pre_live_safety_summary.md"
    lines = [
        "# Pre-live safety gate summary",
        "",
        f"- current mode: {config.execution_policy.mode}",
        f"- live trading allowed? {config.execution_policy.allow_live_trading}",
        f"- real broker allowed? {config.execution_policy.allow_real_broker}",
        f"- real orders allowed? {config.execution_policy.allow_real_orders}",
        f"- real network data allowed? {config.execution_policy.allow_real_network_data}",
        f"- dry-run notify allowed? {config.execution_policy.allow_dry_run_notify}",
        f"- paper trading allowed? {config.execution_policy.allow_paper_trading}",
        f"- backtest allowed? {config.execution_policy.allow_backtest}",
        f"- blocking issues: {len(result.blocking_issues)}",
        f"- warnings: {len(result.warnings)}",
        f"- passed checks: {len(result.passed_checks)}",
        f"- safety acknowledgement status: {'configured' if config.pre_live_safety.safety_ack_phrase else 'missing'}",
        "",
        "## Current Safety Boundary",
        "",
        SAFETY_BOUNDARY,
        "",
        "## Current Limitations",
        "",
        "- Safety gate is a local dry-run guard only.",
        "- No real broker or real network provider exists.",
        "- Live trading remains blocked.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_safety_explanation(config: AppConfig, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "safety_explanation.md"
    lines = [
        "# Safety Explanation",
        "",
        "The current system remains research-only because live trading, real broker access, real orders, and real network data are explicitly disabled by configuration and blocked by the pre-live safety gate.",
        f"Release candidate version: {config.system_health.release_version}. System health, release checklist, and sensitive scan are enabled as local-only pre-release guardrails.",
        "",
        "## Allowed",
        "",
        f"- local CSV: {config.execution_policy.allow_local_csv}",
        f"- mock provider contract tests: {config.execution_policy.allow_mock_provider}",
        f"- paper trading simulation: {config.execution_policy.allow_paper_trading}",
        f"- backtest simulation: {config.execution_policy.allow_backtest}",
        f"- dry-run notification: {config.execution_policy.allow_dry_run_notify}",
        "",
        "## Release Candidate Guardrails",
        "",
        f"- system health enabled: {config.system_health.enabled}",
        f"- release checklist enabled: {config.release_checklist.enabled}",
        f"- sensitive scan enabled: {config.sensitive_scan.enabled}",
        f"- release_version: {config.system_health.release_version}",
        "- manual steps still required: run validation commands, inspect git status, create PR, merge PR, pull main, final validation, tag, push tag",
        "",
        "## Forbidden",
        "",
        f"- live trading: {config.execution_policy.allow_live_trading}",
        f"- real broker: {config.execution_policy.allow_real_broker}",
        f"- real orders: {config.execution_policy.allow_real_orders}",
        f"- real network data: {config.execution_policy.allow_real_network_data}",
        "",
        "Live trading is forbidden because this project has no live broker adapter, no live account reconciliation, no credential handling, and no real order path. Real broker and real network data are forbidden for the same reason: this phase is local-only and research-only.",
        "",
        "## Future Pre-Checks",
        "",
        "- validate-provider-contract",
        "- diff-provider-contract",
        "- validate-schema-migration",
        "- generate-contract-diff-html",
        "- validate-schema",
        "- check-data-quality",
        "- point-in-time checks",
        "- factor audit checks",
        "- backtest before paper",
        "- paper before any future live review",
        "",
        "## Manual Confirmation Phrase",
        "",
        config.pre_live_safety.safety_ack_phrase,
        "",
        "## Safety Statement",
        "",
        SAFETY_BOUNDARY,
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_simulated_live_request_report(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "simulated_live_request_report.csv"
    rows = [
        {"request_type": "live_trading", "requested_mode": "live", "allowed": False, "blocked": True, "reason": "live trading is disabled", "safety_gate": "pre_live_safety"},
        {"request_type": "real_broker", "requested_mode": "real_broker", "allowed": False, "blocked": True, "reason": "real broker connection is disabled", "safety_gate": "pre_live_safety"},
        {"request_type": "real_order", "requested_mode": "real_order", "allowed": False, "blocked": True, "reason": "real order placement is disabled", "safety_gate": "pre_live_safety"},
        {"request_type": "real_network_data", "requested_mode": "real_network_data", "allowed": False, "blocked": True, "reason": "real network data is disabled", "safety_gate": "pre_live_safety"},
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["request_type", "requested_mode", "allowed", "blocked", "reason", "safety_gate"])
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_simulated_live_request_summary(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "simulated_live_request_summary.md"
    lines = [
        "# Simulated Live Request Summary",
        "",
        "- live request was simulated only",
        "- no real order was created",
        "- no broker was connected",
        "- no network request was made",
        "- request was blocked by safety gate",
        "",
        "## Blocking Reasons",
        "",
        "- live trading is disabled",
        "- real broker connection is disabled",
        "- real order placement is disabled",
        "- real network data is disabled",
        "",
        "## Current Safety Boundary",
        "",
        SAFETY_BOUNDARY,
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
