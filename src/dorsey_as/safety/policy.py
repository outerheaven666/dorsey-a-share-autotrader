from __future__ import annotations

from dorsey_as.config.models import AppConfig
from dorsey_as.safety.models import ExecutionPolicy, SafetyGateCheck


def execution_policy_from_config(config: AppConfig) -> ExecutionPolicy:
    policy = config.execution_policy
    return ExecutionPolicy(
        mode=policy.mode,
        allow_live_trading=policy.allow_live_trading,
        allow_real_broker=policy.allow_real_broker,
        allow_real_orders=policy.allow_real_orders,
        allow_real_network_data=policy.allow_real_network_data,
        allow_dry_run_notify=policy.allow_dry_run_notify,
        allow_paper_trading=policy.allow_paper_trading,
        allow_backtest=policy.allow_backtest,
        allow_local_csv=policy.allow_local_csv,
        allow_mock_provider=policy.allow_mock_provider,
    )


def _check(check_type: str, status: str, severity: str, blocking: bool, message: str) -> SafetyGateCheck:
    return SafetyGateCheck("execution_policy", check_type, status, severity, blocking, message)


def evaluate_execution_policy(config: AppConfig) -> list[SafetyGateCheck]:
    safety = config.pre_live_safety
    policy = config.execution_policy
    rows: list[SafetyGateCheck] = []

    if policy.mode in safety.forbidden_modes or policy.mode == "live":
        rows.append(_check("mode", "fail", "error", True, f"execution_policy.mode={policy.mode} is forbidden."))
    elif policy.mode in safety.allowed_modes:
        rows.append(_check("mode", "pass", "info", False, f"execution_policy.mode={policy.mode} is allowed for research-only operation."))
    else:
        rows.append(_check("mode", "warn", "warning", False, f"execution_policy.mode={policy.mode} is not recognized."))

    if policy.allow_live_trading or safety.block_live_trading:
        rows.append(
            _check(
                "live_trading",
                "fail" if policy.allow_live_trading else "pass",
                "error" if policy.allow_live_trading else "info",
                bool(policy.allow_live_trading and safety.block_live_trading),
                "Live trading is blocked by default.",
            )
        )
    if policy.allow_real_broker or safety.block_real_broker:
        rows.append(
            _check(
                "real_broker",
                "fail" if policy.allow_real_broker else "pass",
                "error" if policy.allow_real_broker else "info",
                bool(policy.allow_real_broker and safety.block_real_broker),
                "Real broker connections are blocked by default.",
            )
        )
    rows.append(
        _check(
            "real_orders",
            "fail" if policy.allow_real_orders else "pass",
            "error" if policy.allow_real_orders else "info",
            bool(policy.allow_real_orders),
            "Real order placement is blocked by default.",
        )
    )
    rows.append(
        _check(
            "real_network_data",
            "fail" if policy.allow_real_network_data else "pass",
            "error" if policy.allow_real_network_data else "info",
            bool(policy.allow_real_network_data and safety.block_real_network_provider),
            "Real network data providers are blocked by default.",
        )
    )
    rows.append(_check("dry_run_notify", "pass" if policy.allow_dry_run_notify else "warn", "info" if policy.allow_dry_run_notify else "warning", False, "Dry-run notifications are allowed."))
    rows.append(_check("paper_trading", "pass" if policy.allow_paper_trading else "warn", "info" if policy.allow_paper_trading else "warning", False, "Paper trading is allowed only as simulation."))
    rows.append(_check("backtest", "pass" if policy.allow_backtest else "warn", "info" if policy.allow_backtest else "warning", False, "Backtest simulation is allowed."))
    rows.append(_check("local_csv", "pass" if policy.allow_local_csv else "fail", "info" if policy.allow_local_csv else "error", not policy.allow_local_csv, "Local CSV data is the default allowed data path."))
    rows.append(_check("mock_provider", "pass" if policy.allow_mock_provider else "warn", "info" if policy.allow_mock_provider else "warning", False, "Mock provider is allowed only for contract tests."))
    return rows

