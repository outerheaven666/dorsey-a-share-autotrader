import csv
from pathlib import Path

from dorsey_as.scenarios.scenario_runner import RuntimeScenarioRunner


def test_runtime_scenario_runner_output_includes_report_paths(tmp_path: Path) -> None:
    result = RuntimeScenarioRunner().run_all(output_dir=tmp_path)

    assert result["report"] == {
        "markdown_path": str(tmp_path / "runtime_scenario_report_latest.md"),
        "csv_path": str(tmp_path / "runtime_scenario_summary.csv"),
    }
    assert (tmp_path / "runtime_scenario_report_latest.md").exists()
    assert (tmp_path / "runtime_scenario_summary.csv").exists()


def test_runtime_scenario_report_csv_contains_one_row_per_scenario(tmp_path: Path) -> None:
    result = RuntimeScenarioRunner().run_all(output_dir=tmp_path)

    with Path(result["report"]["csv_path"]).open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == result["summary"]["total"]
    assert {row["scenario_name"] for row in rows} == {
        "baseline_mixed",
        "all_hold",
        "buy_single_cap",
        "sell_path",
    }
