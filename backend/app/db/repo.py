from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from typing import Any


STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_DONE = "done"
STATUS_FAILED = "failed"

PHASE_PARSING = "parsing"
PHASE_ANALYZING = "analyzing"
PHASE_SERIALIZING = "serializing"
PHASE_STORING = "storing"
PHASE_DONE = "done"
PHASE_FAILED = "failed"

_MUTABLE_COLUMNS = {
    "status",
    "phase",
    "progress_pct",
    "eta_sec",
    "timezone",
    "expires_at",
    "upload_path",
    "result_path",
    "warnings_json",
    "error_code",
    "error_message",
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utcnow().isoformat()


class AnalysisRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def init_db(self) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analyses (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    progress_pct INTEGER NOT NULL,
                    eta_sec INTEGER,
                    timezone TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    upload_path TEXT NOT NULL,
                    result_path TEXT,
                    warnings_json TEXT NOT NULL,
                    error_code TEXT,
                    error_message TEXT
                )
                """
            )

    def create_analysis(self, analysis_id: str, timezone_name: str, upload_path: str, ttl_seconds: int) -> dict[str, Any]:
        created_at = utcnow()
        expires_at = created_at + timedelta(seconds=ttl_seconds)
        payload = {
            "id": analysis_id,
            "status": STATUS_QUEUED,
            "phase": PHASE_PARSING,
            "progress_pct": 0,
            "eta_sec": None,
            "timezone": timezone_name,
            "created_at": created_at.isoformat(),
            "updated_at": created_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "upload_path": upload_path,
            "result_path": None,
            "warnings_json": json.dumps([], ensure_ascii=False),
            "error_code": None,
            "error_message": None,
        }
        with closing(self._connect()) as conn, conn:
            conn.execute(
                """
                INSERT INTO analyses (
                    id, status, phase, progress_pct, eta_sec, timezone,
                    created_at, updated_at, expires_at, upload_path,
                    result_path, warnings_json, error_code, error_message
                ) VALUES (
                    :id, :status, :phase, :progress_pct, :eta_sec, :timezone,
                    :created_at, :updated_at, :expires_at, :upload_path,
                    :result_path, :warnings_json, :error_code, :error_message
                )
                """,
                payload,
            )
        return payload

    def get_analysis(self, analysis_id: str) -> dict[str, Any] | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)

    def update_analysis(self, analysis_id: str, **fields: Any) -> None:
        if not fields:
            return

        unknown = [key for key in fields if key not in _MUTABLE_COLUMNS]
        if unknown:
            raise ValueError(f"Unsupported analysis fields for update: {', '.join(sorted(unknown))}")

        fields = dict(fields)
        fields["updated_at"] = iso_now()
        assignments = ", ".join([f"{key} = :{key}" for key in fields])
        fields["analysis_id"] = analysis_id
        with closing(self._connect()) as conn, conn:
            conn.execute(f"UPDATE analyses SET {assignments} WHERE id = :analysis_id", fields)

    def set_warnings(self, analysis_id: str, warnings: list[str]) -> None:
        self.update_analysis(analysis_id, warnings_json=json.dumps(warnings, ensure_ascii=False))

    def mark_running_as_failed(self) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute(
                """
                UPDATE analyses
                SET status = ?, phase = ?, error_code = ?, error_message = ?, updated_at = ?
                WHERE status = ?
                """,
                (
                    STATUS_FAILED,
                    PHASE_FAILED,
                    "restart_interrupted",
                    "Analysis was interrupted by service restart",
                    iso_now(),
                    STATUS_RUNNING,
                ),
            )

    def list_recent_analyses(self, limit: int = 20) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 200))
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM analyses ORDER BY created_at DESC LIMIT ?",
                (safe_limit,),
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def list_expired_analyses(self, now_iso: str | None = None) -> list[dict[str, Any]]:
        compare = now_iso or iso_now()
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT * FROM analyses WHERE expires_at <= ?", (compare,)).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def delete_analysis(self, analysis_id: str) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))

    def healthcheck(self) -> bool:
        try:
            with closing(self._connect()) as conn:
                conn.execute("SELECT 1")
            return True
        except sqlite3.Error:
            return False

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        try:
            data["warnings"] = json.loads(data.pop("warnings_json") or "[]")
        except json.JSONDecodeError:
            data["warnings"] = []
        return data
