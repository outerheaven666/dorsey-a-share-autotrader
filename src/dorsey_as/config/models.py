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
    include_data_quality_summary: bool = True
    include_top_scores: bool = True
    include_trade_summary: bool = True
    include_backtest_metrics: bool = True
    include_holdings_snapshot: bool = True


@dataclass
class AppConfig:
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    portfolio: PortfolioConfig = field(default_factory=PortfolioConfig)
    transaction_cost: TransactionCostConfig = field(default_factory=TransactionCostConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    data_quality: DataQualityConfig = field(default_factory=DataQualityConfig)
    report: ReportConfig = field(default_factory=ReportConfig)
