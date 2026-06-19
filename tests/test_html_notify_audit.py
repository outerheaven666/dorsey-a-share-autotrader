import csv
import json
from pathlib import Path

import pytest

from dorsey_as.audit import append_audit_record
from dorsey_as.cli import generate_report, notify_summary, run_backtest, run_score
from dorsey_as.config.loader import load_config
from dorsey_as.notify.feishu import send_feishu_notification
from dorsey_as.notify.summary import generate_notify_summary
from dorsey_as.reporting.charts import render_drawdown_chart, render_equity_curve_chart
from dorsey_as.reporting.html import generate_backtest_html_report, generate_run_html_report


def write_minimal_backtest_outputs(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "backtest_equity_curve.csv").write_text(
        "trade_date,cash,holdings_value,total_value,net_value\n"
        "2024-03-29,950000,50000,1000000,1.0\n"
        "2024-06-28,940000,80000,1020000,1.02\n"
        "2024-09-30,945000,65000,1010000,1.01\n",
        encoding="utf-8",
    )
    (output_dir / "backtest_metrics.csv").write_text(
        "metric,value\n"
        "total_return,0.02\n"
        "annualized_return,0.08\n"
        "max_drawdown,-0.0098\n"
        "sharpe_ratio,1.2\n"
        "turnover,0.3\n"
        "number_of_trades,5\n"
        "win_rate,0.6\n",
        encoding="utf-8",
    )
    (output_dir / "backtest_trades.csv").write_text(
        "trade_date,symbol,side,quantity,price,amount,commission,stamp_duty,slippage,status,reason\n"
        "2024-03-29,000001.SZ,BUY,100,10,1000,5,0,1,FILLED,\n"
        "2024-06-28,000002.SZ,BUY,0,20,0,0,0,0,SKIPPED,limit_up_no_buy\n",
        encoding="utf-8",
    )
    (output_dir / "backtest_holdings.csv").write_text(
        "trade_date,symbol,quantity,price,market_value\n"
        "2024-09-30,000001.SZ,100,10.1,1010\n",
        encoding="utf-8",
    )
    (output_dir / "backtest_audit_log.csv").write_text(
        "trade_date,event,passed,blocking_issues,warnings\n"
        "2024-03-29,data_quality_check,True,0,1\n",
        encoding="utf-8",
    )


def write_minimal_run_outputs(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "data_quality_report.csv").write_text(
        "as_of_date,check_name,severity,blocking,symbol,field,message\n"
        "2026-06-14,DataQualityCheck,info,False,,,data quality checks passed\n",
        encoding="utf-8",
    )
    (output_dir / "scores.csv").write_text(
        "symbol,quality_score,moat_score,valuation_score,risk_score,composite_score,blocked,reasons,warnings\n"
        "000001.SZ,80,75,70,100,78.5,False,,\n",
        encoding="utf-8",
    )
    (output_dir / "target_portfolio.csv").write_text(
        "symbol,name,industry,target_weight,score\n"
        "000001.SZ,One,Tech,0.05,78.5\n",
        encoding="utf-8",
    )
    (output_dir / "paper_trades.csv").write_text(
        "symbol,side,quantity,price,amount,mode\n"
        "000001.SZ,BUY,100,10,1000,paper\n",
        encoding="utf-8",
    )


def test_equity_curve_chart_can_generate_svg(tmp_path: Path) -> None:
    write_minimal_backtest_outputs(tmp_path)

    svg = render_equity_curve_chart(tmp_path / "backtest_equity_curve.csv")

    assert "<svg" in svg
    assert "Equity Curve" in svg


def test_drawdown_chart_can_generate_svg(tmp_path: Path) -> None:
    write_minimal_backtest_outputs(tmp_path)

    svg = render_drawdown_chart(tmp_path / "backtest_equity_curve.csv")

    assert "<svg" in svg
    assert "Drawdown" in svg


def test_chart_missing_data_returns_fallback_message(tmp_path: Path) -> None:
    html = render_equity_curve_chart(tmp_path / "missing.csv")

    assert "Insufficient data" in html


def test_html_reports_can_generate_and_include_safety_and_metrics(tmp_path: Path) -> None:
    config = load_config()
    write_minimal_run_outputs(tmp_path)
    write_minimal_backtest_outputs(tmp_path)

    run_report = generate_run_html_report(tmp_path, config, Path("config/default.yaml"))
    backtest_report = generate_backtest_html_report(tmp_path, config, Path("config/default.yaml"))

    run_text = run_report.read_text(encoding="utf-8")
    backtest_text = backtest_report.read_text(encoding="utf-8")
    assert "No real-money trading" in run_text
    assert "Top 10 Stock Scores" in run_text
    assert "Backtest Metrics" in backtest_text
    assert "total_return" in backtest_text
    assert "No real broker connection" in backtest_text


def test_generate_report_creates_markdown_and_html(tmp_path: Path) -> None:
    write_minimal_run_outputs(tmp_path)
    write_minimal_backtest_outputs(tmp_path)

    generate_report(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    assert (tmp_path / "run_report.md").exists()
    assert (tmp_path / "backtest_report.md").exists()
    assert (tmp_path / "run_report.html").exists()
    assert (tmp_path / "backtest_report.html").exists()


def test_notify_summary_default_is_dry_run_and_writes_payload_files(tmp_path: Path) -> None:
    config = load_config()
    write_minimal_backtest_outputs(tmp_path)

    payload_path, summary_path = generate_notify_summary(tmp_path, config, Path("config/default.yaml"))

    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    assert payload["dry_run"] is True
    assert payload["would_send"] is False
    assert "No real-money trading" in payload["safety_statement"]
    assert summary_path.exists()


def test_notify_enabled_without_webhook_env_refuses_real_send(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = load_config()
    config.notify.enabled = True
    config.notify.mode = "send"
    monkeypatch.delenv("FEISHU_WEBHOOK_URL", raising=False)

    with pytest.raises(RuntimeError, match="FEISHU_WEBHOOK_URL"):
        send_feishu_notification({"text": "hello"}, config.notify, tmp_path)


def test_notify_summary_cli_generates_files(tmp_path: Path) -> None:
    write_minimal_backtest_outputs(tmp_path)

    notify_summary(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    assert (tmp_path / "notify_payload.json").exists()
    assert (tmp_path / "notify_summary.md").exists()


def test_decision_audit_log_can_generate_and_excludes_sensitive_fields(tmp_path: Path) -> None:
    append_audit_record(
        tmp_path,
        stage="notify",
        as_of_date="2026-06-19",
        symbol="",
        decision_type="dry_run_notify",
        decision="write_payload",
        reason="notify.enabled=false",
        input_summary="webhook_url_env=FEISHU_WEBHOOK_URL",
        output_summary="notify_payload.json",
        severity="info",
        run_id="test-run",
    )

    audit_path = tmp_path / "decision_audit_log.csv"
    assert audit_path.exists()
    text = audit_path.read_text(encoding="utf-8").lower()
    assert "secret" not in text
    assert "token" not in text
    assert "webhook_url=" not in text
    with audit_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert rows[0]["stage"] == "notify"


def test_cli_runs_create_decision_audit_log(tmp_path: Path) -> None:
    run_score(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    run_backtest(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    assert (tmp_path / "decision_audit_log.csv").exists()
