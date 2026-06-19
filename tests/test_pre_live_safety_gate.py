import csv
import re
from pathlib import Path

from dorsey_as.cli import (
    check_pre_live_safety,
    explain_provider,
    explain_safety,
    generate_report,
    notify_summary,
    run_backtest,
    run_score,
    simulate_live_request,
)
from dorsey_as.config.loader import load_config
from dorsey_as.safety.gates import PreLiveSafetyGate


def test_default_execution_policy_is_research_only_and_blocks_real_paths() -> None:
    config = load_config()

    assert config.execution_policy.mode == "research_only"
    assert config.execution_policy.allow_live_trading is False
    assert config.execution_policy.allow_real_broker is False
    assert config.execution_policy.allow_real_orders is False
    assert config.execution_policy.allow_real_network_data is False
    assert config.pre_live_safety.block_live_trading is True
    assert config.pre_live_safety.block_real_broker is True
    assert config.pre_live_safety.block_real_network_provider is True


def test_check_pre_live_safety_cli_generates_reports(tmp_path: Path) -> None:
    output = check_pre_live_safety(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    assert output.name == "pre_live_safety_report.csv"
    assert output.exists()
    assert (tmp_path / "pre_live_safety_summary.md").exists()
    text = (tmp_path / "pre_live_safety_summary.md").read_text(encoding="utf-8")
    assert "live trading allowed? False" in text
    assert "Pre-live safety gate" in text


def test_explain_safety_cli_generates_report(tmp_path: Path) -> None:
    output = explain_safety(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    assert output.name == "safety_explanation.md"
    text = output.read_text(encoding="utf-8")
    assert "research-only" in text
    assert "live trading" in text
    assert "I understand this system is research-only and live trading is disabled" in text


def test_simulate_live_request_is_blocked_and_writes_reports(tmp_path: Path) -> None:
    output = simulate_live_request(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    assert output.name == "simulated_live_request_report.csv"
    assert output.exists()
    assert (tmp_path / "simulated_live_request_summary.md").exists()
    rows = list(csv.DictReader(output.open(newline="", encoding="utf-8")))
    assert rows
    assert all(row["blocked"] == "True" for row in rows)
    summary = (tmp_path / "simulated_live_request_summary.md").read_text(encoding="utf-8")
    assert "live request was simulated only" in summary
    assert "no real order was created" in summary


def test_live_real_broker_orders_and_network_data_are_blocked() -> None:
    case_dir = Path("data/fixtures/safety_cases")
    for case in [
        "safety_live_mode_blocked.yaml",
        "safety_real_broker_blocked.yaml",
        "safety_real_network_data_blocked.yaml",
    ]:
        config = load_config(case_dir / case)
        result = PreLiveSafetyGate(config).evaluate()
        assert result.blocking_issues, case

    config = load_config()
    config.execution_policy.allow_real_orders = True
    result = PreLiveSafetyGate(config).evaluate()
    assert any(row.check_type == "real_orders" and row.blocking for row in result.rows)


def test_missing_safety_ack_can_be_identified() -> None:
    config = load_config(Path("data/fixtures/safety_cases/safety_missing_ack_blocked.yaml"))

    result = PreLiveSafetyGate(config).evaluate()

    assert any(row.check_type == "safety_acknowledgement" and row.blocking for row in result.rows)


def test_paper_backtest_and_dry_run_notify_are_allowed() -> None:
    for case in ["safety_paper_allowed.yaml", "safety_backtest_allowed.yaml"]:
        config = load_config(Path("data/fixtures/safety_cases") / case)
        result = PreLiveSafetyGate(config).evaluate()
        assert not result.blocking_issues

    config = load_config()
    result = PreLiveSafetyGate(config).evaluate()
    assert any(row.check_type == "dry_run_notify" and row.status == "pass" for row in result.rows)


def test_existing_cli_paths_still_run_with_default_policy(tmp_path: Path) -> None:
    run_score(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    run_backtest(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    notify_summary(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    assert (tmp_path / "scores.csv").exists()
    assert (tmp_path / "backtest_equity_curve.csv").exists()
    payload = (tmp_path / "notify_payload.json").read_text(encoding="utf-8")
    assert '"dry_run": true' in payload


def test_explain_provider_contains_pre_live_safety_info(tmp_path: Path) -> None:
    output = explain_provider(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    text = output.read_text(encoding="utf-8")
    assert "execution_policy.mode" in text
    assert "Pre-live safety enabled" in text
    assert "allow_live_trading: false" in text


def test_reports_include_pre_live_safety_summary(tmp_path: Path) -> None:
    check_pre_live_safety(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    run_score(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    run_backtest(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    generate_report(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    run_md = (tmp_path / "run_report.md").read_text(encoding="utf-8")
    run_html = (tmp_path / "run_report.html").read_text(encoding="utf-8")
    backtest_md = (tmp_path / "backtest_report.md").read_text(encoding="utf-8")
    assert "Pre-Live Safety Summary" in run_md
    assert "Pre-Live Safety Summary" in run_html
    assert "Current system has no live trading" in backtest_md


def test_decision_audit_contains_pre_live_safety_and_execution_policy(tmp_path: Path) -> None:
    check_pre_live_safety(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    simulate_live_request(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    with (tmp_path / "decision_audit_log.csv").open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert any(row["stage"] == "pre_live_safety" for row in rows)
    assert any(row["stage"] == "execution_policy" for row in rows)
    assert any(row["stage"] == "simulated_live_request" for row in rows)


def test_no_real_network_or_secret_keywords_in_safety_sources() -> None:
    source_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for root in [Path("src"), Path("config"), Path("data/fixtures")]
        for path in root.rglob("*")
        if path.is_file() and path.suffix in {".py", ".yaml", ".md", ".csv"}
    )
    forbidden = ["akshare", "tushare", "wind", "choice", "jqdata", "joinquant", "qmt", "ptrade"]
    assert not any(re.search(rf"\b{re.escape(word)}\b", source_text.lower()) for word in forbidden)
    assert not any(word in source_text.lower() for word in ["token=", "secret=", "password=", "webhook_url=", "credential="])
