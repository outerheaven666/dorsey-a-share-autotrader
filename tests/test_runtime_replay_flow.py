from pathlib import Path

from dorsey_as.engine.runtime import RuntimeEngine


def test_runtime_output_contains_replay_summary(tmp_path: Path) -> None:
    result = RuntimeEngine(output_dir=tmp_path).run_once(print_output=False)

    assert result["replay"]["valid"] is True
    assert result["replay"]["summary"]["symbols_checked"] == len(result["market_data"])
    assert result["replay"]["summary"]["executions_checked"] == len(result["executions"])
    assert result["replay"]["summary"]["mode"] == "mock"
    assert Path(result["ledger"]["json_path"]).exists()
    assert Path(result["ledger"]["csv_path"]).exists()
