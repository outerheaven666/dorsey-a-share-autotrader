from abc import ABC, abstractmethod

class BrokerAdapter(ABC):
    @abstractmethod
    def submit_order(self, order):
        pass