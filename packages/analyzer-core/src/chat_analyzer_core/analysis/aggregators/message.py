from collections import Counter, defaultdict
from typing import Dict

import pandas as pd

from .base import BaseAggregator
from .stats import hist_median, hist_quantile


class MessageAggregator(BaseAggregator):
    def __init__(self, length_threshold: int = 50):
        self.length_threshold = length_threshold
        self.length_hist = defaultdict(Counter)
        self.question_counts = Counter()
        self.total_counts = Counter()
        self.short_long_hourly = Counter()

    def update(self, chunk: pd.DataFrame) -> None:
        if chunk.empty:
            return
        for _, row in chunk[["from", "text_length", "text", "hour"]].iterrows():
            sender = str(row["from"])
            text_len = int(row["text_length"])
            text = str(row["text"])
            hour = int(row["hour"])

            self.length_hist[sender][text_len] += 1
            self.total_counts[sender] += 1
            if "?" in text:
                self.question_counts[sender] += 1

            msg_type = "short" if text_len <= self.length_threshold else "long"
            self.short_long_hourly[(hour, sender, msg_type)] += 1

    def result(self) -> Dict[str, pd.DataFrame]:
        length_rows = []
        for sender, hist in self.length_hist.items():
            total = sum(hist.values())
            if total <= 0:
                continue
            mean = sum(length * count for length, count in hist.items()) / total
            length_rows.append(
                {
                    "from": sender,
                    "mean": float(mean),
                    "median": hist_median(hist),
                    "p95": hist_quantile(hist, 0.95),
                }
            )
        lengths_df = pd.DataFrame(length_rows) if length_rows else pd.DataFrame()

        ratio_rows = []
        for sender, total in self.total_counts.items():
            q = self.question_counts.get(sender, 0)
            ratio_rows.append({"from": sender, "questions": q, "total": total, "ratio": q / max(total, 1)})
        ratios_df = pd.DataFrame(ratio_rows) if ratio_rows else pd.DataFrame()

        sl_rows = [(h, u, t, c) for (h, u, t), c in self.short_long_hourly.items()]
        sl_df = pd.DataFrame(sl_rows, columns=["hour", "from", "message_type", "count"]) if sl_rows else pd.DataFrame()

        return {"lengths": lengths_df, "question_ratio": ratios_df, "short_long_hourly": sl_df}
