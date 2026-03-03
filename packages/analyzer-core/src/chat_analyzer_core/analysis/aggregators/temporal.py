from collections import Counter
from typing import Dict

import pandas as pd

from .common import logger


class TemporalAggregator:
    def __init__(self, response_limit_minutes: float = 60.0, interval_limit_seconds: float = 3600.0):
        self.response_limit_minutes = response_limit_minutes
        self.interval_limit_seconds = interval_limit_seconds
        self.prev_sender = None
        self.prev_date = None
        self.response_hist = Counter()
        self.interval_hist = Counter()
        self.response_sum = 0.0
        self.response_count = 0
        self.daily_counts = Counter()
        self.out_of_order_count = 0

    def update(self, chunk: pd.DataFrame) -> None:
        if chunk.empty:
            return

        ordered = chunk.sort_values("date")
        for _, row in ordered[["from", "date", "date_only"]].iterrows():
            sender = str(row["from"])
            dt = pd.Timestamp(row["date"])
            self.daily_counts[str(row["date_only"])] += 1

            if self.prev_date is not None:
                if dt < self.prev_date:
                    self.out_of_order_count += 1
                    if self.out_of_order_count <= 3 or self.out_of_order_count % 1000 == 0:
                        logger.warning("Out-of-order message detected in TemporalAggregator: %s < %s", dt, self.prev_date)
                    self.prev_sender = sender
                    self.prev_date = dt
                    continue

                gap_sec = (dt - self.prev_date).total_seconds()
                if 0 < gap_sec <= self.interval_limit_seconds:
                    self.interval_hist[int(gap_sec)] += 1
                if sender != self.prev_sender:
                    gap_min = gap_sec / 60.0
                    if 0 < gap_min <= self.response_limit_minutes:
                        minute_bin = int(gap_min)
                        self.response_hist[minute_bin] += 1
                        self.response_sum += float(gap_min)
                        self.response_count += 1

            self.prev_sender = sender
            self.prev_date = dt

    def result(self) -> Dict[str, pd.DataFrame | float]:
        daily = pd.Series(self.daily_counts).sort_index()
        daily.index = pd.to_datetime(daily.index)
        avg_response = float(self.response_sum / self.response_count) if self.response_count else 0.0

        response_rows = [{"response_min": minute, "count": count} for minute, count in sorted(self.response_hist.items())]
        interval_rows = [{"interval_sec": sec, "count": count} for sec, count in sorted(self.interval_hist.items())]
        response_df = pd.DataFrame(response_rows) if response_rows else pd.DataFrame()
        interval_df = pd.DataFrame(interval_rows) if interval_rows else pd.DataFrame()
        daily_df = daily.rename("count").to_frame()
        return {
            "avg_response_min": avg_response,
            "response_df": response_df,
            "interval_df": interval_df,
            "daily_df": daily_df,
        }
