from __future__ import annotations

from typing import Any


RUNTIME_SCENARIOS: list[dict[str, Any]] = [
    {
        "name": "baseline_mixed",
        "market_data": [
            {"symbol": "600519.SH", "price": 101.0},
            {"symbol": "000001.SZ", "price": 99.0},
            {"symbol": "300750.SZ", "price": 100.0},
        ],
    },
    {
        "name": "all_hold",
        "market_data": [
            {"symbol": "600519.SH", "price": 100.0},
            {"symbol": "000001.SZ", "price": 100.0},
        ],
    },
    {
        "name": "buy_single_cap",
        "market_data": [
            {"symbol": "600519.SH", "price": 101.0},
        ],
    },
    {
        "name": "sell_path",
        "market_data": [
            {"symbol": "000001.SZ", "price": 99.0},
        ],
    },
]
