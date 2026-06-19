from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SafetyGateCheck:
    gate: str
    check_type: str
    status: str
    severity: str
    blocking: bool
    message: str


@dataclass(frozen=True)
class SafetyGateResult:
    rows: list[SafetyGateCheck]

    @property
    def blocking_issues(self) -> list[SafetyGateCheck]:
        return [row for row in self.rows if row.blocking]

    @property
    def warnings(self) -> list[SafetyGateCheck]:
        return [row for row in self.rows if row.severity == "warning"]

    @property
    def passed_checks(self) -> list[SafetyGateCheck]:
        return [row for row in self.rows if row.status == "pass"]

    @property
    def passed(self) -> bool:
        return not self.blocking_issues


@dataclass(frozen=True)
class SafetyChecklist:
    items: list[SafetyGateCheck]


@dataclass(frozen=True)
class ExecutionPolicy:
    mode: str
    allow_live_trading: bool
    allow_real_broker: bool
    allow_real_orders: bool
    allow_real_network_data: bool
    allow_dry_run_notify: bool
    allow_paper_trading: bool
    allow_backtest: bool
    allow_local_csv: bool
    allow_mock_provider: bool

