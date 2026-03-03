from __future__ import annotations

import asyncio
import os
import tempfile

from backend.app.db.repo import (
    PHASE_ANALYZING,
    PHASE_DONE,
    PHASE_FAILED,
    PHASE_PARSING,
    PHASE_SERIALIZING,
    PHASE_STORING,
    STATUS_DONE,
    STATUS_FAILED,
    STATUS_RUNNING,
    AnalysisRepository,
)
from backend.app.services.analyzer import analyze_chat_file
from backend.app.services.dashboard_builder import build_dashboard_payload
from backend.app.storage.base import StorageBackend

_SHUTDOWN_SENTINEL = "__shutdown__"


class TaskRunner:
    def __init__(
        self,
        repo: AnalysisRepository,
        storage: StorageBackend,
        workers: int,
        cleanup_interval_seconds: int,
    ):
        self.repo = repo
        self.storage = storage
        self.workers = max(1, min(workers, 4))
        self.cleanup_interval_seconds = cleanup_interval_seconds

        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._worker_tasks: list[asyncio.Task] = []
        self._cleanup_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        self._stop_event.clear()
        self._worker_tasks = [
            asyncio.create_task(self._worker_loop(worker_idx), name=f"analysis-worker-{worker_idx}")
            for worker_idx in range(self.workers)
        ]
        self._cleanup_task = asyncio.create_task(self._cleanup_loop(), name="analysis-cleanup")

    async def stop(self) -> None:
        self._stop_event.set()

        for _ in self._worker_tasks:
            await self._queue.put(_SHUTDOWN_SENTINEL)

        try:
            await asyncio.wait_for(self._queue.join(), timeout=30)
        except asyncio.TimeoutError:
            for task in self._worker_tasks:
                task.cancel()

        await asyncio.gather(*self._worker_tasks, return_exceptions=True)

        if self._cleanup_task:
            self._cleanup_task.cancel()
            await asyncio.gather(self._cleanup_task, return_exceptions=True)

    async def enqueue(self, analysis_id: str) -> None:
        await self._queue.put(analysis_id)

    async def _worker_loop(self, worker_idx: int) -> None:  # noqa: ARG002
        while True:
            try:
                analysis_id = await self._queue.get()
            except asyncio.CancelledError:
                break

            try:
                if analysis_id == _SHUTDOWN_SENTINEL:
                    return
                await asyncio.to_thread(self._run_analysis_sync, analysis_id)
            finally:
                self._queue.task_done()

    def _run_analysis_sync(self, analysis_id: str) -> None:
        analysis = self.repo.get_analysis(analysis_id)
        if analysis is None:
            return

        temp_file_path: str | None = None
        try:
            self.repo.update_analysis(
                analysis_id,
                status=STATUS_RUNNING,
                phase=PHASE_PARSING,
                progress_pct=5,
                eta_sec=None,
            )

            with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
                temp_file_path = tmp.name
            self.storage.download_to_file(analysis["upload_path"], temp_file_path)

            def on_progress(phase: str, progress_pct: int, eta_sec: int | None) -> None:
                normalized_phase = _normalize_phase(phase)
                self.repo.update_analysis(
                    analysis_id,
                    status=STATUS_RUNNING,
                    phase=normalized_phase,
                    progress_pct=max(0, min(progress_pct, 100)),
                    eta_sec=eta_sec,
                )

            self.repo.update_analysis(
                analysis_id,
                status=STATUS_RUNNING,
                phase=PHASE_ANALYZING,
                progress_pct=10,
                eta_sec=None,
            )
            analysis_result = analyze_chat_file(temp_file_path, analysis["timezone"], progress_hook=on_progress)
            dashboard = build_dashboard_payload(analysis_id=analysis_id, analysis_result=analysis_result)

            self.repo.update_analysis(
                analysis_id,
                status=STATUS_RUNNING,
                phase=PHASE_STORING,
                progress_pct=97,
                eta_sec=0,
            )
            result_path = f"results/{analysis_id}.json"
            self.storage.write_json(result_path, dashboard)

            warnings = dashboard.get("metadata", {}).get("warnings", [])
            self.repo.update_analysis(
                analysis_id,
                status=STATUS_DONE,
                phase=PHASE_DONE,
                progress_pct=100,
                eta_sec=0,
                result_path=result_path,
                error_code=None,
                error_message=None,
            )
            self.repo.set_warnings(analysis_id, list(warnings) if isinstance(warnings, list) else [])

        except Exception as exc:  # pragma: no cover - runtime safety
            self.repo.update_analysis(
                analysis_id,
                status=STATUS_FAILED,
                phase=PHASE_FAILED,
                error_code=type(exc).__name__,
                error_message=str(exc)[:1000],
            )
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    async def _cleanup_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.cleanup_interval_seconds)
            except asyncio.TimeoutError:
                await asyncio.to_thread(self._cleanup_expired)

    def _cleanup_expired(self) -> None:
        expired = self.repo.list_expired_analyses()
        for row in expired:
            self.storage.remove_path(row.get("upload_path"))
            self.storage.remove_path(row.get("result_path"))
            self.repo.delete_analysis(row["id"])


def _normalize_phase(phase: str) -> str:
    if phase == PHASE_PARSING:
        return PHASE_PARSING
    if phase == PHASE_ANALYZING:
        return PHASE_ANALYZING
    if phase == PHASE_SERIALIZING:
        return PHASE_SERIALIZING
    return PHASE_ANALYZING
