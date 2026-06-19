from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from dorsey_as.adapters.mapping import MappingPreviewRow, map_dataset
from dorsey_as.adapters.registry import get_provider
from dorsey_as.adapters.report import write_adapter_mapped_preview
from dorsey_as.config.models import AppConfig
from dorsey_as.data_source.schema import SCHEMAS
from dorsey_as.point_in_time import build_point_in_time_snapshot
from dorsey_as.models import FinancialSnapshot


@dataclass(frozen=True)
class ProviderContractCheck:
    provider: str
    dataset: str
    check_type: str
    status: str
    severity: str
    message: str


@dataclass(frozen=True)
class ProviderContractReport:
    provider: str
    contract_version: str
    rows: list[ProviderContractCheck]
    mapped_preview: list[MappingPreviewRow]

    @property
    def passed(self) -> bool:
        return not any(row.status == "fail" and row.severity == "error" for row in self.rows)


DATASET_METHODS = {
    "stock_basic": "get_stock_basic",
    "financial_snapshot": "get_financial_snapshot",
    "market_snapshot": "get_market_snapshot",
    "historical_market_snapshot": "get_historical_market_snapshot",
    "trading_calendar": "get_trading_calendar",
}


def _check(provider: str, dataset: str, check_type: str, status: str, severity: str, message: str) -> ProviderContractCheck:
    return ProviderContractCheck(provider, dataset, check_type, status, severity, message)


def _validate_mapped_dataset(provider: str, dataset: str, rows: list[dict[str, str]]) -> list[ProviderContractCheck]:
    checks: list[ProviderContractCheck] = []
    schema = SCHEMAS[dataset]
    headers = set().union(*(row.keys() for row in rows)) if rows else set()
    required = set(schema["required"])
    missing = sorted(required - headers)
    if missing:
        checks.append(_check(provider, dataset, "schema_required_columns", "fail", "error", f"missing required columns: {', '.join(missing)}"))
    else:
        checks.append(_check(provider, dataset, "schema_required_columns", "pass", "info", "required columns present after mapping"))

    numeric_failures: list[str] = []
    for index, row in enumerate(rows, start=2):
        for field in schema["numeric"]:
            if row.get(field, "") != "":
                try:
                    float(row[field])
                except ValueError:
                    numeric_failures.append(f"row {index} field {field}")
    if numeric_failures:
        checks.append(_check(provider, dataset, "schema_numeric_fields", "fail", "error", "; ".join(numeric_failures[:5])))
    else:
        checks.append(_check(provider, dataset, "schema_numeric_fields", "pass", "info", "numeric fields parse after mapping"))

    seen: set[tuple[str, ...]] = set()
    duplicates: list[str] = []
    for row in rows:
        if all(field in row for field in schema["key"]):
            key = tuple(row[field] for field in schema["key"])
            if key in seen:
                duplicates.append("|".join(key))
            seen.add(key)
    if duplicates:
        checks.append(_check(provider, dataset, "schema_duplicate_keys", "fail", "error", f"duplicate keys: {', '.join(duplicates[:5])}"))
    else:
        checks.append(_check(provider, dataset, "schema_duplicate_keys", "pass", "info", "no duplicate keys after mapping"))
    return checks


def _financial_snapshots_from_rows(rows: list[dict[str, str]]) -> dict[str, list[FinancialSnapshot]]:
    grouped: dict[str, list[FinancialSnapshot]] = {}
    for row in rows:
        if not row.get("symbol") or not row.get("year"):
            continue
        snapshot = FinancialSnapshot(
            symbol=row["symbol"],
            year=int(float(row["year"])),
            revenue=float(row.get("revenue") or 0),
            net_profit=float(row.get("net_profit") or 0),
            operating_cash_flow=float(row.get("operating_cash_flow") or 0),
            free_cash_flow=float(row.get("free_cash_flow") or 0),
            total_assets=float(row.get("total_assets") or 0),
            total_liabilities=float(row.get("total_liabilities") or 0),
            equity=float(row.get("equity") or 0),
            accounts_receivable=float(row.get("accounts_receivable") or 0),
            inventory=float(row.get("inventory") or 0),
            goodwill=float(row.get("goodwill") or 0),
            non_recurring_profit=float(row.get("non_recurring_profit") or 0),
            roe=float(row.get("roe") or 0),
            roic=float(row.get("roic") or 0),
            gross_margin=float(row.get("gross_margin") or 0),
            net_margin=float(row.get("net_margin") or 0),
            rd_expense=float(row.get("rd_expense") or 0),
            selling_expense=float(row.get("selling_expense") or 0),
            report_date=row.get("report_date", ""),
            disclosure_date=row.get("disclosure_date", ""),
        )
        grouped.setdefault(snapshot.symbol, []).append(snapshot)
    return grouped


def _point_in_time_compatibility(config: AppConfig, rows: list[dict[str, str]], output_dir: Path) -> list[ProviderContractCheck]:
    provider = config.adapter_contract.provider
    financials = _financial_snapshots_from_rows(rows)
    if not financials:
        return [_check(provider, "financial_snapshot", "point_in_time_compatibility", "fail", "error", "no mapped financial rows available")]
    snapshot = build_point_in_time_snapshot(financials, config.point_in_time.as_of_date, config.point_in_time, output_dir)
    if any(not row.disclosure_date for row in snapshot.rows):
        return [_check(provider, "financial_snapshot", "point_in_time_compatibility", "fail", "error", "disclosure_date is required for point-in-time checks")]
    return [_check(provider, "financial_snapshot", "point_in_time_compatibility", "pass", "info", f"visible_rows={sum(1 for row in snapshot.rows if row.visible)}")]


def validate_provider_contract(config: AppConfig, output_dir: Path) -> ProviderContractReport:
    provider = get_provider(config.adapter_contract.provider, config.adapter_contract)
    rows: list[ProviderContractCheck] = []
    preview: list[MappingPreviewRow] = []
    mapped_by_dataset: dict[str, list[dict[str, str]]] = {}

    rows.append(_check(provider.name, "", "network_access", "pass", "info", "network access disabled"))
    rows.append(_check(provider.name, "", "provider_mode", "pass", "info", "mock_only provider contract mode"))

    for dataset, method_name in DATASET_METHODS.items():
        raw_rows = getattr(provider, method_name)()
        rows.append(_check(provider.name, dataset, "provider_method", "pass" if raw_rows else "fail", "info" if raw_rows else "error", f"rows={len(raw_rows)}"))
        mapped, dataset_preview = map_dataset(dataset, raw_rows, provider.name)
        preview.extend(dataset_preview)
        mapped_by_dataset[dataset] = mapped
        rows.extend(_validate_mapped_dataset(provider.name, dataset, mapped))
        for preview_row in dataset_preview:
            if preview_row.status == "warning":
                rows.append(_check(provider.name, dataset, "extra_source_field", "warn", "warning", f"{preview_row.source_field}: {preview_row.message}"))

    rows.extend(_point_in_time_compatibility(config, mapped_by_dataset.get("financial_snapshot", []), output_dir))

    report = ProviderContractReport(provider.name, config.adapter_contract.contract_version, rows, preview)
    write_provider_contract_report(report, output_dir)
    write_provider_contract_summary(report, output_dir)
    write_adapter_mapped_preview(preview, output_dir)
    return report


def write_provider_contract_report(report: ProviderContractReport, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "provider_contract_report.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["provider", "dataset", "check_type", "status", "severity", "message"])
        writer.writeheader()
        for row in report.rows:
            writer.writerow(row.__dict__)
    return path


def write_provider_contract_summary(report: ProviderContractReport, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    failures = [row for row in report.rows if row.status == "fail" and row.severity == "error"]
    warnings = [row for row in report.rows if row.severity == "warning"]
    passed = [row for row in report.rows if row.status == "pass"]
    datasets = sorted({row.dataset for row in report.rows if row.dataset})
    lines = [
        "# Provider Contract Summary",
        "",
        f"- Provider: {report.provider}",
        f"- Contract version: {report.contract_version}",
        f"- Datasets checked: {', '.join(datasets)}",
        f"- Passed checks: {len(passed)}",
        f"- Warnings: {len(warnings)}",
        f"- Blocking failures: {len(failures)}",
        "",
        "## Safety Boundary",
        "",
        "Mock provider only. Network access is disabled. Real external data providers are disabled. No real broker connection or real trading path exists.",
        "",
        "## Current Limitations",
        "",
        "- Fixture data is fake sample data.",
        "- This report validates adapter contracts only.",
        "- Mock provider is not an actual market data source.",
    ]
    path = output_dir / "provider_contract_summary.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
