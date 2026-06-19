from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ScoringConfig:
    quality_weight: float = 0.35
    moat_weight: float = 0.30
    valuation_weight: float = 0.25
    risk_weight: float = 0.10


@dataclass
class PortfolioConfig:
    max_positions: int = 20
    max_stock_weight: float = 0.05
    max_industry_weight: float = 0.25
    cash_reserve: float = 0.05


@dataclass
class TransactionCostConfig:
    commission_rate: float = 0.0003
    minimum_commission: float = 5.0
    stamp_duty_rate: float = 0.0005
    slippage_rate: float = 0.001


@dataclass
class BacktestConfig:
    initial_cash: float = 1_000_000.0
    rebalance_frequency: str = "quarterly"
    benchmark_symbol: str = ""
    risk_free_rate: float = 0.0


@dataclass
class DataQualityConfig:
    stale_days_threshold: int = 450
    severe_stale_days_threshold: int = 900
    allow_stale_warning: bool = True
    block_on_missing_core_fields: bool = True
    block_on_lookahead_bias: bool = True
    block_on_severe_outlier: bool = True


@dataclass
class ReportConfig:
    output_format: str = "markdown"
    output_formats: list[str] = field(default_factory=lambda: ["markdown", "html"])
    include_data_quality_summary: bool = True
    include_top_scores: bool = True
    include_trade_summary: bool = True
    include_backtest_metrics: bool = True
    include_holdings_snapshot: bool = True
    include_equity_curve_chart: bool = True
    include_drawdown_chart: bool = True
    include_trade_table: bool = True
    include_holdings_table: bool = True
    include_data_quality_table: bool = True
    include_audit_summary: bool = True


@dataclass
class NotifyConfig:
    enabled: bool = False
    mode: str = "dry_run"
    channel: str = "feishu"
    webhook_url_env: str = "FEISHU_WEBHOOK_URL"
    write_payload_to_file: bool = True


@dataclass
class AuditConfig:
    enabled: bool = True
    include_score_decisions: bool = True
    include_portfolio_decisions: bool = True
    include_backtest_decisions: bool = True
    include_rejected_trades: bool = True
    include_data_quality_issues: bool = True


@dataclass
class DataSourceConfig:
    mode: str = "local_csv"
    provider: str = "sample_csv"
    allow_network: bool = False
    require_point_in_time: bool = True
    require_disclosure_date: bool = True
    trading_calendar_path: str = "data/sample/trading_calendar.csv"
    stock_basic_path: str = "data/sample/stock_basic.csv"
    financial_snapshot_path: str = "data/sample/financial_snapshot.csv"
    market_snapshot_path: str = "data/sample/market_snapshot.csv"
    historical_market_snapshot_path: str = "data/sample/historical_market_snapshot.csv"


@dataclass
class PointInTimeConfig:
    enabled: bool = True
    as_of_date: str = "2026-06-14"
    exclude_undisclosed_financials: bool = True
    block_on_future_disclosure: bool = True
    max_financial_lag_days: int = 540


@dataclass
class FactorAuditConfig:
    enabled: bool = True
    include_component_scores: bool = True
    include_raw_inputs: bool = True
    include_normalized_values: bool = True
    include_red_flag_reasons: bool = True
    include_moat_proxy_reasons: bool = True
    include_valuation_reasons: bool = True


@dataclass
class SchemaValidationConfig:
    enabled: bool = True
    block_on_missing_required_columns: bool = True
    block_on_invalid_numeric_fields: bool = True
    block_on_duplicate_keys: bool = True
    warn_on_extra_columns: bool = True


@dataclass
class AppConfig:
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    portfolio: PortfolioConfig = field(default_factory=PortfolioConfig)
    transaction_cost: TransactionCostConfig = field(default_factory=TransactionCostConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    data_quality: DataQualityConfig = field(default_factory=DataQualityConfig)
    report: ReportConfig = field(default_factory=ReportConfig)
    notify: NotifyConfig = field(default_factory=NotifyConfig)
    audit: AuditConfig = field(default_factory=AuditConfig)
    data_source: DataSourceConfig = field(default_factory=DataSourceConfig)
    point_in_time: PointInTimeConfig = field(default_factory=PointInTimeConfig)
    factor_audit: FactorAuditConfig = field(default_factory=FactorAuditConfig)
    schema_validation: SchemaValidationConfig = field(default_factory=SchemaValidationConfig)
