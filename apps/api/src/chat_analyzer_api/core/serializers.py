from __future__ import annotations

from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd


def _to_python_scalar(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    return value


def _normalize(value: Any) -> Any:
    value = _to_python_scalar(value)

    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _normalize(v) for k, v in value.items()}
    return value


def dataframe_to_records(df: pd.DataFrame, include_index: bool = False, index_name: str | None = None) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []

    out = df.copy()
    if include_index:
        out = out.reset_index()
        if index_name and "index" in out.columns:
            out = out.rename(columns={"index": index_name})

    records = out.to_dict(orient="records")
    return [_normalize(record) for record in records]
