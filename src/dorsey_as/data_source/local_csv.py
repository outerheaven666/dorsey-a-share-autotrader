from __future__ import annotations

from pathlib import Path

from dorsey_as.config.models import DataSourceConfig
from dorsey_as.data_source.base import DataSource


class LocalCsvDataSource(DataSource):
    def __init__(self, config: DataSourceConfig) -> None:
        if config.mode != "local_csv" or config.allow_network:
            raise ValueError("MVP data source only supports local_csv with allow_network=false")
        self.config = config

    def files(self) -> dict[str, Path]:
        return {
            "stock_basic": Path(self.config.stock_basic_path),
            "financial_snapshot": Path(self.config.financial_snapshot_path),
            "market_snapshot": Path(self.config.market_snapshot_path),
            "historical_market_snapshot": Path(self.config.historical_market_snapshot_path),
            "trading_calendar": Path(self.config.trading_calendar_path),
        }

    def describe(self) -> dict[str, str]:
        return {
            "mode": self.config.mode,
            "provider": self.config.provider,
            "allow_network": str(self.config.allow_network),
            "require_point_in_time": str(self.config.require_point_in_time),
            "require_disclosure_date": str(self.config.require_disclosure_date),
        }
