from dorsey_as.strategy.strategy_engine import StrategyEngine


def test_price_above_100_momentum_is_positive() -> None:
    result = StrategyEngine().evaluate({"symbol": "600519.SH", "price": 101.0})
    scores = {row["name"]: row["score"] for row in result["strategies"]}

    assert scores["momentum"] > 0
    assert scores["mean_reversion"] < 0


def test_price_below_100_mean_reversion_is_positive() -> None:
    result = StrategyEngine().evaluate({"symbol": "600519.SH", "price": 99.0})
    scores = {row["name"]: row["score"] for row in result["strategies"]}

    assert scores["mean_reversion"] > 0
    assert scores["momentum"] < 0


def test_final_decision_correctness() -> None:
    engine = StrategyEngine()

    assert engine.evaluate({"symbol": "600519.SH", "price": 101.0})["decision"] == "BUY"
    assert engine.evaluate({"symbol": "600519.SH", "price": 100.0})["decision"] == "HOLD"
    assert engine.evaluate({"symbol": "600519.SH", "price": 99.0})["decision"] == "SELL"


def test_strategy_engine_output_is_deterministic() -> None:
    engine = StrategyEngine()
    market_data = {"symbol": "600519.SH", "price": 101.0}

    assert engine.evaluate(market_data) == engine.evaluate(market_data)
