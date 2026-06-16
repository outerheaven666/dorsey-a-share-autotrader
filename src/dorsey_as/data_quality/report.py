from __future__ import annotations

import csv
from pathlib import Path

from dorsey_as.data_quality.models import DataQualityIssue, DataQualityReport


FIELDNAMES = ["as_of_date", "check_name", "severity", "blocking", "symbol", "field", "message"]


def _rows(report: DataQualityReport) -> list[dict[str, str]]:
    issues = report.issues or [
        DataQualityIssue(
            check_name="DataQualityCheck",
            severity="info",
            blocking=False,
            as_of_date=report.as_of_date,
            message="data quality checks passed",
        )
    ]
    return [
        {
            "as_of_date": issue.as_of_date or report.as_of_date,
            "check_name": issue.check_name,
            "severity": issue.severity,
            "blocking": str(issue.blocking),
            "symbol": issue.symbol,
            "field": issue.field,
            "message": issue.message,
        }
        for issue in issues
    ]


def write_data_quality_report(report: DataQualityReport, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(_rows(report))
    return path
