from __future__ import annotations

from dorsey_as.adapters.contracts import DataProvider
from dorsey_as.adapters.mock_provider import MockAShareProvider
from dorsey_as.config.models import AdapterContractConfig


def get_provider(name: str, config: AdapterContractConfig) -> DataProvider:
    if config.allow_network:
        raise ValueError("Network access is disabled for adapter contract validation.")
    if config.allow_real_provider:
        raise ValueError("Real providers are disabled for adapter contract validation.")
    if config.mode != "mock_only":
        raise ValueError("Adapter contract mode must be mock_only.")
    if name != "mock_a_share":
        raise ValueError("Only mock_a_share provider is available in this MVP.")
    return MockAShareProvider(config.fixture_dir)

