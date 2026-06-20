from pathlib import Path

from dorsey_as.ledger.replay import RuntimeReplayValidator
from dorsey_as.ledger.runtime_ledger import RuntimeLedger


def _runtime_result() -> dict:
    return {
        "market_data": [
            {"symbol": "600519.SH", "price": 101.0},
            {"symbol": "000001.SZ", "price": 99.0},
        ],
        "strategy_results": [
            {"symbol": "600519.SH", "decision": "BUY", "final_score": 0.4},
            {"symbol": "000001.SZ", "decision": "SELL", "final_score": -0.4},
        ],
        "portfolio": {
            "positions": [
                {"symbol": "600519.SH", "target_weight": 1.0, "decision": "BUY"},
                {"symbol": "000001.SZ", "target_weight": 0.0, "decision": "SELL"},
            ],
            "cash_weight": 0.0,
            "portfolio_mode": "mock",
        },
        "risk": {"approved": True, "risk_flags": [], "adjusted_portfolio": {}},
        "executions": [
            {"symbol": "600519.SH", "status": "filled"},
            {"symbol": "000001.SZ", "status": "filled"},
        ],
    }


def test_runtime_replay_returns_invalid_for_missing_files(tmp_path: Path) -> None:
    result = RuntimeReplayValidator().validate(
        json_path=tmp_path / "missing.json",
        csv_path=tmp_path / "missing.csv",
    )

    assert result["valid"] is False
    assert result["summary"] == {
        "symbols_checked": 0,
        "executions_checked": 0,
        "mode": "mock",
    }
    assert any(check["name"] == "json_file_exists" and not check["passed"] for check in result["checks"])
    assert any(check["name"] == "csv_file_exists" and not check["passed"] for check in result["checks"])


def test_runtime_replay_validates_written_runtime_ledger(tmp_path: Path) -> None:
    paths = RuntimeLedger().record(_runtime_result(), output_dir=tmp_path)

    result = RuntimeReplayValidator().validate(
        json_path=paths["json_path"],
        csv_path=paths["csv_path"],
    )

    assert result["valid"] is True
    assert result["summary"] == {
        "symbols_checked": 2,
        "executions_checked": 2,
        "mode": "mock",
    }
    assert all(check["passed"] for check in result["checks"])
