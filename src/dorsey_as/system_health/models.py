from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HealthCheckItem:
    check: str
    category: str
    status: str
    severity: str
    blocking: bool
    message: str


@dataclass
class SystemHealthResult:
    items: list[HealthCheckItem]

    @property
    def blocking_issues(self) -> list[HealthCheckItem]:
        return [item for item in self.items if item.blocking]

    @property
    def warnings(self) -> list[HealthCheckItem]:
        return [item for item in self.items if item.severity == "warning"]

    @property
    def passed(self) -> bool:
        return not self.blocking_issues


@dataclass
class SensitiveScanFinding:
    path: str
    line: int
    pattern: str
    severity: str
    blocking: bool
    context: str


@dataclass
class SensitiveScanResult:
    findings: list[SensitiveScanFinding]

    @property
    def blocking_findings(self) -> list[SensitiveScanFinding]:
        return [finding for finding in self.findings if finding.blocking]

    @property
    def warnings(self) -> list[SensitiveScanFinding]:
        return [finding for finding in self.findings if finding.severity == "warning"]

    @property
    def passed(self) -> bool:
        return not self.blocking_findings


@dataclass
class ReleaseChecklistItem:
    item: str
    required: bool
    status: str
    blocking: bool
    evidence: str
    message: str


@dataclass
class ReleaseNotesDraft:
    release_version: str
    content: str
