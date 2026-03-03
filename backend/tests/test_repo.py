from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.db.repo import AnalysisRepository, STATUS_FAILED, STATUS_QUEUED


def test_repo_create_and_get_analysis(tmp_path: Path):
    repo = AnalysisRepository(str(tmp_path / "analyses.db"))
    repo.init_db()

    created = repo.create_analysis(
        analysis_id="a1",
        timezone_name="UTC",
        upload_path="uploads/a1.json",
        ttl_seconds=3600,
    )

    assert created["status"] == STATUS_QUEUED

    row = repo.get_analysis("a1")
    assert row is not None
    assert row["id"] == "a1"
    assert row["upload_path"] == "uploads/a1.json"


def test_repo_updates_and_lists_recent(tmp_path: Path):
    repo = AnalysisRepository(str(tmp_path / "analyses.db"))
    repo.init_db()
    repo.create_analysis("a1", "UTC", "uploads/a1.json", 3600)
    repo.create_analysis("a2", "UTC", "uploads/a2.json", 3600)

    repo.update_analysis("a1", status="running", phase="analyzing", progress_pct=50)
    repo.set_warnings("a1", ["warn"])

    recent = repo.list_recent_analyses(limit=10)
    assert len(recent) == 2

    row = repo.get_analysis("a1")
    assert row is not None
    assert row["warnings"] == ["warn"]


def test_repo_mark_running_as_failed(tmp_path: Path):
    repo = AnalysisRepository(str(tmp_path / "analyses.db"))
    repo.init_db()
    repo.create_analysis("a1", "UTC", "uploads/a1.json", 3600)
    repo.update_analysis("a1", status="running", phase="analyzing", progress_pct=50)

    repo.mark_running_as_failed()
    row = repo.get_analysis("a1")

    assert row is not None
    assert row["status"] == STATUS_FAILED
    assert row["phase"] == "failed"
    assert row["error_code"] == "restart_interrupted"


def test_repo_expired_and_delete(tmp_path: Path):
    repo = AnalysisRepository(str(tmp_path / "analyses.db"))
    repo.init_db()
    repo.create_analysis("a1", "UTC", "uploads/a1.json", ttl_seconds=-1)

    expired = repo.list_expired_analyses()
    assert any(item["id"] == "a1" for item in expired)

    repo.delete_analysis("a1")
    assert repo.get_analysis("a1") is None


def test_repo_update_analysis_rejects_unknown_fields(tmp_path: Path):
    repo = AnalysisRepository(str(tmp_path / "analyses.db"))
    repo.init_db()
    repo.create_analysis("a1", "UTC", "uploads/a1.json", 3600)

    with pytest.raises(ValueError):
        repo.update_analysis("a1", something_unexpected="x")


def test_repo_uses_wal_and_busy_timeout(tmp_path: Path):
    repo = AnalysisRepository(str(tmp_path / "analyses.db"))
    repo.init_db()

    with repo._connect() as conn:
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        synchronous = conn.execute("PRAGMA synchronous").fetchone()[0]
        busy_timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]

    assert str(journal_mode).lower() == "wal"
    assert synchronous in (1, "1", "normal", "NORMAL")
    assert int(busy_timeout) == 5000
