from collections import Counter
from typing import Dict

import numpy as np
import pandas as pd

from .base import BaseAggregator


class AnomalyAggregator(BaseAggregator):
    def __init__(self, threshold: float = 2.0, mode: str = "robust"):
        self.threshold = threshold
        self.mode = mode
        self.daily_counts = Counter()

    def update(self, chunk: pd.DataFrame) -> None:
        if chunk.empty:
            return
        day_counts = chunk.groupby("date_only").size()
        for day, count in day_counts.items():
            self.daily_counts[str(day)] += int(count)

    def result(self) -> Dict[str, pd.DataFrame | Dict[str, float | int | str]]:
        if not self.daily_counts:
            return {"daily": pd.DataFrame(), "anomalies": pd.DataFrame(), "metrics": {"mode": self.mode, "threshold": self.threshold}}

        daily = pd.Series(self.daily_counts).sort_index().astype(float)
        daily.index = pd.to_datetime(daily.index)
        df = daily.rename("count").to_frame()
        values = df["count"].values

        robust_score = np.zeros_like(values)
        median = float(np.median(values))
        mad = float(np.median(np.abs(values - median)))
        if mad > 0:
            robust_score = 0.6745 * (values - median) / mad

        zscore = np.zeros_like(values)
        std = float(np.std(values))
        mean = float(np.mean(values))
        if std > 0:
            zscore = (values - mean) / std

        out = df.copy()
        out["robust_score"] = robust_score
        out["zscore"] = zscore

        if self.mode == "robust":
            anomalies = out[np.abs(out["robust_score"]) >= self.threshold]
        elif self.mode == "zscore":
            anomalies = out[np.abs(out["zscore"]) >= self.threshold]
        else:
            anomalies = out[(np.abs(out["robust_score"]) >= self.threshold) | (np.abs(out["zscore"]) >= self.threshold)]

        metrics = {
            "mode": self.mode,
            "threshold": self.threshold,
            "robust_count": int((np.abs(out["robust_score"]) >= self.threshold).sum()),
            "zscore_count": int((np.abs(out["zscore"]) >= self.threshold).sum()),
        }
        return {"daily": out, "anomalies": anomalies, "metrics": metrics}
