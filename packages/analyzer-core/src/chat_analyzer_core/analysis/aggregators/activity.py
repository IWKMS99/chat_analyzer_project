from collections import Counter
from typing import Dict

import pandas as pd

from .base import BaseAggregator


class ActivityAggregator(BaseAggregator):
    def __init__(self):
        self.hourly = Counter()
        self.weekday = Counter()
        self.monthly = Counter()
        self.periods = Counter()

    def update(self, chunk: pd.DataFrame) -> None:
        if chunk.empty:
            return
        for _, row in chunk[["hour", "from", "day_of_week", "date"]].iterrows():
            sender = str(row["from"])
            hour = int(row["hour"])
            day = str(row["day_of_week"])
            month = pd.Timestamp(row["date"]).strftime("%Y-%m")
            self.hourly[(hour, sender)] += 1
            self.weekday[(day, sender)] += 1
            self.monthly[(month, sender)] += 1
            if 5 <= hour < 12:
                period = "morning"
            elif 12 <= hour < 18:
                period = "day"
            elif 18 <= hour < 24:
                period = "evening"
            else:
                period = "night"
            self.periods[(period, sender)] += 1

    def result(self) -> Dict[str, pd.DataFrame]:
        def _pivot(counter, idx, col):
            if not counter:
                return pd.DataFrame()
            df = pd.DataFrame([(k[0], k[1], v) for k, v in counter.items()], columns=[idx, col, "count"])
            return df.pivot(index=idx, columns=col, values="count").fillna(0)

        return {
            "hourly": _pivot(self.hourly, "hour", "from").reindex(range(24), fill_value=0),
            "weekday": _pivot(self.weekday, "day_of_week", "from"),
            "monthly": _pivot(self.monthly, "month", "from"),
            "periods": _pivot(self.periods, "period", "from"),
        }
