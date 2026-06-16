from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DataQualityIssue:
    check_name: str
    severity: str
    message: str
    blocking: bool = False
    symbol: str = ""
    field: str = ""
    as_of_date: str = ""


@dataclass(frozen=True)
class DataQualityReport:
    as_of_date: str
    issues: list[DataQualityIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(issue.blocking for issue in self.issues)

    @property
    def blocking_issues(self) -> list[DataQualityIssue]:
        return [issue for issue in self.issues if issue.blocking]

    @property
    def warnings(self) -> list[DataQualityIssue]:
        return [issue for issue in self.issues if issue.severity == "warning"]


class DataQualityError(RuntimeError):
    def __init__(self, report: DataQualityReport) -> None:
        self.report = report
        super().__init__("data quality check failed")
