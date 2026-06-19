from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from typing import Any

from dorsey_as.config.models import AppConfig
from dorsey_as.safety.models import SafetyGateCheck, SafetyGateResult
from dorsey_as.safety.policy import evaluate_execution_policy


SENSITIVE_KEYS = ["token", "secret", "password", "credential", "webhook_url"]


class PreLiveSafetyGate:
    def __init__(self, config: AppConfig, output_dir: Path | None = None) -> None:
        self.config = config
        self.output_dir = output_dir

    def _row(self, gate: str, check_type: str, status: str, severity: str, blocking: bool, message: str) -> SafetyGateCheck:
        return SafetyGateCheck(gate, check_type, status, severity, blocking, message)

    def _has_sensitive_config_value(self, value: Any) -> bool:
        if isinstance(value, str):
            lower = value.lower()
            return any(f"{key}=" in lower for key in SENSITIVE_KEYS)
        if isinstance(value, list):
            return any(self._has_sensitive_config_value(item) for item in value)
        if hasattr(value, "__dataclass_fields__"):
            return any(self._has_sensitive_config_value(getattr(value, field.name)) for field in fields(value))
        return False

    def _artifact_check(self, check_type: str, filename: str, required: bool) -> SafetyGateCheck:
        if self.output_dir is None or not required:
            return self._row("pre_live_safety", check_type, "pass", "info", False, f"{check_type} policy is configured.")
        path = self.output_dir / filename
        if path.exists():
            return self._row("pre_live_safety", check_type, "pass", "info", False, f"{filename} exists.")
        return self._row("pre_live_safety", check_type, "warn", "warning", False, f"{filename} is not present yet; required before any future escalation.")

    def evaluate(self) -> SafetyGateResult:
        safety = self.config.pre_live_safety
        rows: list[SafetyGateCheck] = []
        rows.extend(evaluate_execution_policy(self.config))
        rows.append(self._row("pre_live_safety", "enabled", "pass" if safety.enabled else "warn", "info" if safety.enabled else "warning", False, f"pre_live_safety.enabled={safety.enabled}"))
        ack_ok = bool(safety.safety_ack_phrase.strip())
        ack_blocking = bool(not ack_ok and safety.block_missing_safety_ack)
        rows.append(
            self._row(
                "safety_acknowledgement",
                "safety_acknowledgement",
                "pass" if ack_ok else "fail",
                "info" if ack_ok else "error",
                ack_blocking,
                "Safety acknowledgement phrase is configured." if ack_ok else "Safety acknowledgement phrase is missing.",
            )
        )
        rows.append(self._row("pre_live_safety", "read_only_first", "pass", "info", False, "Read-only checks are required before any future escalation."))
        rows.append(self._artifact_check("schema_validation", "schema_validation_report.csv", safety.require_schema_validation))
        rows.append(self._artifact_check("provider_contract_validation", "provider_contract_report.csv", safety.require_provider_contract_validation))
        rows.append(self._artifact_check("contract_diff_check", "provider_contract_diff_report.csv", safety.require_contract_diff_check))
        rows.append(self._artifact_check("schema_migration_check", "schema_migration_report.csv", safety.require_schema_migration_check))
        rows.append(self._artifact_check("data_quality_check", "data_quality_report.csv", safety.require_data_quality_check))
        rows.append(self._artifact_check("point_in_time_check", "point_in_time_snapshot.csv", safety.require_point_in_time_check))
        rows.append(self._artifact_check("factor_audit_check", "factor_audit_log.csv", safety.require_factor_audit_check))
        rows.append(self._artifact_check("backtest_before_paper", "backtest_equity_curve.csv", safety.require_backtest_before_paper))
        rows.append(self._artifact_check("paper_before_live", "paper_trades.csv", safety.require_paper_before_live))
        rows.append(self._artifact_check("audit_log", "decision_audit_log.csv", safety.block_missing_audit_log))
        sensitive = self._has_sensitive_config_value(self.config)
        rows.append(
            self._row(
                "pre_live_safety",
                "credential_like_strings",
                "fail" if sensitive else "pass",
                "error" if sensitive else "info",
                sensitive,
                "Credential-like assignment string found in config." if sensitive else "No credential-like assignment strings found in config.",
            )
        )
        return SafetyGateResult(rows)
