from __future__ import annotations

import csv
from pathlib import Path


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def count_rows(path: Path) -> int:
    return len(read_csv_rows(path))


def top_rows(path: Path, limit: int) -> list[dict[str, str]]:
    return read_csv_rows(path)[:limit]


def latest_rows_by_date(path: Path, date_field: str) -> list[dict[str, str]]:
    rows = read_csv_rows(path)
    if not rows:
        return []
    latest = max(row[date_field] for row in rows if row.get(date_field))
    return [row for row in rows if row.get(date_field) == latest]
