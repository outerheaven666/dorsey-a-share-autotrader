import csv
from pathlib import Path

from dorsey_as.backtest.engine import BacktestEngine
from dorsey_as.backtest.metrics import calculate_max_drawdown
from dorsey_as.backtest.models import BacktestConfig, HistoricalMarketSnapshot, TradeRequest


def snapshot(symbol: str, date: str, price: float, *, suspended: bool = False, limit_up: bool = False, limit_down: bool = False) -> HistoricalMarketSnapshot:
    return HistoricalMarketSnapshot(
        symbol=symbol,
        trade_date=date,
        close_price=price,
        is_suspended=suspended,
        is_limit_up=limit_up,
        is_limit_down=limit_down,
    )


def test_transaction_cost_calculation_uses_commission_minimum_stamp_duty_and_slippage() -> None:
    config = BacktestConfig(initial_cash=100_000.0)

    buy = config.transaction_cost(side="BUY", quantity=1000, price=10)
    sell = config.transaction_cost(side="SELL", quantity=1000, price=10)

    assert buy.commission == 5.0
    assert buy.stamp_duty == 0.0
    assert buy.slippage == 10.0
    assert buy.total_cost == 15.0
    assert sell.commission == 5.0
    assert sell.stamp_duty == 5.0
    assert sell.slippage == 10.0
    assert sell.total_cost == 20.0


def test_suspended_stock_rejects_buy_and_sell() -> None:
    engine = BacktestEngine(config=BacktestConfig(initial_cash=100_000.0))
    blocked = snapshot("000001.SZ", "2024-03-29", 10.0, suspended=True)

    buy = engine.validate_trade(TradeRequest("000001.SZ", "BUY", 100, 10.0), blocked)
    sell = engine.validate_trade(TradeRequest("000001.SZ", "SELL", 100, 10.0), blocked)

    assert buy.accepted is False
    assert buy.reason == "suspended"
    assert sell.accepted is False
    assert sell.reason == "suspended"


def test_limit_up_rejects_buy_and_limit_down_rejects_sell() -> None:
    engine = BacktestEngine(config=BacktestConfig(initial_cash=100_000.0))

    buy = engine.validate_trade(
        TradeRequest("000001.SZ", "BUY", 100, 10.0),
        snapshot("000001.SZ", "2024-03-29", 10.0, limit_up=True),
    )
    sell = engine.validate_trade(
        TradeRequest("000001.SZ", "SELL", 100, 10.0),
        snapshot("000001.SZ", "2024-03-29", 10.0, limit_down=True),
    )

    assert buy.accepted is False
    assert buy.reason == "limit_up_no_buy"
    assert sell.accepted is False
    assert sell.reason == "limit_down_no_sell"


def test_max_drawdown_calculation_uses_peak_to_trough_decline() -> None:
    drawdown = calculate_max_drawdown([1.0, 1.2, 0.9, 1.1])

    assert round(drawdown, 6) == -0.25


def test_backtest_generates_equity_curve_and_output_files(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    engine = BacktestEngine.from_sample_data(
        data_dir=Path("data/sample"),
        output_dir=output_dir,
        config=BacktestConfig(initial_cash=1_000_000.0),
    )

    result = engine.run()

    assert len(result.equity_curve) >= 4
    assert result.equity_curve[0].total_value > 0
    assert result.metrics.number_of_trades > 0
    expected = {
        "backtest_equity_curve.csv",
        "backtest_trades.csv",
        "backtest_holdings.csv",
        "backtest_metrics.csv",
    }
    assert expected.issubset({path.name for path in output_dir.iterdir()})

    with (output_dir / "backtest_trades.csv").open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert any(row["status"] == "SKIPPED" for row in rows)
    assert any(row["reason"] in {"suspended", "limit_up_no_buy", "limit_down_no_sell"} for row in rows)
