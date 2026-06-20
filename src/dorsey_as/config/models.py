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
class AdapterContractConfig:
    enabled: bool = True
    mode: str = "mock_only"
    allow_network: bool = False
    allow_real_provider: bool = False
    provider: str = "mock_a_share"
    contract_version: str = "v1"
    fixture_dir: str = "data/fixtures/mock_provider"
    output_dir: str = "data/output"


@dataclass
class FieldMappingConfig:
    enabled: bool = True
    strict_required_fields: bool = True
    allow_extra_fields: bool = True
    normalize_symbol: bool = True
    normalize_dates: bool = True


@dataclass
class ProviderTestsConfig:
    enabled: bool = True
    require_stock_basic: bool = True
    require_financial_snapshot: bool = True
    require_market_snapshot: bool = True
    require_historical_market_snapshot: bool = True
    require_trading_calendar: bool = True
    block_on_contract_failure: bool = True


@dataclass
class SchemaVersioningConfig:
    enabled: bool = True
    current_version: str = "v1"
    schema_dir: str = "config/schemas"
    baseline_contract: str = "config/schemas/provider_contract_v1.yaml"
    candidate_contract: str = "config/schemas/provider_contract_candidate.yaml"
    block_on_breaking_change: bool = True
    warn_on_additive_change: bool = True
    allow_documented_extra_fields: bool = True


@dataclass
class ContractDiffConfig:
    enabled: bool = True
    output_dir: str = "data/output"
    compare_required_fields: bool = True
    compare_field_types: bool = True
    compare_date_fields: bool = True
    compare_numeric_fields: bool = True
    compare_boolean_fields: bool = True
    compare_dataset_presence: bool = True


@dataclass
class ProviderTemplatesConfig:
    enabled: bool = True
    real_provider_templates_enabled: bool = False
    templates_are_non_executable: bool = True


@dataclass
class SchemaMigrationConfig:
    enabled: bool = True
    current_version: str = "v1"
    target_version: str = "v1_1"
    migration_dir: str = "config/schema_migrations"
    migration_plan: str = "config/schema_migrations/v1_to_v1_1.yaml"
    compatibility_window_days: int = 180
    block_on_expired_deprecation: bool = True
    block_on_missing_migration_plan: bool = True
    warn_on_pending_deprecation: bool = True
    allow_backward_compatible_aliases: bool = True


@dataclass
class ContractVisualizationConfig:
    enabled: bool = True
    output_dir: str = "data/output"
    generate_html: bool = True
    generate_markdown: bool = True
    include_dataset_summary: bool = True
    include_field_lifecycle: bool = True
    include_migration_steps: bool = True
    include_breaking_change_table: bool = True
    include_additive_change_table: bool = True
    include_compatibility_matrix: bool = True


@dataclass
class PreLiveSafetyConfig:
    enabled: bool = True
    default_mode: str = "research_only"
    allowed_modes: list[str] = field(default_factory=lambda: ["research_only", "paper", "backtest", "dry_run"])
    forbidden_modes: list[str] = field(default_factory=lambda: ["live", "real_broker", "real_order"])
    require_manual_confirmation: bool = True
    require_read_only_first: bool = True
    require_schema_validation: bool = True
    require_provider_contract_validation: bool = True
    require_contract_diff_check: bool = True
    require_schema_migration_check: bool = True
    require_data_quality_check: bool = True
    require_point_in_time_check: bool = True
    require_factor_audit_check: bool = True
    require_backtest_before_paper: bool = True
    require_paper_before_live: bool = True
    block_live_trading: bool = True
    block_real_broker: bool = True
    block_real_network_provider: bool = True
    block_missing_audit_log: bool = True
    block_missing_safety_ack: bool = True
    safety_ack_phrase: str = "I understand this system is research-only and live trading is disabled"
    output_dir: str = "data/output"


@dataclass
class ExecutionPolicyConfig:
    mode: str = "research_only"
    allow_live_trading: bool = False
    allow_real_broker: bool = False
    allow_real_orders: bool = False
    allow_real_network_data: bool = False
    allow_dry_run_notify: bool = True
    allow_paper_trading: bool = True
    allow_backtest: bool = True
    allow_local_csv: bool = True
    allow_mock_provider: bool = True


@dataclass
class SystemHealthConfig:
    enabled: bool = True
    output_dir: str = "data/output"
    release_version: str = "v0.11.0"
    require_clean_worktree: bool = False
    check_gitignore_outputs: bool = True
    check_sensitive_patterns: bool = True
    check_forbidden_imports: bool = True
    check_forbidden_keywords: bool = True
    check_config_safety_flags: bool = True
    check_required_cli_outputs: bool = True
    check_reports_exist: bool = True
    check_mock_provider_only: bool = True
    check_no_live_trading: bool = True
    check_no_real_broker: bool = True
    check_no_real_network_data: bool = True


@dataclass
class ReleaseChecklistConfig:
    enabled: bool = True
    output_dir: str = "data/output"
    release_version: str = "v0.11.0"
    require_pytest_passed: bool = True
    require_health_check_passed: bool = True
    require_pre_live_safety_passed: bool = True
    require_contract_diff_passed: bool = True
    require_schema_migration_passed: bool = True
    require_provider_contract_passed: bool = True
    require_data_quality_passed: bool = True
    require_backtest_passed: bool = True
    require_reports_generated: bool = True
    require_no_sensitive_strings: bool = True
    require_no_data_output_tracked: bool = True
    generate_release_notes: bool = True


@dataclass
class SensitiveScanConfig:
    enabled: bool = True
    scan_paths: list[str] = field(default_factory=lambda: ["README.md", "config", "data/fixtures", "src", "tests"])
    forbidden_patterns: list[str] = field(
        default_factory=lambda: [
            "token=",
            "secret=",
            "password=",
            "webhook_url=",
            "credential=",
            "broker_password",
            "access_key",
            "api_key",
        ]
    )
    forbidden_provider_keywords: list[str] = field(default_factory=lambda: ["AkShare", "Tushare", "Wind", "Choice", "JQData", "QMT", "PTrade"])
    allow_documentation_mentions: bool = True


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
    adapter_contract: AdapterContractConfig = field(default_factory=AdapterContractConfig)
    field_mapping: FieldMappingConfig = field(default_factory=FieldMappingConfig)
    provider_tests: ProviderTestsConfig = field(default_factory=ProviderTestsConfig)
    schema_versioning: SchemaVersioningConfig = field(default_factory=SchemaVersioningConfig)
    contract_diff: ContractDiffConfig = field(default_factory=ContractDiffConfig)
    provider_templates: ProviderTemplatesConfig = field(default_factory=ProviderTemplatesConfig)
    schema_migration: SchemaMigrationConfig = field(default_factory=SchemaMigrationConfig)
    contract_visualization: ContractVisualizationConfig = field(default_factory=ContractVisualizationConfig)
    pre_live_safety: PreLiveSafetyConfig = field(default_factory=PreLiveSafetyConfig)
    execution_policy: ExecutionPolicyConfig = field(default_factory=ExecutionPolicyConfig)
    system_health: SystemHealthConfig = field(default_factory=SystemHealthConfig)
    release_checklist: ReleaseChecklistConfig = field(default_factory=ReleaseChecklistConfig)
    sensitive_scan: SensitiveScanConfig = field(default_factory=SensitiveScanConfig)
