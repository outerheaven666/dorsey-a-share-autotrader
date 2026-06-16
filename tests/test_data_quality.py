import csv
from pathlib import Path

import pytest

from dorsey_as.backtest.engine import BacktestEngine
from dorsey_as.backtest.models import BacktestConfig
from dorsey_as.cli import check_data_quality, run_backtest, run_score
from dorsey_as.data.loaders import load_sample_data
from dorsey_as.data_quality.report import write_data_quality_report
from dorsey_as.data_quality.validators import run_data_quality_checks
from dorsey_as.models import FinancialSnapshot, MarketSnapshot, StockBasic


def financial(disclosure_date: str = "2024-03-01") -> FinancialSnapshot:
    return FinancialSnapshot(
        symbol="000001.SZ",
        year=2023,
        revenue=100.0,
        net_profit=10.0,
        operating_cash_flow=12.0,
        free_cash_flow=8.0,
        total_assets=200.0,
        total_liabilities=80.0,
        equity=120.0,
        accounts_receivable=10.0,
        inventory=12.0,
        goodwill=0.0,
        non_recurring_profit=1.0,
        roe=0.12,
        roic=0.10,
        gross_margin=0.35,
        net_margin=0.10,
        report_date="2023-12-31",
        disclosure_date=disclosure_date,
    )


def market(close_price: float = 10.0) -> MarketSnapshot:
    return MarketSnapshot(
        symbol="000001.SZ",
        trade_date="2024-03-29",
        close_price=close_price,
        market_cap=1000.0,
        pe=12.0,
        pb=1.5,
        ev_to_fcf=10.0,
        fcf_yield=0.08,
        dividend_yield=0.03,
    )


def test_disclosure_date_after_as_of_date_is_blocking_look_ahead_issue() -> None:
    report = run_data_quality_checks(
        as_of_date="2024-03-29",
        stocks={"000001.SZ": StockBasic("000001.SZ", "Future Co", "Tech")},
        financials={"000001.SZ": [financial(disclosure_date="2024-04-30")]},
        markets={"000001.SZ": market()},
    )

    assert report.passed is False
    assert any(issue.check_name == "LookAheadBiasCheck" and issue.blocking for issue in report.issues)


def test_missing_market_price_is_blocking_issue() -> None:
    bad_market = market()
    object.__setattr__(bad_market, "close_price", None)

    report = run_data_quality_checks(
        as_of_date="2024-03-29",
        stocks={"000001.SZ": StockBasic("000001.SZ", "Missing Price", "Tech")},
        financials={"000001.SZ": [financial()]},
        markets={"000001.SZ": bad_market},
    )

    assert report.passed is False
    assert any(issue.check_name == "MissingValueCheck" and issue.field == "close_price" for issue in report.issues)


def test_non_positive_close_price_is_blocking_outlier_issue() -> None:
    report = run_data_quality_checks(
        as_of_date="2024-03-29",
        stocks={"000001.SZ": StockBasic("000001.SZ", "Bad Price", "Tech")},
        financials={"000001.SZ": [financial()]},
        markets={"000001.SZ": market(close_price=0.0)},
    )

    assert report.passed is False
    assert any(issue.check_name == "OutlierCheck" and issue.field == "close_price" for issue in report.issues)


def test_stale_data_generates_warning_without_blocking() -> None:
    report = run_data_quality_checks(
        as_of_date="2025-12-31",
        stocks={"000001.SZ": StockBasic("000001.SZ", "Stale Co", "Tech")},
        financials={"000001.SZ": [financial(disclosure_date="2024-01-01")]},
        markets={"000001.SZ": market()},
    )

    assert report.passed is True
    assert any(issue.check_name == "StaleDataCheck" and issue.severity == "warning" for issue in report.issues)


def test_normal_sample_data_passes_quality_checks() -> None:
    stocks, financials, markets = load_sample_data(Path("data/sample"))

    report = run_data_quality_checks("2026-06-14", stocks, financials, markets)

    assert report.passed is True
    assert not any(issue.blocking for issue in report.issues)


def test_check_data_quality_writes_report_csv(tmp_path: Path) -> None:
    output = check_data_quality(Path("data/sample"), tmp_path, as_of_date="2026-06-14")

    assert output.name == "data_quality_report.csv"
    with output.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert rows
    assert set(rows[0]) == {"as_of_date", "check_name", "severity", "blocking", "symbol", "field", "message"}


def test_run_score_stops_and_writes_report_when_data_quality_fails(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        run_score(Path("data/sample"), tmp_path, as_of_date="2024-03-01")

    assert (tmp_path / "data_quality_report.csv").exists()


def test_run_backtest_stops_on_future_data_and_writes_audit_log(tmp_path: Path) -> None:
    engine = BacktestEngine.from_sample_data(
        data_dir=Path("data/sample"),
        output_dir=tmp_path,
        config=BacktestConfig(initial_cash=1_000_000.0),
    )

    with pytest.raises(SystemExit):
        engine.run(as_of_override="2024-03-01")

    assert (tmp_path / "data_quality_report.csv").exists()
    assert (tmp_path / "backtest_audit_log.csv").exists()


def test_run_backtest_cli_writes_audit_log(tmp_path: Path) -> None:
    run_backtest(Path("data/sample"), tmp_path, cash=1_000_000.0)

    assert (tmp_path / "backtest_audit_log.csv").exists()
    with (tmp_path / "backtest_audit_log.csv").open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert rows
    assert set(rows[0]) == {"trade_date", "event", "passed", "blocking_issues", "warnings"}
