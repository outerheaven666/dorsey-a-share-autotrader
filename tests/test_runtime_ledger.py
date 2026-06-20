import csv
import json
from pathlib import Path

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


def test_runtime_ledger_writes_json(tmp_path: Path) -> None:
    paths = RuntimeLedger().record(_runtime_result(), output_dir=tmp_path)

    payload = json.loads((tmp_path / "runtime_ledger_latest.json").read_text(encoding="utf-8"))
    assert paths["json_path"] == str(tmp_path / "runtime_ledger_latest.json")
    assert payload["run_id"] == "mock-runtime-run"
    assert payload["mode"] == "mock"
    assert payload["runtime_result"]["risk"]["approved"] is True


def test_runtime_ledger_writes_csv_one_row_per_symbol(tmp_path: Path) -> None:
    paths = RuntimeLedger().record(_runtime_result(), output_dir=tmp_path)

    with (tmp_path / "runtime_ledger_latest.csv").open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert paths["csv_path"] == str(tmp_path / "runtime_ledger_latest.csv")
    assert len(rows) == 2
    assert rows[0]["run_id"] == "mock-runtime-run"
    assert rows[0]["symbol"] == "600519.SH"
    assert rows[0]["price"] == "101.0"
    assert rows[0]["decision"] == "BUY"
    assert rows[0]["final_score"] == "0.4"
    assert rows[0]["target_weight"] == "1.0"
    assert rows[0]["risk_approved"] == "True"
    assert rows[0]["execution_status"] == "filled"
