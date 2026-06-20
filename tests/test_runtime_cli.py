import json
import subprocess
import sys
from pathlib import Path


def _run_cli(tmp_path: Path, command: str) -> dict:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "dorsey_as",
            "--output-dir",
            str(tmp_path),
            command,
            "--config",
            "config/default.yaml",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout.strip().splitlines()[-1])


def test_run_runtime_command_executes_successfully(tmp_path: Path) -> None:
    result = _run_cli(tmp_path, "run-runtime")

    assert {"market_data", "strategy_results", "portfolio", "risk", "executions", "ledger", "replay", "report"} <= set(result)
    assert result["replay"]["valid"] is True
    assert Path(result["ledger"]["json_path"]).exists()
    assert Path(result["report"]["markdown_path"]).exists()


def test_validate_runtime_artifacts_command_returns_valid_after_runtime_has_run(tmp_path: Path) -> None:
    _run_cli(tmp_path, "run-runtime")

    result = _run_cli(tmp_path, "validate-runtime-artifacts")

    assert result["valid"] is True
    assert all(check["passed"] for check in result["checks"])
