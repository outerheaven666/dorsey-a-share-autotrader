import csv
from pathlib import Path

import pytest

from dorsey_as.adapters.registry import get_provider
from dorsey_as.cli import diff_provider_contract_cli, explain_provider, generate_report, run_backtest, run_score, validate_provider_contract_cli
from dorsey_as.config.loader import load_config
from dorsey_as.schema_versioning.diff import diff_contracts
from dorsey_as.schema_versioning.loader import load_provider_contract


def test_provider_contract_v1_can_load() -> None:
    contract = load_provider_contract(Path("config/schemas/provider_contract_v1.yaml"))

    assert contract.version == "v1"
    assert "stock_basic" in contract.datasets
    assert "symbol" in contract.datasets["stock_basic"].required_fields


def test_provider_contract_candidate_can_load() -> None:
    contract = load_provider_contract(Path("config/schemas/provider_contract_candidate.yaml"))

    assert contract.version == "v1"
    assert "audit_opinion" in contract.datasets["financial_snapshot"].optional_fields


def test_additive_change_is_warning() -> None:
    baseline = load_provider_contract(Path("config/schemas/provider_contract_v1.yaml"))
    candidate = load_provider_contract(Path("config/schemas/provider_contract_candidate.yaml"))

    report = diff_contracts(baseline, candidate)

    assert any(row.change_type == "additive_optional_field" and row.severity == "warning" for row in report.rows)
    assert report.breaking_count == 0
    assert report.blocking_decision is False


def test_removed_required_field_is_breaking() -> None:
    baseline = load_provider_contract(Path("config/schemas/provider_contract_v1.yaml"))
    candidate = load_provider_contract(Path("data/fixtures/contract_diff_cases/candidate_breaking_missing_required.yaml"))

    report = diff_contracts(baseline, candidate)

    assert any(row.change_type == "required_field_removed" and row.breaking for row in report.rows)
    assert report.blocking_decision is True


def test_required_field_type_change_is_breaking() -> None:
    baseline = load_provider_contract(Path("config/schemas/provider_contract_v1.yaml"))
    candidate = load_provider_contract(Path("data/fixtures/contract_diff_cases/candidate_breaking_type_change.yaml"))

    report = diff_contracts(baseline, candidate)

    assert any(row.change_type == "field_type_changed" and row.field == "close_price" and row.breaking for row in report.rows)


def test_primary_key_change_is_breaking() -> None:
    baseline = load_provider_contract(Path("config/schemas/provider_contract_v1.yaml"))
    candidate = load_provider_contract(Path("data/fixtures/contract_diff_cases/candidate_breaking_primary_key.yaml"))

    report = diff_contracts(baseline, candidate)

    assert any(row.change_type == "primary_key_changed" and row.breaking for row in report.rows)


def test_dataset_removal_is_breaking() -> None:
    baseline = load_provider_contract(Path("config/schemas/provider_contract_v1.yaml"))
    candidate = load_provider_contract(Path("data/fixtures/contract_diff_cases/candidate_additive.yaml"))

    report = diff_contracts(baseline, candidate)

    assert any(row.change_type == "dataset_removed" and row.breaking for row in report.rows)


def test_compatible_optional_field_change_does_not_block_default_candidate() -> None:
    baseline = load_provider_contract(Path("config/schemas/provider_contract_v1.yaml"))
    candidate = load_provider_contract(Path("config/schemas/provider_contract_candidate.yaml"))

    report = diff_contracts(baseline, candidate)

    assert report.blocking_decision is False
    assert report.additive_count > 0


def test_diff_provider_contract_cli_generates_reports_and_audit(tmp_path: Path) -> None:
    output = diff_provider_contract_cli(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    assert output.name == "provider_contract_diff_report.csv"
    assert output.exists()
    assert (tmp_path / "provider_contract_diff_summary.md").exists()
    with (tmp_path / "decision_audit_log.csv").open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert any(row["stage"] == "schema_versioning" for row in rows)
    assert any(row["stage"] == "contract_diff" for row in rows)


def test_disabled_real_provider_template_is_not_registered() -> None:
    config = load_config()

    with pytest.raises(ValueError):
        get_provider("real_provider_template", config.adapter_contract)


def test_validate_provider_contract_still_passes(tmp_path: Path) -> None:
    output = validate_provider_contract_cli(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    assert output.exists()


def test_explain_provider_includes_schema_versioning_info(tmp_path: Path) -> None:
    output = explain_provider(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    text = output.read_text(encoding="utf-8")
    assert "schema contract version" in text
    assert "provider_contract_v1.yaml" in text
    assert "real provider template" in text
    assert "non-executable" in text


def test_run_score_and_backtest_still_use_local_csv(tmp_path: Path) -> None:
    run_score(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    run_backtest(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    manifest = (tmp_path / "data_source_manifest.csv").read_text(encoding="utf-8")
    assert "sample_csv" in manifest
    assert "mock_a_share" not in manifest


def test_reports_include_schema_versioning_and_contract_diff(tmp_path: Path) -> None:
    diff_provider_contract_cli(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    run_score(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    run_backtest(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    generate_report(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    run_md = (tmp_path / "run_report.md").read_text(encoding="utf-8")
    run_html = (tmp_path / "run_report.html").read_text(encoding="utf-8")
    backtest_md = (tmp_path / "backtest_report.md").read_text(encoding="utf-8")
    assert "Schema Versioning Summary" in run_md
    assert "Contract Diff Summary" in run_html
    assert "contract diff does not participate in trading decisions" in backtest_md


def test_no_real_network_or_secret_keywords_in_mvp8_source() -> None:
    source_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for root in [Path("src"), Path("config/schemas"), Path("data/fixtures")]
        for path in root.rglob("*")
        if path.is_file() and path.suffix in {".py", ".yaml", ".md", ".csv"}
    )
    forbidden = ["akshare", "tushare", "wind", "choice", "jqdata", "joinquant", "qmt", "ptrade"]
    assert not any(word in source_text.lower() for word in forbidden)
    assert not any(word in source_text.lower() for word in ["token=", "secret=", "password=", "webhook_url=", "credential="])
