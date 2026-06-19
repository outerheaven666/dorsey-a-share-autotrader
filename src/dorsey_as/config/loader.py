from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from typing import Any

from dorsey_as.config.defaults import PROJECT_ROOT
from dorsey_as.config.models import (
    AppConfig,
    AuditConfig,
    BacktestConfig,
    DataQualityConfig,
    NotifyConfig,
    PortfolioConfig,
    ReportConfig,
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
