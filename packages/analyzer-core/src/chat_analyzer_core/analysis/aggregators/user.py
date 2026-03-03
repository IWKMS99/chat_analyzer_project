from collections import Counter, defaultdict
from typing import Dict

import pandas as pd

from .base import BaseAggregator
from .stats import hist_median, logger


class UserAggregator(BaseAggregator):
    def __init__(self):
        self.message_counts = Counter()
        self.sum_text_len = Counter()
        self.chain_hist = defaultdict(Counter)
        self.chain_sum = Counter()
        self.chain_count = Counter()
        self.chain_max = Counter()
        self._prev_sender = None
        self._prev_date = None
        self._current_chain_len = 0
        self._daily_by_user = Counter()
        self._out_of_order = 0

    def _record_chain(self, sender: str, length: int) -> None:
        if not sender or length <= 0:
            return
        self.chain_hist[sender][int(length)] += 1
        self.chain_sum[sender] += int(length)
        self.chain_count[sender] += 1
        self.chain_max[sender] = max(self.chain_max[sender], int(length))

    def update(self, chunk: pd.DataFrame) -> None:
        if chunk.empty:
            return
        ordered = chunk.sort_values("date")
        for _, row in ordered[["from", "text_length", "date_only", "date"]].iterrows():
            sender = str(row["from"])
            dt = pd.Timestamp(row["date"])
            self.message_counts[sender] += 1
            self.sum_text_len[sender] += int(row["text_length"])
            self._daily_by_user[(str(row["date_only"]), sender)] += 1

            if self._prev_date is not None and dt < self._prev_date:
                self._out_of_order += 1
                if self._out_of_order <= 3 or self._out_of_order % 1000 == 0:
                    logger.warning("Out-of-order message detected in UserAggregator: %s < %s", dt, self._prev_date)
                self._record_chain(self._prev_sender, self._current_chain_len)
                self._prev_sender = sender
                self._current_chain_len = 1
                self._prev_date = dt
                continue

            if self._prev_sender is None:
                self._prev_sender = sender
                self._current_chain_len = 1
            elif self._prev_sender == sender:
                self._current_chain_len += 1
            else:
                self._record_chain(self._prev_sender, self._current_chain_len)
                self._prev_sender = sender
                self._current_chain_len = 1
            self._prev_date = dt

    def finalize(self) -> None:
        if self._prev_sender is not None and self._current_chain_len > 0:
            self._record_chain(self._prev_sender, self._current_chain_len)
            self._current_chain_len = 0

    def result(self) -> Dict[str, pd.DataFrame | Dict[str, float]]:
        self.finalize()
        counts = pd.Series(dict(self.message_counts), name="count").sort_values(ascending=False)
        avg_len = {
            user: (self.sum_text_len[user] / cnt if cnt else 0.0)
            for user, cnt in self.message_counts.items()
        }
        avg_len_series = pd.Series(avg_len, name="avg_text_length").sort_values(ascending=False)

        chains_rows = []
        for user, ccount in self.chain_count.items():
            if ccount <= 0:
                continue
            hist = self.chain_hist[user]
            chains_rows.append(
                {
                    "from": user,
                    "avg_chain": float(self.chain_sum[user] / ccount),
                    "median_chain": hist_median(hist),
                    "max_chain": int(self.chain_max[user]),
                    "chains": int(ccount),
                }
            )
        chains_df = pd.DataFrame(chains_rows).sort_values("chains", ascending=False) if chains_rows else pd.DataFrame()

        day_rows = [(d, u, c) for (d, u), c in self._daily_by_user.items()]
        daily_df = pd.DataFrame(day_rows, columns=["date_only", "from", "count"]) if day_rows else pd.DataFrame()
        return {
            "message_counts": counts,
            "avg_length": avg_len_series,
            "chains": chains_df,
            "daily_by_user": daily_df,
        }
