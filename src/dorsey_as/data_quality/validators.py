from __future__ import annotations

from dataclasses import fields
from datetime import date
from typing import Any

from dorsey_as.backtest.models import HistoricalMarketSnapshot, TradingCalendarEntry
from dorsey_as.data_quality.models import DataQualityIssue, DataQualityReport
from dorsey_as.models import FinancialSnapshot, MarketSnapshot, StockBasic


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _is_missing(value: Any) -> bool:
    return value is None or value == ""


def _issue(
    check_name: str,
    severity: str,
    message: str,
    *,
    blocking: bool,
    as_of_date: str,
    symbol: str = "",
    field: str = "",
) -> DataQualityIssue:
    return DataQualityIssue(
        check_name=check_name,
        severity=severity,
        message=message,
        blocking=blocking,
        symbol=symbol,
        field=field,
        as_of_date=as_of_date,
    )


class DataAvailabilityCheck:
    def run(
        self,
        as_of_date: str,
        stocks: dict[str, StockBasic],
        financials: dict[str, list[FinancialSnapshot]],
        markets: dict[str, MarketSnapshot],
        historical_market: dict[str, dict[str, HistoricalMarketSnapshot]] | None = None,
        calendar: list[TradingCalendarEntry] | None = None,
    ) -> list[DataQualityIssue]:
        issues: list[DataQualityIssue] = []
        if not stocks:
            issues.append(_issue("DataAvailabilityCheck", "error", "stock_basic data is empty", blocking=True, as_of_date=as_of_date))
        if not financials:
            issues.append(_issue("DataAvailabilityCheck", "error", "financial_snapshot data is empty", blocking=True, as_of_date=as_of_date))
        if not markets and historical_market is None:
            issues.append(_issue("DataAvailabilityCheck", "error", "market_snapshot data is empty", blocking=True, as_of_date=as_of_date))
        if historical_market is not None and as_of_date not in historical_market:
            issues.append(
                _issue(
                    "DataAvailabilityCheck",
                    "error",
                    "historical market data is missing for as_of_date",
                    blocking=True,
                    as_of_date=as_of_date,
                )
            )
        if calendar is not None and not calendar:
            issues.append(_issue("DataAvailabilityCheck", "error", "trading_calendar data is empty", blocking=True, as_of_date=as_of_date))
        return issues


class LookAheadBiasCheck:
    def run(self, as_of_date: str, financials: dict[str, list[FinancialSnapshot]]) -> list[DataQualityIssue]:
        issues: list[DataQualityIssue] = []
        as_of = _parse_date(as_of_date)
        for symbol, rows in financials.items():
            for row in rows:
                disclosure = _parse_date(row.disclosure_date)
                if as_of and disclosure and disclosure > as_of:
                    issues.append(
                        _issue(
                            "LookAheadBiasCheck",
                            "error",
                            f"financial report {row.report_date or row.year} disclosed at {row.disclosure_date} is after as_of_date {as_of_date}",
                            blocking=True,
                            as_of_date=as_of_date,
                            symbol=symbol,
                            field="disclosure_date",
                        )
                    )
        return issues


class MissingValueCheck:
    stock_fields = ["symbol", "name", "industry"]
    financial_fields = [
        "symbol",
        "year",
        "revenue",
        "net_profit",
        "operating_cash_flow",
        "free_cash_flow",
        "total_assets",
        "total_liabilities",
        "equity",
        "gross_margin",
        "net_margin",
        "report_date",
        "disclosure_date",
    ]
    market_fields = ["symbol", "trade_date", "close_price", "market_cap", "pe", "pb"]
    historical_fields = ["symbol", "trade_date", "close_price", "is_suspended", "is_limit_up", "is_limit_down"]
    calendar_fields = ["trade_date", "is_rebalance_date"]

    def run(
        self,
        as_of_date: str,
        stocks: dict[str, StockBasic],
        financials: dict[str, list[FinancialSnapshot]],
        markets: dict[str, MarketSnapshot],
        historical_market: dict[str, dict[str, HistoricalMarketSnapshot]] | None = None,
        calendar: list[TradingCalendarEntry] | None = None,
    ) -> list[DataQualityIssue]:
        issues: list[DataQualityIssue] = []
        for symbol, stock in stocks.items():
            issues.extend(self._check_object(as_of_date, "MissingValueCheck", symbol, stock, self.stock_fields))
        for symbol, rows in financials.items():
            for row in rows:
                issues.extend(self._check_object(as_of_date, "MissingValueCheck", symbol, row, self.financial_fields))
        for symbol, market in markets.items():
            issues.extend(self._check_object(as_of_date, "MissingValueCheck", symbol, market, self.market_fields))
        if historical_market is not None:
            for day_rows in historical_market.values():
                for symbol, snapshot in day_rows.items():
                    issues.extend(self._check_object(as_of_date, "MissingValueCheck", symbol, snapshot, self.historical_fields))
        if calendar is not None:
            for entry in calendar:
                issues.extend(self._check_object(as_of_date, "MissingValueCheck", "", entry, self.calendar_fields))
        return issues

    def _check_object(self, as_of_date: str, check_name: str, symbol: str, obj: object, names: list[str]) -> list[DataQualityIssue]:
        issues: list[DataQualityIssue] = []
        available_fields = {field.name for field in fields(obj)}
        for name in names:
            if name not in available_fields or _is_missing(getattr(obj, name, None)):
                issues.append(
                    _issue(
                        check_name,
                        "error",
                        f"missing required field {name}",
                        blocking=True,
                        as_of_date=as_of_date,
                        symbol=symbol,
                        field=name,
                    )
                )
        return issues


class StaleDataCheck:
    def __init__(self, stale_days_threshold: int = 450) -> None:
        self.stale_days_threshold = stale_days_threshold

    def run(self, as_of_date: str, financials: dict[str, list[FinancialSnapshot]]) -> list[DataQualityIssue]:
        issues: list[DataQualityIssue] = []
        as_of = _parse_date(as_of_date)
        if as_of is None:
            return issues
        for symbol, rows in financials.items():
            disclosed = [_parse_date(row.disclosure_date) for row in rows if _parse_date(row.disclosure_date)]
            valid_disclosed = [item for item in disclosed if item and item <= as_of]
            if not valid_disclosed:
                continue
            age = (as_of - max(valid_disclosed)).days
            if age > self.stale_days_threshold:
                issues.append(
                    _issue(
                        "StaleDataCheck",
                        "warning",
                        f"latest disclosure is {age} days old, threshold is {self.stale_days_threshold}",
                        blocking=False,
                        as_of_date=as_of_date,
                        symbol=symbol,
                        field="disclosure_date",
                    )
                )
        return issues


class OutlierCheck:
    def run(
        self,
        as_of_date: str,
        financials: dict[str, list[FinancialSnapshot]],
        markets: dict[str, MarketSnapshot],
        historical_market: dict[str, dict[str, HistoricalMarketSnapshot]] | None = None,
    ) -> list[DataQualityIssue]:
        issues: list[DataQualityIssue] = []
        for symbol, market in markets.items():
            issues.extend(self._check_positive(as_of_date, symbol, "close_price", market.close_price))
            issues.extend(self._check_positive(as_of_date, symbol, "market_cap", market.market_cap))
            issues.extend(self._check_positive(as_of_date, symbol, "pb", market.pb))
            if market.pe < 0:
                issues.append(_issue("OutlierCheck", "warning", "negative PE requires loss-making explanation", blocking=False, as_of_date=as_of_date, symbol=symbol, field="pe"))
        if historical_market is not None:
            for day_rows in historical_market.values():
                for symbol, snapshot in day_rows.items():
                    issues.extend(self._check_positive(as_of_date, symbol, "close_price", snapshot.close_price))
        for symbol, rows in financials.items():
            for row in rows:
                for field_name in ["revenue", "total_assets", "total_liabilities"]:
                    value = getattr(row, field_name)
                    if value < 0:
                        issues.append(
                            _issue(
                                "OutlierCheck",
                                "error",
                                f"{field_name} is negative",
                                blocking=True,
                                as_of_date=as_of_date,
                                symbol=symbol,
                                field=field_name,
                            )
                        )
                if row.gross_margin < -0.5 or row.gross_margin > 1.0:
                    issues.append(_issue("OutlierCheck", "error", "gross_margin is outside reasonable range", blocking=True, as_of_date=as_of_date, symbol=symbol, field="gross_margin"))
                if row.net_margin < -1.0 or row.net_margin > 1.0:
                    issues.append(_issue("OutlierCheck", "error", "net_margin is extremely abnormal", blocking=True, as_of_date=as_of_date, symbol=symbol, field="net_margin"))
        return issues

    def _check_positive(self, as_of_date: str, symbol: str, field_name: str, value: Any) -> list[DataQualityIssue]:
        if _is_missing(value):
            return []
        if value <= 0:
            return [
                _issue(
                    "OutlierCheck",
                    "error",
                    f"{field_name} must be positive",
                    blocking=True,
                    as_of_date=as_of_date,
                    symbol=symbol,
                    field=field_name,
                )
            ]
        return []


def run_data_quality_checks(
    as_of_date: str,
    stocks: dict[str, StockBasic],
    financials: dict[str, list[FinancialSnapshot]],
    markets: dict[str, MarketSnapshot],
    historical_market: dict[str, dict[str, HistoricalMarketSnapshot]] | None = None,
    calendar: list[TradingCalendarEntry] | None = None,
    stale_days_threshold: int = 450,
) -> DataQualityReport:
    issues: list[DataQualityIssue] = []
    issues.extend(DataAvailabilityCheck().run(as_of_date, stocks, financials, markets, historical_market, calendar))
    issues.extend(MissingValueCheck().run(as_of_date, stocks, financials, markets, historical_market, calendar))
    issues.extend(LookAheadBiasCheck().run(as_of_date, financials))
    issues.extend(StaleDataCheck(stale_days_threshold).run(as_of_date, financials))
    issues.extend(OutlierCheck().run(as_of_date, financials, markets, historical_market))
    return DataQualityReport(as_of_date=as_of_date, issues=issues)


def filter_financials_as_of(
    financials: dict[str, list[FinancialSnapshot]],
    as_of_date: str,
) -> dict[str, list[FinancialSnapshot]]:
    as_of = _parse_date(as_of_date)
    if as_of is None:
        return financials
    filtered: dict[str, list[FinancialSnapshot]] = {}
    for symbol, rows in financials.items():
        kept = [row for row in rows if row.disclosure_date and _parse_date(row.disclosure_date) and _parse_date(row.disclosure_date) <= as_of]
        if kept:
            filtered[symbol] = kept
    return filtered
