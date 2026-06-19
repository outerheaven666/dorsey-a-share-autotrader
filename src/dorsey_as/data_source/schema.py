from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from dorsey_as.config.models import SchemaValidationConfig
from dorsey_as.data_source.base import DataSource
from dorsey_as.data_source.manifest import write_data_source_manifest


@dataclass(frozen=True)
class SchemaCheckRow:
    file: str
    check_type: str
    status: str
    severity: str
    message: str


@dataclass(frozen=True)
class SchemaValidationReport:
    rows: list[SchemaCheckRow]

    @property
    def passed(self) -> bool:
        return not any(row.status == "fail" and row.severity == "error" for row in self.rows)


SCHEMAS = {
    "stock_basic": {
        "required": ["symbol", "name", "industry", "is_st", "is_suspended"],
        "numeric": [],
        "key": ["symbol"],
    },
    "financial_snapshot": {
        "required": [
            "symbol",
            "year",
            "revenue",
            "net_profit",
            "operating_cash_flow",
            "free_cash_flow",
            "total_assets",
            "total_liabilities",
            "equity",
            "accounts_receivable",
            "inventory",
            "goodwill",
            "non_recurring_profit",
            "roe",
            "roic",
            "gross_margin",
            "net_margin",
            "report_date",
            "disclosure_date",
        ],
        "numeric": [
            "year",
            "revenue",
            "net_profit",
            "operating_cash_flow",
            "free_cash_flow",
            "total_assets",
            "total_liabilities",
            "equity",
            "accounts_receivable",
            "inventory",
            "goodwill",
            "non_recurring_profit",
            "roe",
            "roic",
            "gross_margin",
            "net_margin",
            "rd_expense",
            "selling_expense",
        ],
        "key": ["symbol", "year"],
    },
    "market_snapshot": {
        "required": ["symbol", "trade_date", "close_price", "market_cap", "pe", "pb", "ev_to_fcf", "fcf_yield", "dividend_yield"],
        "numeric": ["close_price", "market_cap", "pe", "pb", "ev_to_fcf", "fcf_yield", "dividend_yield"],
        "key": ["symbol", "trade_date"],
    },
    "historical_market_snapshot": {
        "required": ["symbol", "trade_date", "close_price", "is_suspended", "is_limit_up", "is_limit_down", "volume", "amount"],
        "numeric": ["close_price", "volume", "amount"],
        "key": ["symbol", "trade_date"],
    },
    "trading_calendar": {
        "required": ["trade_date", "is_rebalance_date"],
        "numeric": [],
        "key": ["trade_date"],
    },
}


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), list(reader)


def _row(file: str, check_type: str, status: str, severity: str, message: str) -> SchemaCheckRow:
    return SchemaCheckRow(file, check_type, status, severity, message)


def validate_csv_schema(data_source: DataSource, config: SchemaValidationConfig, output_dir: Path | None = None) -> SchemaValidationReport:
    rows: list[SchemaCheckRow] = []
    for dataset, path in data_source.files().items():
        schema = SCHEMAS[dataset]
        if not path.exists():
            rows.append(_row(str(path), "file_exists", "fail", "error", "file is missing"))
            continue
        headers, records = _read_csv(path)
        required = set(schema["required"])
        missing = sorted(required - set(headers))
        if missing:
            rows.append(
                _row(
                    str(path),
                    "required_columns",
                    "fail" if config.block_on_missing_required_columns else "warn",
                    "error" if config.block_on_missing_required_columns else "warning",
                    f"missing required columns: {', '.join(missing)}",
                )
            )
        else:
            rows.append(_row(str(path), "required_columns", "pass", "info", "required columns present"))

        extra = sorted(set(headers) - required - set(schema["numeric"]))
        if extra and config.warn_on_extra_columns:
            rows.append(_row(str(path), "extra_columns", "warn", "warning", f"extra columns: {', '.join(extra)}"))

        numeric_failures: list[str] = []
        for index, record in enumerate(records, start=2):
            for field in schema["numeric"]:
                if field in record and record[field] not in ("", None):
                    try:
                        float(record[field])
                    except ValueError:
                        numeric_failures.append(f"row {index} field {field}")
        if numeric_failures:
            rows.append(
                _row(
                    str(path),
                    "numeric_fields",
                    "fail" if config.block_on_invalid_numeric_fields else "warn",
                    "error" if config.block_on_invalid_numeric_fields else "warning",
                    "; ".join(numeric_failures[:5]),
                )
            )
        else:
            rows.append(_row(str(path), "numeric_fields", "pass", "info", "numeric fields parse"))

        seen: set[tuple[str, ...]] = set()
        duplicates: list[str] = []
        key_fields = schema["key"]
        for record in records:
            if all(field in record for field in key_fields):
                key = tuple(record[field] for field in key_fields)
                if key in seen:
                    duplicates.append("|".join(key))
                seen.add(key)
        if duplicates:
            rows.append(
                _row(
                    str(path),
                    "duplicate_keys",
                    "fail" if config.block_on_duplicate_keys else "warn",
                    "error" if config.block_on_duplicate_keys else "warning",
                    f"duplicate keys: {', '.join(duplicates[:5])}",
                )
            )
        else:
            rows.append(_row(str(path), "duplicate_keys", "pass", "info", "no duplicate keys"))

    report = SchemaValidationReport(rows)
    if output_dir is not None:
        write_schema_validation_report(report, output_dir)
        write_data_source_manifest(data_source, output_dir)
    return report


def write_schema_validation_report(report: SchemaValidationReport, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "schema_validation_report.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["file", "check_type", "status", "severity", "message"])
        writer.writeheader()
        for row in report.rows:
            writer.writerow(row.__dict__)
    return path
