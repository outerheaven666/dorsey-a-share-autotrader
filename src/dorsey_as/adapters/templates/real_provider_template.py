"""Disabled-by-default, non-executable provider template.

This file is documentation-oriented scaffolding only.
Do not connect to real providers.
Do not import real provider SDKs.
Do not add credentials, endpoints, or live trading paths.
The active provider registry must not register this template.
"""

from __future__ import annotations


class DisabledRealProviderTemplate:
    """Non-executable template showing the shape a future adapter must satisfy."""

    enabled = False
    non_executable_template = True

    def __init__(self) -> None:
        raise RuntimeError("Disabled by default: this non-executable template must not be instantiated.")

    def get_stock_basic(self):
        raise NotImplementedError("Template only.")

    def get_financial_snapshot(self):
        raise NotImplementedError("Template only.")

    def get_market_snapshot(self):
        raise NotImplementedError("Template only.")

    def get_historical_market_snapshot(self):
        raise NotImplementedError("Template only.")

    def get_trading_calendar(self):
        raise NotImplementedError("Template only.")
