from dorsey_as.portfolio.portfolio_engine import PortfolioEngine


def test_buy_symbols_receive_equal_weights() -> None:
    result = PortfolioEngine().evaluate(
        [
            {"symbol": "600519.SH", "decision": "BUY", "final_score": 0.4},
            {"symbol": "300750.SZ", "decision": "BUY", "final_score": 0.5},
            {"symbol": "000001.SZ", "decision": "HOLD", "final_score": 0.0},
        ]
    )
    weights = {row["symbol"]: row["target_weight"] for row in result["positions"]}

    assert weights["600519.SH"] == 0.5
    assert weights["300750.SZ"] == 0.5
    assert weights["000001.SZ"] == 0.0
    assert result["cash_weight"] == 0.0
    assert result["portfolio_mode"] == "mock"


def test_hold_and_sell_receive_zero_weight() -> None:
    result = PortfolioEngine().evaluate(
        [
            {"symbol": "600519.SH", "decision": "SELL", "final_score": -0.4},
            {"symbol": "000001.SZ", "decision": "HOLD", "final_score": 0.0},
        ]
    )

    assert all(row["target_weight"] == 0.0 for row in result["positions"])
    assert result["cash_weight"] == 1.0


def test_no_buy_symbols_cash_weight_is_one() -> None:
    result = PortfolioEngine().evaluate([{"symbol": "000001.SZ", "decision": "HOLD", "final_score": 0.0}])

    assert result["cash_weight"] == 1.0


def test_portfolio_output_is_deterministic() -> None:
    engine = PortfolioEngine()
    inputs = [
        {"symbol": "600519.SH", "decision": "BUY", "final_score": 0.4},
        {"symbol": "000001.SZ", "decision": "HOLD", "final_score": 0.0},
    ]

    assert engine.evaluate(inputs) == engine.evaluate(inputs)
