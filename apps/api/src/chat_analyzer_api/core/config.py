from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", enable_decoding=False)

    app_name: str = "chat-analyzer-api"
    app_version: str = "2.0.0"
    debug: bool = False
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:8080"])

    max_upload_bytes: int = 100 * 1024 * 1024
    sqlite_path: str = "backend_data/analyses.db"
    storage_base_dir: str = "backend_data"

    task_workers: int = 1
    task_ttl_seconds: int = 604_800
    cleanup_interval_seconds: int = 600

    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: str | list[str] | None) -> list[str]:
        if value is None:
            return ["http://localhost:8080"]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("debug", mode="before")
    @classmethod
    def _parse_debug_flag(cls, value: bool | str | None) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    @field_validator("max_upload_bytes", "task_ttl_seconds", "cleanup_interval_seconds", "rate_limit_requests", "rate_limit_window_seconds")
    @classmethod
    def _validate_positive_ints(cls, value: int) -> int:
        return max(1, value)

    @field_validator("task_workers")
    @classmethod
    def _validate_task_workers(cls, value: int) -> int:
        return max(1, min(value, 4))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
