from __future__ import annotations

import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status

_ANALYSIS_ID_RE = re.compile(r"^[a-f0-9]{32}$")
_MAX_TIMEZONE_LEN = 128


def validate_analysis_id(analysis_id: str) -> str:
    if not _ANALYSIS_ID_RE.fullmatch(analysis_id):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid analysis id format")
    return analysis_id


def normalize_timezone(timezone_name: str | None) -> str:
    candidate = (timezone_name or "UTC").strip() or "UTC"
    if len(candidate) > _MAX_TIMEZONE_LEN:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Timezone is too long")
    if "\x00" in candidate:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Timezone contains forbidden characters")

    try:
        ZoneInfo(candidate)
        return candidate
    except (ZoneInfoNotFoundError, ValueError):
        return "UTC"
