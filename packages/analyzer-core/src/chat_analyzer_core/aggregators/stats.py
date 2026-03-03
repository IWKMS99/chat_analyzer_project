import logging
from collections import Counter

import numpy as np

logger = logging.getLogger(__name__)


def hist_median(hist: Counter[int]) -> float:
    total = sum(hist.values())
    if total <= 0:
        return 0.0
    threshold = (total + 1) / 2.0
    running = 0
    for value in sorted(hist):
        running += hist[value]
        if running >= threshold:
            return float(value)
    return 0.0


def hist_quantile(hist: Counter[int], q: float) -> float:
    total = sum(hist.values())
    if total <= 0:
        return 0.0
    target = max(1, int(np.ceil(total * min(max(q, 0.0), 1.0))))
    running = 0
    for value in sorted(hist):
        running += hist[value]
        if running >= target:
            return float(value)
    return float(max(hist))
