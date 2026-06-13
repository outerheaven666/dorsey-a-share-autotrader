from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StockBasic:
    symbol: str
    name: str
    industry: str
    is_st: bool = False
    is_suspended: bool = False


@dataclass
class FinancialSnapshot:
    symbol: str
    year: int
    revenue: float
    net_profit: float
    operating_cash_flow: float
    free_cash_flow: float
    total_assets: float
    total_liabilities: float
    equity: float
    accounts_receivable: float
    inventory: float
    goodwill: float
    non_recurring_profit: float
    roe: float
    roic: float
    gross_margin: float
    net_margin: float
    rd_expense: float = 0.0
    selling_expense: float = 0.0


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    trade_date: str
    close_price: float
    market_cap: float
    pe: float
    pb: float
    ev_to_fcf: float
    fcf_yield: float
    dividend_yield: float


@dataclass(frozen=True)
class FactorResult:
    symbol: str
    components: dict[str, float]
    score: float


@dataclass(frozen=True)
class RedFlagResult:
    symbol: str
    blocked: bool
    reasons: list[str]
    warnings: list[str]
    risk_score: float


@dataclass(frozen=True)
class ScoreResult:
    symbol: str
    quality_score: float
    moat_score: float
    valuation_score: float
    risk_score: float
    composite_score: float
    blocked: bool
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PortfolioPosition:
    symbol: str
    name: str
    industry: str
    target_weight: float
    score: float


@dataclass(frozen=True)
class TargetPortfolio:
    positions: list[PortfolioPosition]
    cash_weight: float = 0.05


@dataclass(frozen=True)
class PaperOrder:
    symbol: str
    side: str
    quantity: float
    price: float
    amount: float
    mode: str = "paper"
