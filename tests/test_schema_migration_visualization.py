import csv
import re
from pathlib import Path

import pytest

from dorsey_as.adapters.registry import get_provider
from dorsey_as.cli import (
    diff_provider_contract_cli,
    explain_provider,
    generate_contract_diff_html_cli,
    generate_report,
    run_backtest,
    run_score,
    validate_provider_contract_cli,
    validate_schema_migration_cli,
)
from dorsey_as.config.loader import load_config
from dorsey_as.schema_migration.loader import load_migration_plan
from dorsey_as.schema_migration.validator import build_compatibility_matrix, validate_migration_plan
from safety_scan_helpers import assert_no_real_provider_or_broker_integration


def test_migration_yaml_can_load() -> None:
    plan = load_migration_plan(Path("config/schema_migrations/v1_to_v1_1.yaml"))

    assert plan.from_version == "v1"
    assert plan.to_version == "v1_1"
    assert plan.field_migrations


def test_validate_schema_migration_cli_generates_reports(tmp_path: Path) -> None:
    output = validate_schema_migration_cli(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    assert output.name == "schema_migration_report.csv"
    assert output.exists()
    assert (tmp_path / "schema_migration_summary.md").exists()


def test_default_migration_plan_has_no_blocking_failure() -> None:
    config = load_config()
    plan = load_migration_plan(Path(config.schema_migration.migration_plan))
    report = validate_migration_plan(plan, config.schema_migration, as_of_date="2026-06-19")

    assert report.blocking_decision is False
    assert report.expired_deprecation_count == 0


def test_expired_deprecation_is_blocking() -> None:
    config = load_config()
    plan = load_migration_plan(Path("data/fixtures/schema_migration_cases/migration_expired_deprecation.yaml"))
    report = validate_migration_plan(plan, config.schema_migration, as_of_date="2026-06-19")

    assert any(row.check_type == "expired_deprecation" and row.status == "fail" for row in report.rows)
    assert report.blocking_decision is True


def test_missing_migration_rule_is_blocking() -> None:
    config = load_config()
    plan = load_migration_plan(Path("data/fixtures/schema_migration_cases/migration_missing_rule.yaml"))
    report = validate_migration_plan(plan, config.schema_migration, as_of_date="2026-06-19")

    assert any(row.check_type == "missing_migration_rule" and row.status == "fail" for row in report.rows)


def test_pending_deprecation_is_warning() -> None:
    config = load_config()
    plan = load_migration_plan(Path("config/schema_migrations/v1_to_v1_1.yaml"))
    report = validate_migration_plan(plan, config.schema_migration, as_of_date="2026-09-15")

    assert any(row.check_type == "pending_deprecation" and row.severity == "warning" for row in report.rows)


def test_backward_compatible_alias_can_pass() -> None:
    config = load_config()
    plan = load_migration_plan(Path("data/fixtures/schema_migration_cases/migration_backward_compatible_alias.yaml"))
    report = validate_migration_plan(plan, config.schema_migration, as_of_date="2026-06-19")

    assert report.blocking_decision is False
    assert any(row.check_type == "backward_compatible_alias" and row.status == "pass" for row in report.rows)


def test_compatibility_matrix_can_generate() -> None:
    plan = load_migration_plan(Path("config/schema_migrations/v1_to_v1_1.yaml"))

    matrix = build_compatibility_matrix(plan, as_of_date="2026-06-19")

    assert matrix
    assert {"dataset", "field", "status", "backward_compatible"}.issubset(matrix[0])


def test_generate_contract_diff_html_cli_generates_outputs(tmp_path: Path) -> None:
    diff_provider_contract_cli(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    validate_schema_migration_cli(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    output = generate_contract_diff_html_cli(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    assert output.name == "provider_contract_diff.html"
    assert output.exists()
    assert (tmp_path / "provider_contract_diff_visual_summary.md").exists()
    html = output.read_text(encoding="utf-8")
    assert "Compatibility Matrix" in html
    assert "cdn" not in html.lower()
    assert "http://" not in html.lower()
    assert "https://" not in html.lower()


def test_explain_provider_contains_schema_migration_info(tmp_path: Path) -> None:
    output = explain_provider(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    text = output.read_text(encoding="utf-8")
    assert "Schema migration enabled" in text
    assert "v1_1" in text
    assert "validate-schema-migration" in text
    assert "generate-contract-diff-html" in text


def test_reports_include_schema_migration_summary(tmp_path: Path) -> None:
    diff_provider_contract_cli(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    validate_schema_migration_cli(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    generate_contract_diff_html_cli(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    run_score(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    run_backtest(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    generate_report(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    run_md = (tmp_path / "run_report.md").read_text(encoding="utf-8")
    run_html = (tmp_path / "run_report.html").read_text(encoding="utf-8")
    backtest_md = (tmp_path / "backtest_report.md").read_text(encoding="utf-8")
    assert "Schema Migration Summary" in run_md
    assert "Schema Migration Summary" in run_html
    assert "migration metadata does not participate in trading decisions" in backtest_md


def test_decision_audit_contains_schema_migration_and_visualization(tmp_path: Path) -> None:
    validate_schema_migration_cli(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    diff_provider_contract_cli(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    generate_contract_diff_html_cli(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    with (tmp_path / "decision_audit_log.csv").open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert any(row["stage"] == "schema_migration" for row in rows)
    assert any(row["stage"] == "contract_visualization" for row in rows)


def test_disabled_template_still_not_registered_and_existing_contracts_still_pass(tmp_path: Path) -> None:
    config = load_config()
    with pytest.raises(ValueError):
        get_provider("real_provider_template", config.adapter_contract)

    validate_provider_contract_cli(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    diff_provider_contract_cli(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    assert (tmp_path / "provider_contract_report.csv").exists()
    assert (tmp_path / "provider_contract_diff_report.csv").exists()


def test_run_score_and_backtest_still_use_local_csv(tmp_path: Path) -> None:
    run_score(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    run_backtest(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    manifest = (tmp_path / "data_source_manifest.csv").read_text(encoding="utf-8")
    assert "sample_csv" in manifest
    assert "mock_a_share" not in manifest


def test_no_real_network_or_secret_keywords_in_mvp9_text_sources() -> None:
    assert_no_real_provider_or_broker_integration([Path("src"), Path("config"), Path("data/fixtures")])
