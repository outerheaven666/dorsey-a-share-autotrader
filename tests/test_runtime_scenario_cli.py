import json
import subprocess
import sys
from pathlib import Path


def test_run_runtime_scenarios_cli_executes_successfully(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "dorsey_as",
            "--output-dir",
            str(tmp_path),
            "run-runtime-scenarios",
            "--config",
            "config/default.yaml",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    result = json.loads(completed.stdout.strip().splitlines()[-1])
    assert result["summary"] == {
        "total": 4,
        "passed": 4,
        "failed": 0,
        "mode": "mock",
    }
