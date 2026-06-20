import csv
from pathlib import Path

from dorsey_as.scenarios.scenario_report import ScenarioReportWriter


def _scenario_results() -> dict:
    return {
        "scenario_results": [
            {
                "name": "baseline_mixed",
                "passed": True,
                "checks": [
                    {"name": "includes_buy_sell_hold", "passed": True, "message": "ok"},
                    {"name": "risk_approved", "passed": True, "message": "ok"},
                ],
                "runtime_result": {},
            },
            {
                "name": "all_hold",
                "passed": True,
                "checks": [
                    {"name": "all_decisions_hold", "passed": True, "message": "ok"},
                ],
                "runtime_result": {},
            },
        ],
        "summary": {
            "total": 2,
            "passed": 2,
            "failed": 0,
            "mode": "mock",
        },
    }


def test_scenario_report_writer_writes_markdown(tmp_path: Path) -> None:
    paths = ScenarioReportWriter().write(_scenario_results(), output_dir=tmp_path)

    markdown = (tmp_path / "runtime_scenario_report_latest.md").read_text(encoding="utf-8")
    assert paths["markdown_path"] == str(tmp_path / "runtime_scenario_report_latest.md")
    assert "## Scenario Matrix Summary" in markdown
    assert "Total Scenarios" in markdown
    assert "Per Scenario Results" in markdown
    assert "Checks" in markdown
    assert "Runtime Safety Note" in markdown


def test_scenario_report_writer_writes_csv_summary(tmp_path: Path) -> None:
    paths = ScenarioReportWriter().write(_scenario_results(), output_dir=tmp_path)

    with (tmp_path / "runtime_scenario_summary.csv").open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert paths["csv_path"] == str(tmp_path / "runtime_scenario_summary.csv")
    assert len(rows) == 2
    assert rows[0] == {
        "scenario_name": "baseline_mixed",
        "passed": "True",
        "checks_total": "2",
        "checks_passed": "2",
        "checks_failed": "0",
        "mode": "mock",
    }
