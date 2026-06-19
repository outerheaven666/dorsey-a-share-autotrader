from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from dorsey_as.config.models import PointInTimeConfig
from dorsey_as.models import FinancialSnapshot


@dataclass(frozen=True)
class PointInTimeRow:
    as_of_date: str
    symbol: str
    year: int
    report_date: str
    disclosure_date: str
    visible: bool
    reason: str


@dataclass(frozen=True)
class PointInTimeSnapshot:
    as_of_date: str
    visible_financials: dict[str, list[FinancialSnapshot]]
    rows: list[PointInTimeRow]

    @property
    def future_disclosure_count(self) -> int:
        return sum(1 for row in self.rows if row.reason == "future_disclosure")

    @property
    def missing_disclosure_count(self) -> int:
        return sum(1 for row in self.rows if row.reason == "missing_disclosure_date")


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def build_point_in_time_snapshot(
    financials: dict[str, list[FinancialSnapshot]],
    as_of_date: str,
    config: PointInTimeConfig,
    output_dir: Path | None = None,
) -> PointInTimeSnapshot:
    as_of = _parse_date(as_of_date)
    rows: list[PointInTimeRow] = []
    visible: dict[str, list[FinancialSnapshot]] = {}
    for symbol, snapshots in financials.items():
        for snapshot in snapshots:
            disclosure = _parse_date(snapshot.disclosure_date)
            report = _parse_date(snapshot.report_date)
            is_visible = True
            reason = "visible"
            if disclosure is None:
                is_visible = False
                reason = "missing_disclosure_date"
            elif as_of is not None and disclosure > as_of:
                is_visible = False
                reason = "future_disclosure"
            elif report is not None and as_of is not None and (as_of - disclosure).days > config.max_financial_lag_days:
                reason = "stale_but_visible"

            rows.append(
                PointInTimeRow(
                    as_of_date=as_of_date,
                    symbol=symbol,
                    year=snapshot.year,
                    report_date=snapshot.report_date,
                    disclosure_date=snapshot.disclosure_date,
                    visible=is_visible,
                    reason=reason,
                )
            )
            if is_visible:
                visible.setdefault(symbol, []).append(snapshot)

    for kept in visible.values():
        kept.sort(key=lambda item: item.year)
    result = PointInTimeSnapshot(as_of_date=as_of_date, visible_financials=visible, rows=rows)
    if output_dir is not None:
        write_point_in_time_snapshot(result, output_dir)
    return result


def write_point_in_time_snapshot(snapshot: PointInTimeSnapshot, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "point_in_time_snapshot.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["as_of_date", "symbol", "year", "report_date", "disclosure_date", "visible", "reason"])
        writer.writeheader()
        for row in snapshot.rows:
            writer.writerow(row.__dict__)
    return path
