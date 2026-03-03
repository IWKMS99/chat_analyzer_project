import pandas as pd

from .base import BaseAggregator
from .models import CoreStats


class SummaryAggregator(BaseAggregator):
    def __init__(self):
        self.total_messages = 0
        self.participants = set()
        self.start = None
        self.end = None

    def update(self, chunk: pd.DataFrame) -> None:
        if chunk.empty:
            return
        self.total_messages += len(chunk)
        self.participants.update(map(str, chunk["from"].astype(str).unique()))
        cmin = chunk["date"].min()
        cmax = chunk["date"].max()
        self.start = cmin if self.start is None else min(self.start, cmin)
        self.end = cmax if self.end is None else max(self.end, cmax)

    def result(self) -> CoreStats:
        return CoreStats(
            total_messages=self.total_messages,
            participants=len(self.participants),
            start=self.start,
            end=self.end,
        )
