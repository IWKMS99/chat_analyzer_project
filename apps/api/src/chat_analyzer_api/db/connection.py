from __future__ import annotations

import os
import sqlite3
from pathlib import Path


class SQLiteConnectionFactory:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def __call__(self) -> sqlite3.Connection:
        return connect_sqlite(self.db_path)


def connect_sqlite(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def sqlite_path_to_url(db_path: str) -> str:
    path = Path(db_path).resolve()
    return f"sqlite:///{path}"
