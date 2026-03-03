from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class CoreStats:
    total_messages: int
    participants: int
    start: pd.Timestamp | None
    end: pd.Timestamp | None
