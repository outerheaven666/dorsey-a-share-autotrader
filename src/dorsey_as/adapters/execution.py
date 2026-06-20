from abc import ABC, abstractmethod

class ExecutionAdapter(ABC):
    @abstractmethod
    def fill_order(self, order):
        pass