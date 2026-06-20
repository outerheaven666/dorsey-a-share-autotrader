import csv
from pathlib import Path

from dorsey_as.engine.runtime import RuntimeEngine


def test_runtime_output_contains_report_paths(tmp_path: Path) -> None:
    result = RuntimeEngine(output_dir=tmp_path).run_once(print_output=False)

    assert result["report"] == {
        "markdown_path": str(tmp_path / "runtime_report_latest.md"),
        "csv_path": str(tmp_path / "runtime_report_summary.csv"),
    }
    assert (tmp_path / "runtime_report_latest.md").exists()
    assert (tmp_path / "runtime_report_summary.csv").exists()


def test_runtime_report_csv_contains_one_row_per_symbol(tmp_path: Path) -> None:
    result = RuntimeEngine(output_dir=tmp_path).run_once(print_output=False)

    with Path(result["report"]["csv_path"]).open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == len(result["market_data"])
    assert {row["symbol"] for row in rows} == {"600519.SH", "000001.SZ", "300750.SZ"}
