from __future__ import annotations

import asyncio
from pathlib import Path

from chat_analyzer_api.storage.file_storage import FileStorage
from chat_analyzer_api.workers.task_queue import TaskRunner

from apps.api.tests.helpers import build_repo


def test_cleanup_expired_removes_files_and_rows(tmp_path: Path):
    repo = build_repo(tmp_path / "analyses.db")
    storage = FileStorage(str(tmp_path / "storage"))

    created = repo.create_analysis(
        analysis_id="expired",
        timezone_name="UTC",
        upload_path="uploads/expired.json",
        ttl_seconds=-1,
    )
    storage.write_json(created["upload_path"], {"messages": []})

    result_path = "results/expired.json"
    storage.write_json(result_path, {"analysis_id": "expired", "summary": {}, "tabs": [], "widgets": [], "datasets": {}, "metadata": {}})
    repo.update_analysis("expired", result_path=result_path)

    runner = TaskRunner(repo=repo, storage=storage, workers=1, cleanup_interval_seconds=600)
    runner._cleanup_expired()

    assert repo.get_analysis("expired") is None
    assert storage.exists("uploads/expired.json") is False
    assert storage.exists(result_path) is False


def test_task_runner_stop_without_jobs(tmp_path: Path):
    repo = build_repo(tmp_path / "analyses.db")
    storage = FileStorage(str(tmp_path / "storage"))
    runner = TaskRunner(repo=repo, storage=storage, workers=2, cleanup_interval_seconds=600)

    async def _run() -> None:
        await runner.start()
        await runner.stop()

    asyncio.run(_run())
