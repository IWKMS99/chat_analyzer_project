from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from chat_analyzer_api.db.connection import sqlite_path_to_url


REPO_ROOT = Path(__file__).resolve().parents[5]
ALEMBIC_INI = REPO_ROOT / "apps" / "api" / "alembic.ini"


def run_migrations(sqlite_path: str) -> None:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", sqlite_path_to_url(sqlite_path))
    command.upgrade(config, "head")
