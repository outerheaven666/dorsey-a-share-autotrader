from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class DataSource(ABC):
    @abstractmethod
    def files(self) -> dict[str, Path]:
        raise NotImplementedError

    @abstractmethod
    def describe(self) -> dict[str, str]:
        raise NotImplementedError
