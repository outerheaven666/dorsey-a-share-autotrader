import csv
from pathlib import Path

from dorsey_as.cli import explain_score, generate_report, run_backtest, run_score, validate_schema
from dorsey_as.config.loader import load_config
from dorsey_as.data.loaders import load_financial_snapshots, load_sample_data
from dorsey_as.data_source.local_csv import LocalCsvDataSource
from dorsey_as.data_source.schema import validate_csv_schema
from dorsey_as.factors.audit import write_factor_audit_log
from dorsey_as.point_in_time import build_point_in_time_snapshot
from dorsey_as.scoring import calculate_scores


def test_schema_validation_passes_default_sample_csv(tmp_path: Path) -> None:
    config = load_config()
    report = validate_csv_schema(LocalCsvDataSource(config.data_source), config.schema_validation, tmp_path)

    assert report.passed is True
    assert (tmp_path / "schema_validation_report.csv").exists()
    assert (tmp_path / "data_source_manifest.csv").exists()


def test_schema_validation_fails_missing_required_column(tmp_path: Path) -> None:
    bad = tmp_path / "bad_stock_basic.csv"
    bad.write_text("symbol,name\n000001.SZ,Missing Industry\n", encoding="utf-8")
    config = load_config()
    config.data_source.stock_basic_path = str(bad)

    report = validate_csv_schema(LocalCsvDataSource(config.data_source), config.schema_validation, tmp_path)

    assert report.passed is False
    assert any(row.check_type == "required_columns" and row.status == "fail" for row in report.rows)


def test_schema_validation_fails_invalid_numeric_field(tmp_path: Path) -> None:
    bad = tmp_path / "bad_market.csv"
    bad.write_text(
        "symbol,trade_date,close_price,market_cap,pe,pb,ev_to_fcf,fcf_yield,dividend_yield\n"
        "000001.SZ,2026-06-14,not-a-number,1000,10,1,8,0.1,0.02\n",
        encoding="utf-8",
    )
    config = load_config()
    config.data_source.market_snapshot_path = str(bad)

    report = validate_csv_schema(LocalCsvDataSource(config.data_source), config.schema_validation, tmp_path)

    assert report.passed is False
    assert any(row.check_type == "numeric_fields" and row.status == "fail" for row in report.rows)


def test_schema_validation_fails_duplicate_key(tmp_path: Path) -> None:
    bad = tmp_path / "dup_stock_basic.csv"
    bad.write_text(
        "symbol,name,industry,is_st,is_suspended\n"
        "000001.SZ,One,Tech,false,false\n"
        "000001.SZ,One Again,Tech,false,false\n",
        encoding="utf-8",
    )
    config = load_config()
    config.data_source.stock_basic_path = str(bad)

    report = validate_csv_schema(LocalCsvDataSource(config.data_source), config.schema_validation, tmp_path)

    assert report.passed is False
    assert any(row.check_type == "duplicate_keys" and row.status == "fail" for row in report.rows)


def test_schema_validation_extra_column_is_warning(tmp_path: Path) -> None:
    extra = tmp_path / "extra_stock_basic.csv"
    extra.write_text("symbol,name,industry,is_st,is_suspended,extra\n000001.SZ,One,Tech,false,false,x\n", encoding="utf-8")
    config = load_config()
    config.data_source.stock_basic_path = str(extra)

    report = validate_csv_schema(LocalCsvDataSource(config.data_source), config.schema_validation, tmp_path)

    assert any(row.check_type == "extra_columns" and row.severity == "warning" for row in report.rows)


def test_point_in_time_excludes_future_disclosure_and_keeps_visible_rows(tmp_path: Path) -> None:
    financials = load_financial_snapshots(Path("data/sample/financial_snapshot.csv"))

    visible = build_point_in_time_snapshot(financials, "2024-03-01", load_config().point_in_time, tmp_path)
    later_visible = build_point_in_time_snapshot(financials, "2024-03-29", load_config().point_in_time, tmp_path)

    assert not visible.visible_financials
    assert later_visible.visible_financials
    assert any(not row.visible and row.reason == "future_disclosure" for row in visible.rows)
    assert (tmp_path / "point_in_time_snapshot.csv").exists()


def test_run_score_generates_point_in_time_and_factor_audit(tmp_path: Path) -> None:
    run_score(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    assert (tmp_path / "point_in_time_snapshot.csv").exists()
    assert (tmp_path / "factor_audit_log.csv").exists()
    rows = list(csv.DictReader((tmp_path / "factor_audit_log.csv").open(newline="", encoding="utf-8")))
    groups = {row["factor_group"] for row in rows}
    assert {"quality", "moat", "valuation", "risk", "composite"}.issubset(groups)
    assert any(row["reason"] for row in rows)


def test_factor_audit_traces_red_flag_block_reason(tmp_path: Path) -> None:
    config = load_config()
    stocks, financials, markets = load_sample_data(Path("data/sample"))
    scores = calculate_scores(stocks, financials, markets, scoring_config=config.scoring)

    write_factor_audit_log(scores, stocks, financials, markets, tmp_path, config, "2026-06-14", "test-run")

    text = (tmp_path / "factor_audit_log.csv").read_text(encoding="utf-8")
    assert "negative_net_profit_2_of_3" in text or "st_stock" in text


def test_explain_score_generates_single_stock_report(tmp_path: Path) -> None:
    run_score(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    output = explain_score(Path("data/sample"), tmp_path, "600519.SH", Path("config/default.yaml"))

    assert output.name == "explain_600519.SH.md"
    text = output.read_text(encoding="utf-8")
    assert "600519.SH" in text
    assert "No real-money trading" in text


def test_validate_schema_cli_writes_report(tmp_path: Path) -> None:
    output = validate_schema(Path("data/sample"), tmp_path, Path("config/default.yaml"))

    assert output.name == "schema_validation_report.csv"
    assert output.exists()


def test_reports_include_point_in_time_and_factor_audit_summary(tmp_path: Path) -> None:
    run_score(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    run_backtest(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    generate_report(Path("data/sample"), tmp_path, Path("config/default.yaml"))

    run_md = (tmp_path / "run_report.md").read_text(encoding="utf-8")
    run_html = (tmp_path / "run_report.html").read_text(encoding="utf-8")
    backtest_md = (tmp_path / "backtest_report.md").read_text(encoding="utf-8")
    assert "Point-in-Time Summary" in run_md
    assert "Factor Audit Summary" in run_html
    assert "Point-in-Time Summary" in backtest_md


def test_no_real_network_or_broker_source_keywords_in_src() -> None:
    source_text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in Path("src").rglob("*.py"))
    forbidden = ["akshare", "tushare", "wind", "choice", "joinquant", "jqdatasdk", "qmt", "ptrade"]
    assert not any(word in source_text.lower() for word in forbidden)
    assert not any(word in source_text.lower() for word in ["token=", "secret=", "password=", "webhook_url="])
