from __future__ import annotations

from abc import ABC, abstractmethod


class DataProvider(ABC):
    """Standard contract future data providers must satisfy."""

    name: str

    @abstractmethod
    def get_stock_basic(self) -> list[dict[str, str]]:
        raise NotImplementedError

    @abstractmethod
    def get_financial_snapshot(self) -> list[dict[str, str]]:
        raise NotImplementedError

    @abstractmethod
    def get_market_snapshot(self) -> list[dict[str, str]]:
        raise NotImplementedError

    @abstractmethod
    def get_historical_market_snapshot(self) -> list[dict[str, str]]:
        raise NotImplementedError

    @abstractmethod
    def get_trading_calendar(self) -> list[dict[str, str]]:
        raise NotImplementedError

