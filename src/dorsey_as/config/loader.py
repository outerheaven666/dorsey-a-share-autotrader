from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from typing import Any

from dorsey_as.config.defaults import PROJECT_ROOT
from dorsey_as.config.models import (
    AdapterContractConfig,
    AppConfig,
    AuditConfig,
    BacktestConfig,
    ContractVisualizationConfig,
    ContractDiffConfig,
    DataQualityConfig,
    DataSourceConfig,
    ExecutionPolicyConfig,
    FactorAuditConfig,
    FieldMappingConfig,
    NotifyConfig,
    PointInTimeConfig,
    PreLiveSafetyConfig,
    PortfolioConfig,
    ProviderTestsConfig,
    ProviderTemplatesConfig,
    ReportConfig,
    SchemaValidationConfig,
    SchemaMigrationConfig,
    SchemaVersioningConfig,
    ScoringConfig,
    TransactionCostConfig,
)


class ConfigError(ValueError):
    pass


DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "default.yaml"


def _parse_value(raw: str) -> Any:
    value = raw.strip()
    if value in {'""', "''"}:
        return ""
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value.strip('"').strip("'")


def _parse_yaml(path: Path) -> dict[str, dict[str, Any]]:
    data: dict[str, dict[str, Any]] = {}
    current_section: str | None = None
    current_key: str | None = None
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith(" ") and line.endswith(":"):
            current_section = line[:-1].strip()
            data[current_section] = {}
            current_key = None
            continue
        stripped = line.strip()
        if stripped.startswith("- "):
            if current_section is None or current_key is None:
                raise ConfigError(f"Invalid config list item: {raw_line}")
            value = _parse_value(stripped[2:])
            existing = data[current_section].setdefault(current_key, [])
            if not isinstance(existing, list):
                raise ConfigError(f"Config field {current_section}.{current_key} mixes scalar and list values.")
            existing.append(value)
            continue
        if current_section is None or ":" not in line:
            raise ConfigError(f"Invalid config line: {raw_line}")
        key, raw_value = stripped.split(":", 1)
        current_key = key.strip()
        if raw_value.strip() == "":
            data[current_section][current_key] = []
        else:
            data[current_section][current_key] = _parse_value(raw_value)
    return data


def _section(cls, raw: dict[str, Any] | None):
    values = raw or {}
    if cls is ReportConfig and isinstance(values.get("output_format"), list):
        formats = [str(item) for item in values["output_format"]]
        values = dict(values)
        values["output_formats"] = formats
        values["output_format"] = formats[0] if formats else "markdown"
    allowed = {field.name for field in fields(cls)}
    unknown = set(values) - allowed
    if unknown:
        raise ConfigError(f"Unknown config fields for {cls.__name__}: {sorted(unknown)}")
    return cls(**values)


def load_config(path: Path | str | None = None) -> AppConfig:
    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")
    raw = _parse_yaml(config_path)
    config = AppConfig(
        scoring=_section(ScoringConfig, raw.get("scoring")),
        portfolio=_section(PortfolioConfig, raw.get("portfolio")),
        transaction_cost=_section(TransactionCostConfig, raw.get("transaction_cost")),
        backtest=_section(BacktestConfig, raw.get("backtest")),
        data_quality=_section(DataQualityConfig, raw.get("data_quality")),
        report=_section(ReportConfig, raw.get("report")),
        notify=_section(NotifyConfig, raw.get("notify")),
        audit=_section(AuditConfig, raw.get("audit")),
        data_source=_section(DataSourceConfig, raw.get("data_source")),
        point_in_time=_section(PointInTimeConfig, raw.get("point_in_time")),
        factor_audit=_section(FactorAuditConfig, raw.get("factor_audit")),
        schema_validation=_section(SchemaValidationConfig, raw.get("schema_validation")),
        adapter_contract=_section(AdapterContractConfig, raw.get("adapter_contract")),
        field_mapping=_section(FieldMappingConfig, raw.get("field_mapping")),
        provider_tests=_section(ProviderTestsConfig, raw.get("provider_tests")),
        schema_versioning=_section(SchemaVersioningConfig, raw.get("schema_versioning")),
        contract_diff=_section(ContractDiffConfig, raw.get("contract_diff")),
        provider_templates=_section(ProviderTemplatesConfig, raw.get("provider_templates")),
        schema_migration=_section(SchemaMigrationConfig, raw.get("schema_migration")),
        contract_visualization=_section(ContractVisualizationConfig, raw.get("contract_visualization")),
        pre_live_safety=_section(PreLiveSafetyConfig, raw.get("pre_live_safety")),
        execution_policy=_section(ExecutionPolicyConfig, raw.get("execution_policy")),
    )
    validate_config(config)
    return config


def validate_config(config: AppConfig) -> None:
    weights = [
        config.scoring.quality_weight,
        config.scoring.moat_weight,
        config.scoring.valuation_weight,
        config.scoring.risk_weight,
    ]
    if any(weight < 0 for weight in weights) or sum(weights) <= 0:
        raise ConfigError("Scoring weights must be non-negative and have a positive total.")
    if abs(sum(weights) - 1.0) > 1e-6:
        raise ConfigError("Scoring weights must sum to 1.0.")

    if config.portfolio.max_positions <= 0:
        raise ConfigError("portfolio.max_positions must be positive.")
    for name in ["max_stock_weight", "max_industry_weight", "cash_reserve"]:
        value = getattr(config.portfolio, name)
        if value < 0 or value > 1:
            raise ConfigError(f"portfolio.{name} must be between 0 and 1.")
    if config.portfolio.cash_reserve >= 1:
        raise ConfigError("portfolio.cash_reserve must be below 1.")

    for name in ["commission_rate", "minimum_commission", "stamp_duty_rate", "slippage_rate"]:
        if getattr(config.transaction_cost, name) < 0:
            raise ConfigError(f"transaction_cost.{name} must be non-negative.")

    if config.backtest.initial_cash <= 0:
        raise ConfigError("backtest.initial_cash must be positive.")
    if config.backtest.risk_free_rate < 0:
        raise ConfigError("backtest.risk_free_rate must be non-negative.")

    if config.data_quality.stale_days_threshold <= 0:
        raise ConfigError("data_quality.stale_days_threshold must be positive.")
    if config.data_quality.severe_stale_days_threshold < config.data_quality.stale_days_threshold:
        raise ConfigError("data_quality.severe_stale_days_threshold must be >= stale_days_threshold.")
    if not config.report.output_formats:
        raise ConfigError("report.output_format must include at least one format.")
    unsupported = set(config.report.output_formats) - {"markdown", "html"}
    if unsupported:
        raise ConfigError(f"Unsupported report output formats: {sorted(unsupported)}")
    if config.notify.mode not in {"dry_run", "send"}:
        raise ConfigError("notify.mode must be dry_run or send.")
    if config.notify.channel != "feishu":
        raise ConfigError("notify.channel currently only supports feishu.")
    if config.data_source.mode != "local_csv":
        raise ConfigError("data_source.mode must be local_csv in this MVP.")
    if config.data_source.allow_network:
        raise ConfigError("data_source.allow_network must remain false in this MVP.")
    if config.data_source.provider != "sample_csv":
        raise ConfigError("data_source.provider must be sample_csv in this MVP.")
    if config.point_in_time.max_financial_lag_days <= 0:
        raise ConfigError("point_in_time.max_financial_lag_days must be positive.")
    if config.adapter_contract.mode != "mock_only":
        raise ConfigError("adapter_contract.mode must be mock_only in this MVP.")
    if config.adapter_contract.allow_network:
        raise ConfigError("adapter_contract.allow_network must remain false in this MVP.")
    if config.adapter_contract.allow_real_provider:
        raise ConfigError("adapter_contract.allow_real_provider must remain false in this MVP.")
    if config.adapter_contract.provider != "mock_a_share":
        raise ConfigError("adapter_contract.provider must be mock_a_share in this MVP.")
    if config.schema_versioning.current_version != "v1":
        raise ConfigError("schema_versioning.current_version must be v1 in this MVP.")
    if not config.schema_versioning.block_on_breaking_change:
        raise ConfigError("schema_versioning.block_on_breaking_change must remain true in this MVP.")
    if not config.provider_templates.templates_are_non_executable:
        raise ConfigError("provider_templates.templates_are_non_executable must remain true in this MVP.")
    if config.provider_templates.real_provider_templates_enabled:
        raise ConfigError("provider_templates.real_provider_templates_enabled must remain false in this MVP.")
    if config.schema_migration.compatibility_window_days <= 0:
        raise ConfigError("schema_migration.compatibility_window_days must be positive.")
    if config.schema_migration.current_version != config.schema_versioning.current_version:
        raise ConfigError("schema_migration.current_version must match schema_versioning.current_version.")
    if not config.schema_migration.block_on_expired_deprecation:
        raise ConfigError("schema_migration.block_on_expired_deprecation must remain true in this MVP.")
    if config.pre_live_safety.default_mode != "research_only":
        raise ConfigError("pre_live_safety.default_mode must be research_only in this MVP.")
    if "live" not in config.pre_live_safety.forbidden_modes:
        raise ConfigError("pre_live_safety.forbidden_modes must include live.")
    if not config.pre_live_safety.block_live_trading:
        raise ConfigError("pre_live_safety.block_live_trading must remain true in this MVP.")
    if not config.pre_live_safety.block_real_broker:
        raise ConfigError("pre_live_safety.block_real_broker must remain true in this MVP.")
    if not config.pre_live_safety.block_real_network_provider:
        raise ConfigError("pre_live_safety.block_real_network_provider must remain true in this MVP.")
