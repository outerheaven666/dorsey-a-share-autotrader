from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class HistoricalMarketSnapshot:
    symbol: str
    trade_date: str
    close_price: float
    is_suspended: bool = False
    is_limit_up: bool = False
    is_limit_down: bool = False


@dataclass(frozen=True)
class TradingCalendarEntry:
    trade_date: str
    is_rebalance_date: bool = False


@dataclass(frozen=True)
class TransactionCost:
    commission: float
    stamp_duty: float
    slippage: float

    @property
    def total_cost(self) -> float:
        return self.commission + self.stamp_duty + self.slippage


@dataclass(frozen=True)
class BacktestConfig:
    initial_cash: float = 1_000_000.0
    commission_rate: float = 0.0003
    minimum_commission: float = 5.0
    stamp_duty_rate: float = 0.0005
    slippage_rate: float = 0.001

    def transaction_cost(self, side: str, quantity: float, price: float) -> TransactionCost:
        amount = abs(quantity) * price
        commission = max(self.minimum_commission, amount * self.commission_rate) if amount > 0 else 0.0
        stamp_duty = amount * self.stamp_duty_rate if side.upper() == "SELL" else 0.0
        slippage = amount * self.slippage_rate
        return TransactionCost(
            commission=round(commission, 6),
            stamp_duty=round(stamp_duty, 6),
            slippage=round(slippage, 6),
        )


@dataclass(frozen=True)
class TradeRequest:
    symbol: str
    side: str
    quantity: float
    price: float


@dataclass(frozen=True)
class TradeValidation:
    accepted: bool
    reason: str = ""


@dataclass(frozen=True)
class BacktestTrade:
    trade_date: str
    symbol: str
    side: str
    quantity: float
    price: float
    amount: float
    commission: float
    stamp_duty: float
    slippage: float
    status: str
    reason: str = ""


@dataclass(frozen=True)
class EquityPoint:
    trade_date: str
    cash: float
    holdings_value: float
    total_value: float
    net_value: float


@dataclass(frozen=True)
class HoldingSnapshot:
    trade_date: str
    symbol: str
    quantity: float
    price: float
    market_value: float


@dataclass(frozen=True)
class BacktestMetrics:
    total_return: float
    annualized_return: float
    max_drawdown: float
    sharpe_ratio: float
    turnover: float
    number_of_trades: int
    win_rate: float | None = None


@dataclass(frozen=True)
class BacktestResult:
    equity_curve: list[EquityPoint] = field(default_factory=list)
    trades: list[BacktestTrade] = field(default_factory=list)
    holdings: list[HoldingSnapshot] = field(default_factory=list)
    metrics: BacktestMetrics | None = None
