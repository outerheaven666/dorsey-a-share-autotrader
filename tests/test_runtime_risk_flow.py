from dorsey_as.engine.runtime import RuntimeEngine


def test_runtime_output_contains_risk_section() -> None:
    result = RuntimeEngine().run_once(print_output=False)

    for key in ["market_data", "strategy_results", "portfolio", "risk", "executions"]:
        assert key in result
    assert result["risk"]["approved"] is True
    assert result["risk"]["adjusted_portfolio"]["portfolio_mode"] == "mock"


def test_runtime_uses_adjusted_risk_portfolio() -> None:
    result = RuntimeEngine().run_once(print_output=False)

    buy_position = next(row for row in result["risk"]["adjusted_portfolio"]["positions"] if row["symbol"] == "600519.SH")
    assert buy_position["target_weight"] == 0.6
    assert result["risk"]["adjusted_portfolio"]["cash_weight"] == 0.4
    assert any(flag["code"] == "MAX_SINGLE_POSITION_CAPPED" for flag in result["risk"]["risk_flags"])


class BlockingPortfolioEngine:
    def evaluate(self, strategy_results):
        return {
            "positions": [
                {"symbol": "600519.SH", "target_weight": 0.7, "decision": "BUY"},
                {"symbol": "000001.SZ", "target_weight": 0.7, "decision": "BUY"},
            ],
            "cash_weight": 0.0,
            "portfolio_mode": "mock",
        }


def test_runtime_blocks_executions_when_risk_not_approved() -> None:
    result = RuntimeEngine(portfolio_engine=BlockingPortfolioEngine()).run_once(print_output=False)

    assert result["risk"]["approved"] is False
    assert result["executions"] == []
