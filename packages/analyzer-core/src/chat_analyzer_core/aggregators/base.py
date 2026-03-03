from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class BaseAggregator(ABC):
    @abstractmethod
    def update(self, chunk: pd.DataFrame) -> None:
        raise NotImplementedError

    @abstractmethod
    def result(self) -> Any:
        raise NotImplementedError
