from __future__ import annotations

import csv
from pathlib import Path

from dorsey_as.adapters.contracts import DataProvider


class MockAShareProvider(DataProvider):
    """Fixture-backed provider used only for contract tests."""

    name = "mock_a_share"

    def __init__(self, fixture_dir: str | Path) -> None:
        self.fixture_dir = Path(fixture_dir)

    def _read(self, filename: str) -> list[dict[str, str]]:
        path = self.fixture_dir / filename
        with path.open(newline="", encoding="utf-8-sig") as fh:
            return list(csv.DictReader(fh))

    def get_stock_basic(self) -> list[dict[str, str]]:
        return self._read("stock_basic_raw.csv")

    def get_financial_snapshot(self) -> list[dict[str, str]]:
        return self._read("financial_snapshot_raw.csv")

    def get_market_snapshot(self) -> list[dict[str, str]]:
        return self._read("market_snapshot_raw.csv")

    def get_historical_market_snapshot(self) -> list[dict[str, str]]:
        return self._read("historical_market_snapshot_raw.csv")

    def get_trading_calendar(self) -> list[dict[str, str]]:
        return self._read("trading_calendar_raw.csv")

