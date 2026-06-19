from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from dorsey_as.data_source.schema import SCHEMAS


@dataclass(frozen=True)
class MappingPreviewRow:
    provider: str
    dataset: str
    source_field: str
    target_field: str
    status: str
    message: str


FIELD_MAPPINGS: dict[str, dict[str, list[str]]] = {
    "stock_basic": {
        "symbol": ["symbol", "ts_code", "code"],
        "name": ["name", "stock_name"],
        "industry": ["industry", "industry_name"],
        "is_st": ["is_st", "st_flag"],
        "is_suspended": ["is_suspended", "suspend_flag"],
    },
    "financial_snapshot": {
        "symbol": ["symbol", "ts_code", "code"],
        "year": ["year", "report_year"],
        "revenue": ["revenue", "oper_rev"],
        "net_profit": ["net_profit", "n_income"],
        "operating_cash_flow": ["operating_cash_flow", "n_cashflow_act"],
        "free_cash_flow": ["free_cash_flow", "free_cashflow"],
        "total_assets": ["total_assets"],
        "total_liabilities": ["total_liabilities", "total_liab"],
        "equity": ["equity", "total_hldr_eqy_exc_min_int"],
        "accounts_receivable": ["accounts_receivable", "accounts_receiv"],
        "inventory": ["inventory", "inventories"],
        "goodwill": ["goodwill"],
        "non_recurring_profit": ["non_recurring_profit"],
        "roe": ["roe"],
        "roic": ["roic"],
        "gross_margin": ["gross_margin"],
        "net_margin": ["net_margin"],
        "rd_expense": ["rd_expense", "rd_exp"],
        "selling_expense": ["selling_expense"],
        "report_date": ["report_date", "end_date"],
        "disclosure_date": ["disclosure_date", "ann_date"],
    },
    "market_snapshot": {
        "symbol": ["symbol", "ts_code", "code"],
        "trade_date": ["trade_date", "date"],
        "close_price": ["close_price", "close"],
        "market_cap": ["market_cap", "total_mv"],
        "pe": ["pe", "pe_ttm"],
        "pb": ["pb"],
        "ev_to_fcf": ["ev_to_fcf"],
        "fcf_yield": ["fcf_yield"],
        "dividend_yield": ["dividend_yield"],
    },
    "historical_market_snapshot": {
        "symbol": ["symbol", "ts_code", "code"],
        "trade_date": ["trade_date", "date"],
        "close_price": ["close_price", "close"],
        "is_suspended": ["is_suspended", "suspend_flag"],
        "is_limit_up": ["is_limit_up", "limit_up"],
        "is_limit_down": ["is_limit_down", "limit_down"],
        "volume": ["volume", "vol"],
        "amount": ["amount"],
    },
    "trading_calendar": {
        "trade_date": ["trade_date", "date"],
        "is_rebalance_date": ["is_rebalance_date", "rebalance_flag"],
    },
}

BOOL_FIELDS = {"is_st", "is_suspended", "is_limit_up", "is_limit_down", "is_rebalance_date"}
DATE_FIELDS = {"trade_date", "report_date", "disclosure_date"}


def normalize_symbol(value: str) -> str:
    raw = value.strip().upper().replace("_", ".")
    if "." in raw:
        code, suffix = raw.split(".", 1)
        return f"{code.zfill(6)}.{suffix}"
    if len(raw) == 8 and raw[:2] in {"SH", "SZ"}:
        return f"{raw[2:]}.{raw[:2]}"
    if len(raw) == 8 and raw[-2:] in {"SH", "SZ"}:
        return f"{raw[:6]}.{raw[-2:]}"
    return raw


def normalize_date(value: str) -> str:
    raw = value.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return raw


def normalize_numeric(value: str) -> str:
    raw = value.strip().replace(",", "")
    if raw == "":
        return ""
    return str(float(raw))


def normalize_bool(value: str) -> str:
    raw = value.strip().lower()
    if raw in {"1", "true", "yes", "y", "t"}:
        return "true"
    if raw in {"0", "false", "no", "n", "f"}:
        return "false"
    return raw


def _source_for(row: dict[str, str], aliases: list[str]) -> tuple[str, str] | None:
    for alias in aliases:
        if alias in row:
            return alias, row.get(alias, "")
    return None


def _normalize(dataset: str, target_field: str, value: str) -> str:
    if target_field == "symbol":
        return normalize_symbol(value)
    if target_field in DATE_FIELDS:
        return normalize_date(value)
    if target_field in BOOL_FIELDS:
        return normalize_bool(value)
    if target_field in SCHEMAS[dataset]["numeric"]:
        return normalize_numeric(value)
    return value.strip()


def map_dataset(dataset: str, raw_rows: list[dict[str, str]], provider: str = "mock_a_share") -> tuple[list[dict[str, str]], list[MappingPreviewRow]]:
    mappings = FIELD_MAPPINGS[dataset]
    mapped_rows: list[dict[str, str]] = []
    preview: list[MappingPreviewRow] = []
    headers = set(raw_rows[0].keys()) if raw_rows else set()
    used_source_fields: set[str] = set()

    for target, aliases in mappings.items():
        source = next((alias for alias in aliases if alias in headers), "")
        if source:
            used_source_fields.add(source)
            preview.append(MappingPreviewRow(provider, dataset, source, target, "mapped", "source field mapped to standard field"))
        else:
            preview.append(MappingPreviewRow(provider, dataset, "", target, "missing", "no source field found for required target"))

    for raw in raw_rows:
        mapped: dict[str, str] = {}
        for target, aliases in mappings.items():
            source_value = _source_for(raw, aliases)
            if source_value is not None:
                mapped[target] = _normalize(dataset, target, source_value[1])
        mapped_rows.append(mapped)

    for extra in sorted(headers - used_source_fields):
        preview.append(MappingPreviewRow(provider, dataset, extra, "", "warning", "extra source field not used by standard mapping"))
    return mapped_rows, preview

