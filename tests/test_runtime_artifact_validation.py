from pathlib import Path

from dorsey_as.engine.artifact_validation import RuntimeArtifactValidator
from dorsey_as.engine.runtime import RuntimeEngine


def test_runtime_artifact_validator_returns_invalid_for_missing_artifacts(tmp_path: Path) -> None:
    result = RuntimeArtifactValidator().validate(output_dir=tmp_path)

    assert result["valid"] is False
    assert any(check["name"] == "runtime_ledger_json_exists" and not check["passed"] for check in result["checks"])
    assert any(check["name"] == "runtime_report_markdown_exists" and not check["passed"] for check in result["checks"])


def test_runtime_artifact_validator_returns_valid_after_runtime_run(tmp_path: Path) -> None:
    RuntimeEngine(output_dir=tmp_path).run_once(print_output=False)

    result = RuntimeArtifactValidator().validate(output_dir=tmp_path)

    assert result["valid"] is True
    assert all(check["passed"] for check in result["checks"])
