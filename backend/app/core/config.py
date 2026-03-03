from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_version: str
    debug: bool
    cors_origins: list[str]

    max_upload_bytes: int
    sqlite_path: str
    storage_base_dir: str

    task_workers: int
    task_ttl_seconds: int
    cleanup_interval_seconds: int

    rate_limit_requests: int
    rate_limit_window_seconds: int


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "chat-analyzer-api"),
        app_version=os.getenv("APP_VERSION", "2.0.0"),
        debug=_as_bool(os.getenv("DEBUG"), False),
        cors_origins=_split_csv(os.getenv("CORS_ORIGINS", "http://localhost:8080")),
        max_upload_bytes=_as_int(os.getenv("MAX_UPLOAD_BYTES"), 100 * 1024 * 1024),
        sqlite_path=os.getenv("SQLITE_PATH", "backend_data/analyses.db"),
        storage_base_dir=os.getenv("STORAGE_BASE_DIR", "backend_data"),
        task_workers=max(1, min(_as_int(os.getenv("TASK_WORKERS"), 1), 4)),
        task_ttl_seconds=_as_int(os.getenv("TASK_TTL_SECONDS"), 604_800),
        cleanup_interval_seconds=_as_int(os.getenv("CLEANUP_INTERVAL_SECONDS"), 600),
        rate_limit_requests=_as_int(os.getenv("RATE_LIMIT_REQUESTS"), 120),
        rate_limit_window_seconds=_as_int(os.getenv("RATE_LIMIT_WINDOW_SECONDS"), 60),
    )
