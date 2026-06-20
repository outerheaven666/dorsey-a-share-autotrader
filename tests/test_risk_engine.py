from dorsey_as.risk.risk_engine import RiskEngine


def test_position_over_06_is_capped_and_warned() -> None:
    portfolio = {
        "positions": [{"symbol": "600519.SH", "target_weight": 1.0, "decision": "BUY"}],
        "cash_weight": 0.0,
        "portfolio_mode": "mock",
    }

    result = RiskEngine().evaluate(portfolio)

    assert result["approved"] is True
    assert result["adjusted_portfolio"]["positions"][0]["target_weight"] == 0.6
    assert result["adjusted_portfolio"]["cash_weight"] == 0.4
    assert any(flag["code"] == "MAX_SINGLE_POSITION_CAPPED" and flag["severity"] == "WARNING" for flag in result["risk_flags"])


def test_total_invested_weight_over_one_blocks() -> None:
    portfolio = {
        "positions": [
            {"symbol": "600519.SH", "target_weight": 0.7, "decision": "BUY"},
            {"symbol": "300750.SZ", "target_weight": 0.7, "decision": "BUY"},
        ],
        "cash_weight": 0.0,
        "portfolio_mode": "mock",
    }

    result = RiskEngine().evaluate(portfolio)

    assert result["approved"] is False
    assert any(flag["code"] == "TOTAL_INVESTED_WEIGHT_EXCEEDED" and flag["severity"] == "BLOCKING" for flag in result["risk_flags"])


def test_negative_weights_block() -> None:
    portfolio = {
        "positions": [{"symbol": "600519.SH", "target_weight": -0.1, "decision": "BUY"}],
        "cash_weight": -0.1,
        "portfolio_mode": "mock",
    }

    result = RiskEngine().evaluate(portfolio)

    assert result["approved"] is False
    assert any(flag["code"] == "NEGATIVE_POSITION_WEIGHT" for flag in result["risk_flags"])
    assert any(flag["code"] == "NEGATIVE_CASH_WEIGHT" for flag in result["risk_flags"])


def test_portfolio_within_limits_is_approved() -> None:
    portfolio = {
        "positions": [
            {"symbol": "600519.SH", "target_weight": 0.5, "decision": "BUY"},
            {"symbol": "000001.SZ", "target_weight": 0.0, "decision": "HOLD"},
        ],
        "cash_weight": 0.5,
        "portfolio_mode": "mock",
    }

    result = RiskEngine().evaluate(portfolio)

    assert result["approved"] is True
    assert result["risk_flags"] == [{"code": "RISK_CHECK_PASSED", "message": "Mock portfolio risk check passed.", "severity": "INFO"}]
    assert result["adjusted_portfolio"] == portfolio
