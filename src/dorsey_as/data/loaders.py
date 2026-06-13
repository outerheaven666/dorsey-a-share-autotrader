from __future__ import annotations

import csv
from pathlib import Path

from dorsey_as.models import FinancialSnapshot, MarketSnapshot, StockBasic


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def _as_float(row: dict[str, str], key: str) -> float:
    return float(row.get(key, "0") or 0)


def load_stock_basic(path: Path) -> dict[str, StockBasic]:
    with path.open(newline="", encoding="utf-8") as fh:
        return {
            row["symbol"]: StockBasic(
                symbol=row["symbol"],
                name=row["name"],
                industry=row["industry"],
                is_st=_as_bool(row.get("is_st", "false")),
                is_suspended=_as_bool(row.get("is_suspended", "false")),
            )
            for row in csv.DictReader(fh)
        }


def load_financial_snapshots(path: Path) -> dict[str, list[FinancialSnapshot]]:
    grouped: dict[str, list[FinancialSnapshot]] = {}
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            snapshot = FinancialSnapshot(
                symbol=row["symbol"],
                year=int(row["year"]),
                revenue=_as_float(row, "revenue"),
                net_profit=_as_float(row, "net_profit"),
                operating_cash_flow=_as_float(row, "operating_cash_flow"),
                free_cash_flow=_as_float(row, "free_cash_flow"),
                total_assets=_as_float(row, "total_assets"),
                total_liabilities=_as_float(row, "total_liabilities"),
                equity=_as_float(row, "equity"),
                accounts_receivable=_as_float(row, "accounts_receivable"),
                inventory=_as_float(row, "inventory"),
                goodwill=_as_float(row, "goodwill"),
                non_recurring_profit=_as_float(row, "non_recurring_profit"),
                roe=_as_float(row, "roe"),
                roic=_as_float(row, "roic"),
                gross_margin=_as_float(row, "gross_margin"),
                net_margin=_as_float(row, "net_margin"),
                rd_expense=_as_float(row, "rd_expense"),
                selling_expense=_as_float(row, "selling_expense"),
            )
            grouped.setdefault(snapshot.symbol, []).append(snapshot)
    for rows in grouped.values():
        rows.sort(key=lambda item: item.year)
    return grouped


def load_market_snapshots(path: Path) -> dict[str, MarketSnapshot]:
    with path.open(newline="", encoding="utf-8") as fh:
        return {
            row["symbol"]: MarketSnapshot(
                symbol=row["symbol"],
                trade_date=row["trade_date"],
                close_price=_as_float(row, "close_price"),
                market_cap=_as_float(row, "market_cap"),
                pe=_as_float(row, "pe"),
                pb=_as_float(row, "pb"),
                ev_to_fcf=_as_float(row, "ev_to_fcf"),
                fcf_yield=_as_float(row, "fcf_yield"),
                dividend_yield=_as_float(row, "dividend_yield"),
            )
            for row in csv.DictReader(fh)
        }


def load_sample_data(data_dir: Path) -> tuple[dict[str, StockBasic], dict[str, list[FinancialSnapshot]], dict[str, MarketSnapshot]]:
    return (
        load_stock_basic(data_dir / "stock_basic.csv"),
        load_financial_snapshots(data_dir / "financial_snapshot.csv"),
        load_market_snapshots(data_dir / "market_snapshot.csv"),
    )
