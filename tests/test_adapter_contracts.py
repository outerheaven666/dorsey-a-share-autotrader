import csv
from pathlib import Path

import pytest

from dorsey_as.adapters.mapping import (
    map_dataset,
    normalize_bool,
    normalize_date,
    normalize_numeric,
    normalize_symbol,
)
from dorsey_as.adapters.mock_provider import MockAShareProvider
from dorsey_as.adapters.registry import get_provider
from dorsey_as.adapters.validation import validate_provider_contract
from dorsey_as.cli import explain_provider, run_backtest, run_score, validate_provider_contract_cli
from dorsey_as.config.loader import load_config


def test_mock_a_share_provider_loads_fixture_data() -> None:
    config = load_config()
    provider = MockAShareProvider(config.adapter_contract.fixture_dir)

    assert provider.name == "mock_a_share"
    assert provider.get_stock_basic()
    assert provider.get_financial_snapshot()
    assert provider.get_market_snapshot()
    assert provider.get_historical_market_snapshot()
    assert provider.get_trading_calendar()


def test_provider_registry_only_returns_mock_provider() -> None:
    config = load_config()

    provider = get_provider("mock_a_share", config.adapter_contract)

    assert isinstance(provider, MockAShareProvider)


def test_provider_registry_rejects_real_provider_name() -> None:
    config = load_config()

    with pytest.raises(ValueError, match="Only mock_a_share"):
        get_provider("real_external_provider", config.adapter_contract)


def test_provider_registry_rejects_network_access() -> None:
    config = load_config()
    config.adapter_contract.allow_network = True

    with pytest.raises(ValueError, match="Network access"):
        get_provider("mock_a_share", config.adapter_contract)


def test_field_mapping_generates_standard_internal_fields() -> None:
    raw = [
        {
            "ts_code": "600519SH",
            "stock_name": "Mock Kweichow",
            "industry_name": "Consumer",
            "st_flag": "N",
            "suspend_flag": "0",
            "vendor_extra": "fixture-only",
        }
    ]

    mapped, preview = map_dataset("stock_basic", raw)

    assert mapped[0]["symbol"] == "600519.SH"
    assert mapped[0]["name"] == "Mock Kweichow"
    assert mapped[0]["industry"] == "Consumer"
    assert mapped[0]["is_st"] == "false"
    assert mapped[0]["is_suspended"] == "false"
    assert any(row.source_field == "vendor_extra" and row.status == "warning" for row in preview)


def test_symbol_date_numeric_and_bool_normalization() -> None:
    assert normalize_symbol("600519SH") == "600519.SH"
    assert normalize_symbol("sz000001") == "000001.SZ"
    assert normalize_date("20240614") == "2024-06-14"
    assert normalize_date("2024/06/14") == "2024-06-14"
    assert normalize_numeric("1,234.50") == "1234.5"
    assert normalize_bool("Y") == "true"
    assert normalize_bool("0") == "false"


def test_provider_contract_validation_outputs_reports(tmp_path: Path) -> None:
    config = load_config()
    config.adapter_contract.output_dir = str(tmp_path)

    report = validate_provider_contract(config, tmp_path)

    assert report.passed is True
    assert (tmp_path / "provider_contract_report.csv").exists()
    assert (tmp_path / "provider_contract_summary.md").exists()
    assert (tmp_path / "adapter_mapped_preview.csv").exists()


def test_provider_contract_validation_fails_missing_required_field(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    for source in Path("data/fixtures/mock_provider").glob("*_raw.csv"):
        target = fixture_dir / source.name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (fixture_dir / "stock_basic_raw.csv").write_text(
        "ts_code,stock_name,st_flag,suspend_flag\n600519SH,Missing Industry,N,0\n",
        encoding="utf-8",
    )
    config = load_config()
    config.adapter_contract.fixture_dir = str(fixture_dir)

    report = validate_provider_contract(config, tmp_path)

    assert report.passed is False
    assert any(row.check_type == "schema_required_columns" and row.status == "fail" for row in report.rows)


def test_validate_provider_contract_cli_writes_reports_and_audit(tmp_path: Path) -> None:
    validate_provider_contract_cli(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    assert (tmp_path / "provider_contract_report.csv").exists()
    assert (tmp_path / "provider_contract_summary.md").exists()
    assert (tmp_path / "adapter_mapped_preview.csv").exists()
    with (tmp_path / "decision_audit_log.csv").open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert any(row["stage"] == "adapter_contract" for row in rows)


def test_explain_provider_generates_provider_explanation(tmp_path: Path) -> None:
    output = explain_provider(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    text = output.read_text(encoding="utf-8")
    assert output.name == "provider_explanation.md"
    assert "mock_only" in text
    assert "allow_network: false" in text
    assert "Mock provider" in text
    assert "No real network data source connection" in text


def test_run_score_and_backtest_default_to_local_csv_not_mock_provider(tmp_path: Path) -> None:
    run_score(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))
    run_backtest(Path("data/sample"), tmp_path, config_path=Path("config/default.yaml"))

    manifest = (tmp_path / "data_source_manifest.csv").read_text(encoding="utf-8")
    assert "sample_csv" in manifest
    assert "mock_a_share" not in manifest


def test_no_real_network_or_trading_keywords_in_adapter_source() -> None:
    source_text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in Path("src/dorsey_as/adapters").rglob("*.py"))
    forbidden = ["akshare", "tushare", "wind", "choice", "jqdata", "joinquant", "qmt", "ptrade"]
    assert not any(word in source_text.lower() for word in forbidden)
    assert not any(word in source_text.lower() for word in ["token=", "secret=", "password=", "webhook_url=", "credential="])
