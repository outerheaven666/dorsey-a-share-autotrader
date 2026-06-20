import csv
import re
from dataclasses import replace
from pathlib import Path

from dorsey_as.adapters.registry import get_provider
from dorsey_as.cli import (
    explain_provider,
    explain_safety,
    generate_release_notes,
    generate_report,
    notify_summary,
    release_checklist,
    run_backtest,
    run_score,
    scan_sensitive_content_cli,
    system_health,
)
from dorsey_as.config.loader import load_config
from dorsey_as.system_health.checks import data_output_is_ignored, evaluate_system_health
from dorsey_as.system_health.release import build_release_checklist
from dorsey_as.system_health.scanner import scan_sensitive_content


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def test_system_health_cli_outputs(tmp_path: Path) -> None:
    report = system_health(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    assert report.exists()
    assert (tmp_path / "system_health_summary.md").exists()
    assert (tmp_path / "output_artifact_manifest.csv").exists()
    assert (tmp_path / "output_artifact_manifest.md").exists()
    assert not [row for row in _rows(report) if row["blocking"] == "True"]


def test_scan_sensitive_content_cli_outputs(tmp_path: Path) -> None:
    report = scan_sensitive_content_cli(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    assert report.exists()
    assert (tmp_path / "sensitive_scan_summary.md").exists()
    assert not [row for row in _rows(report) if row["blocking"] == "True"]


def test_release_checklist_cli_outputs(tmp_path: Path) -> None:
    report = release_checklist(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    assert report.exists()
    assert (tmp_path / "release_checklist.md").exists()
    assert not [row for row in _rows(report) if row["blocking"] == "True"]


def test_generate_release_notes_cli_output(tmp_path: Path) -> None:
    output = generate_release_notes(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    text = output.read_text(encoding="utf-8")

    assert output.name == "release_notes_v0.11.0.md"
    assert "# v0.11.0" in text
    assert "does not support real trading" in text
    assert "does not publish, tag, push, or release automatically" in text


def test_sensitive_scan_allows_documentation_mentions_and_blocks_assignments(tmp_path: Path) -> None:
    config = load_config()
    docs = tmp_path / "docs.md"
    docs.write_text("AkShare, Tushare, Wind, Choice, JQData, QMT, and PTrade are documented as disabled.\n", encoding="utf-8")
    fixture = tmp_path / "bad.py"
    assignment = "api" + "_key" + "=" + "sample"
    fixture.write_text(assignment + "\n", encoding="utf-8")
    config.sensitive_scan = replace(config.sensitive_scan, scan_paths=[str(tmp_path)])

    result = scan_sensitive_content(config, root=Path("."))

    assert any(finding.blocking for finding in result.findings if finding.path.endswith("bad.py"))
    assert not any(finding.blocking for finding in result.findings if finding.path.endswith("docs.md"))


def test_health_and_release_defaults_are_non_blocking() -> None:
    config = load_config()
    health = evaluate_system_health(config, Path("data/output"))
    checklist = build_release_checklist(config, health, Path("data/output"))

    assert not health.blocking_issues
    assert not [item for item in checklist if item.blocking]


def test_data_output_gitignore_and_safety_defaults() -> None:
    config = load_config()

    assert data_output_is_ignored(Path("."))
    assert config.execution_policy.mode == "research_only"
    assert config.execution_policy.allow_live_trading is False
    assert config.execution_policy.allow_real_broker is False
    assert config.execution_policy.allow_real_orders is False
    assert config.execution_policy.allow_real_network_data is False
    assert config.pre_live_safety.block_live_trading is True
    assert config.pre_live_safety.block_real_broker is True
    assert config.pre_live_safety.block_real_network_provider is True


def test_provider_registry_still_rejects_real_provider_template() -> None:
    config = load_config()
    try:
        get_provider("real_provider_template", config.adapter_contract)
        registered = True
    except ValueError:
        registered = False

    assert registered is False


def test_existing_commands_still_generate_local_outputs(tmp_path: Path) -> None:
    score_path = run_score(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    backtest_path = run_backtest(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    notify_payload, notify_summary_path = notify_summary(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    assert score_path.exists()
    assert backtest_path.exists()
    assert notify_payload.exists()
    assert notify_summary_path.exists()
    assert "dry-run" in notify_summary_path.read_text(encoding="utf-8").lower()


def test_explanations_and_reports_include_system_health_release_info(tmp_path: Path) -> None:
    system_health(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    release_checklist(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    provider = explain_provider(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    safety = explain_safety(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    run_score(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    run_backtest(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    generate_report(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    assert "System health enabled" in provider.read_text(encoding="utf-8")
    assert "release checklist enabled" in safety.read_text(encoding="utf-8")
    assert "System Health And Release Summary" in (tmp_path / "run_report.md").read_text(encoding="utf-8")
    assert "System health rows" in (tmp_path / "backtest_report.md").read_text(encoding="utf-8")


def test_decision_audit_contains_mvp11_stages(tmp_path: Path) -> None:
    system_health(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    scan_sensitive_content_cli(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    release_checklist(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    generate_release_notes(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    text = (tmp_path / "decision_audit_log.csv").read_text(encoding="utf-8")

    assert "system_health" in text
    assert "release_checklist" in text
    assert "sensitive_scan" in text
    assert "release_notes" in text
    assert "artifact_manifest" in text


def test_no_credential_like_assignment_or_real_imports_in_source() -> None:
    source_text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in list(Path("src").rglob("*.py")) + list(Path("config").rglob("*.yaml")) + list(Path("data/fixtures").rglob("*.yaml")))

    assert re.search(r"(token|secret|password|webhook_url|credential)=['\"]?[A-Za-z0-9_\-]{3,}", source_text.lower()) is None
    assert re.search(r"\b(import|from)\s+(akshare|tushare|wind|choice|jqdata|qmt|ptrade)\b", source_text.lower()) is None
