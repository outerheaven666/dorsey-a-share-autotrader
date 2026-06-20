import csv
from pathlib import Path

from dorsey_as.reporting.runtime_report import RuntimeReportWriter


def _runtime_result() -> dict:
    return {
        "market_data": [
            {"symbol": "600519.SH", "price": 101.0},
            {"symbol": "000001.SZ", "price": 99.0},
        ],
        "strategy_results": [
            {"symbol": "600519.SH", "decision": "BUY", "final_score": 0.4},
            {"symbol": "000001.SZ", "decision": "SELL", "final_score": -0.4},
        ],
        "portfolio": {
            "positions": [
                {"symbol": "600519.SH", "target_weight": 1.0, "decision": "BUY"},
                {"symbol": "000001.SZ", "target_weight": 0.0, "decision": "SELL"},
            ],
            "cash_weight": 0.0,
            "portfolio_mode": "mock",
        },
        "risk": {"approved": True, "risk_flags": [], "adjusted_portfolio": {}},
        "executions": [
            {"symbol": "600519.SH", "status": "filled"},
            {"symbol": "000001.SZ", "status": "filled"},
        ],
        "ledger": {
            "json_path": "data/output/runtime_ledger_latest.json",
            "csv_path": "data/output/runtime_ledger_latest.csv",
        },
        "replay": {
            "valid": True,
            "summary": {"symbols_checked": 2, "executions_checked": 2, "mode": "mock"},
        },
    }


def test_runtime_report_writer_writes_markdown(tmp_path: Path) -> None:
    paths = RuntimeReportWriter().write(_runtime_result(), output_dir=tmp_path)

    markdown = (tmp_path / "runtime_report_latest.md").read_text(encoding="utf-8")
    assert paths["markdown_path"] == str(tmp_path / "runtime_report_latest.md")
    assert "## Runtime Mode" in markdown
    assert "## Strategy Decisions" in markdown
    assert "## Risk Check" in markdown
    assert "## Replay Validation" in markdown


def test_runtime_report_writer_writes_csv_summary(tmp_path: Path) -> None:
    paths = RuntimeReportWriter().write(_runtime_result(), output_dir=tmp_path)

    with (tmp_path / "runtime_report_summary.csv").open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert paths["csv_path"] == str(tmp_path / "runtime_report_summary.csv")
    assert len(rows) == 2
    assert rows[0]["symbol"] == "600519.SH"
    assert rows[0]["price"] == "101.0"
    assert rows[0]["decision"] == "BUY"
    assert rows[0]["final_score"] == "0.4"
    assert rows[0]["target_weight"] == "1.0"
    assert rows[0]["risk_approved"] == "True"
    assert rows[0]["execution_status"] == "filled"
