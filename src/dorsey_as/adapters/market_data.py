from abc import ABC, abstractmethod

class MarketDataAdapter(ABC):
    @abstractmethod
    def get_bars(self, symbol, start, end, timeframe):
        pass