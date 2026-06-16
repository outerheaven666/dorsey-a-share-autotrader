from __future__ import annotations

import math

from dorsey_as.backtest.models import BacktestMetrics, BacktestTrade, EquityPoint


def calculate_max_drawdown(values: list[float]) -> float:
    if not values:
        return 0.0
    peak = values[0]
    max_drawdown = 0.0
    for value in values:
        peak = max(peak, value)
        if peak > 0:
            max_drawdown = min(max_drawdown, value / peak - 1.0)
    return max_drawdown


def _daily_returns(equity_curve: list[EquityPoint]) -> list[float]:
    returns: list[float] = []
    for previous, current in zip(equity_curve, equity_curve[1:]):
        if previous.total_value > 0:
            returns.append(current.total_value / previous.total_value - 1.0)
    return returns


def calculate_metrics(equity_curve: list[EquityPoint], trades: list[BacktestTrade], risk_free_rate: float = 0.0) -> BacktestMetrics:
    if not equity_curve:
        return BacktestMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0, None)

    start_value = equity_curve[0].total_value
    end_value = equity_curve[-1].total_value
    total_return = end_value / start_value - 1.0 if start_value > 0 else 0.0
    periods = max(1, len(equity_curve) - 1)
    annualized_return = (1.0 + total_return) ** (252.0 / periods) - 1.0 if total_return > -1.0 else -1.0
    returns = _daily_returns(equity_curve)
    if len(returns) > 1:
        daily_risk_free = risk_free_rate / 252.0
        excess_returns = [value - daily_risk_free for value in returns]
        mean_return = sum(excess_returns) / len(excess_returns)
        variance = sum((value - mean_return) ** 2 for value in excess_returns) / (len(excess_returns) - 1)
        sharpe = mean_return / math.sqrt(variance) * math.sqrt(252.0) if variance > 0 else 0.0
    else:
        sharpe = 0.0

    filled_trades = [trade for trade in trades if trade.status == "FILLED"]
    total_turnover_value = sum(trade.amount for trade in filled_trades)
    average_equity = sum(point.total_value for point in equity_curve) / len(equity_curve)
    turnover = total_turnover_value / average_equity if average_equity > 0 else 0.0

    sell_trades = [trade for trade in filled_trades if trade.side == "SELL"]
    win_rate = None
    if sell_trades:
        # MVP approximation: a sell with positive cash proceeds after costs is counted as executable, not a realized PnL win.
        win_rate = sum(1 for trade in sell_trades if trade.amount > trade.commission + trade.stamp_duty + trade.slippage) / len(sell_trades)

    return BacktestMetrics(
        total_return=round(total_return, 6),
        annualized_return=round(annualized_return, 6),
        max_drawdown=round(calculate_max_drawdown([point.total_value for point in equity_curve]), 6),
        sharpe_ratio=round(sharpe, 6),
        turnover=round(turnover, 6),
        number_of_trades=len(filled_trades),
        win_rate=None if win_rate is None else round(win_rate, 6),
    )
