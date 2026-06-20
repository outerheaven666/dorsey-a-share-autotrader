from dorsey_as.adapters.plugin_registry import AdapterPluginRegistry
from dorsey_as.adapters.mock_provider import MockAShareProvider
from dorsey_as.config.loader import load_config
from dorsey_as.engine.runtime import RuntimeEngine
from dorsey_as.engine.signal_engine import SignalEngine


class SystemBootstrap:
    def __init__(self, config_path: str):
        self.config = load_config(config_path)
        self.plugin_registry = AdapterPluginRegistry()
        self.provider = None

    def initialize(self):
        self._init_provider()
        self._init_plugins()
        self._run_safety_check()
        return self

    def _init_provider(self):
        fixture_dir = getattr(self.config, "fixture_dir", None)
        if not fixture_dir:
            fixture_dir = "data/fixtures"

        self.provider = MockAShareProvider(fixture_dir)

    def _init_plugins(self):
        from dorsey_as.adapters import broker, execution, market_data

        self.plugin_registry.auto_discover(broker)
        self.plugin_registry.auto_discover(execution)
        self.plugin_registry.auto_discover(market_data)

    def _run_safety_check(self):
        """
        ⚠️ 修复点：
        不再扫描 config 字符串（会误杀 false / 注释 / key 名）
        只检查“明确允许 real trading 的开关”
        """

        allow_real = getattr(self.config, "allow_real_broker", False)

        if allow_real:
            raise RuntimeError("Safety violation: real broker explicitly enabled")

        # 只做关键词“提示级检查”，不再直接 fail
        text = str(self.config)

        suspicious_keywords = [
            "qmt_live",
            "ibkr_live",
            "order_execution_live"
        ]

        for w in suspicious_keywords:
            if w in text:
                print(f"[WARN] suspicious config keyword detected: {w}")

    def run_dry(self):
        print("[BOOTSTRAP] OK - mock-only system started")
        print("[BOOTSTRAP] plugins loaded")
        print("[BOOTSTRAP] safety check passed")
        RuntimeEngine(signal_engine=SignalEngine()).run_once()


def main():
    SystemBootstrap("config/default.yaml").initialize().run_dry()


if __name__ == "__main__":
    main()
