from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from uuid import uuid4


AUDIT_FIELDS = [
    "run_id",
    "timestamp",
    "stage",
    "as_of_date",
    "symbol",
    "decision_type",
    "decision",
    "reason",
    "input_summary",
    "output_summary",
    "severity",
]

SENSITIVE_WORDS = ["webhook", "token", "secret", "credential", "password", "key"]


def new_run_id(prefix: str = "run") -> str:
    return f"{prefix}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"


def sanitize_summary(value: str) -> str:
    sanitized = value
    for word in SENSITIVE_WORDS:
        sanitized = sanitized.replace(word, f"{word[:2]}***")
        sanitized = sanitized.replace(word.upper(), f"{word[:2].upper()}***")
    return sanitized


def append_audit_record(
    output_dir: Path,
    *,
    stage: str,
    as_of_date: str,
    symbol: str,
    decision_type: str,
    decision: str,
    reason: str,
    input_summary: str,
    output_summary: str,
    severity: str,
    run_id: str,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "decision_audit_log.csv"
    write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=AUDIT_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow(
            {
                "run_id": run_id,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "stage": stage,
                "as_of_date": as_of_date,
                "symbol": symbol,
                "decision_type": decision_type,
                "decision": decision,
                "reason": reason,
                "input_summary": sanitize_summary(input_summary),
                "output_summary": sanitize_summary(output_summary),
                "severity": severity,
            }
        )
    return path


def append_many_audit_records(output_dir: Path, rows: list[dict[str, str]], run_id: str) -> Path | None:
    path: Path | None = None
    for row in rows:
        path = append_audit_record(
            output_dir,
            stage=row.get("stage", ""),
            as_of_date=row.get("as_of_date", ""),
            symbol=row.get("symbol", ""),
            decision_type=row.get("decision_type", ""),
            decision=row.get("decision", ""),
            reason=row.get("reason", ""),
            input_summary=row.get("input_summary", ""),
            output_summary=row.get("output_summary", ""),
            severity=row.get("severity", "info"),
            run_id=run_id,
        )
    return path
