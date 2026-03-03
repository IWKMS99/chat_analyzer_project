from __future__ import annotations

from pathlib import Path

from chat_analyzer_api.db.connection import SQLiteConnectionFactory, connect_sqlite
from chat_analyzer_api.db.migrations import run_migrations
from chat_analyzer_api.db.repo import AnalysisRepository


def build_repo(db_path: Path) -> AnalysisRepository:
    run_migrations(str(db_path))
    return AnalysisRepository(SQLiteConnectionFactory(str(db_path)))


def assert_sqlite_pragmas(db_path: Path) -> tuple[str, int | str, int]:
    with connect_sqlite(str(db_path)) as conn:
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        synchronous = conn.execute("PRAGMA synchronous").fetchone()[0]
        busy_timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
    return str(journal_mode), synchronous, int(busy_timeout)
