from __future__ import annotations

from typing import Callable, TypeVar

from fastapi import FastAPI

from chat_analyzer_api.core.config import Settings
from chat_analyzer_api.db.repo import AnalysisRepository
from chat_analyzer_api.storage.base import StorageBackend
from chat_analyzer_api.workers.task_queue import TaskRunner

_T = TypeVar("_T")


def get_settings() -> Settings:
    raise RuntimeError("Settings dependency is not configured")


def get_repo() -> AnalysisRepository:
    raise RuntimeError("Repository dependency is not configured")


def get_storage() -> StorageBackend:
    raise RuntimeError("Storage dependency is not configured")


def get_task_runner() -> TaskRunner:
    raise RuntimeError("Task runner dependency is not configured")


def configure_runtime_dependencies(
    app: FastAPI,
    *,
    settings: Settings,
    repo: AnalysisRepository,
    storage: StorageBackend,
    task_runner: TaskRunner,
) -> None:
    app.dependency_overrides[get_settings] = _constant_provider(settings)
    app.dependency_overrides[get_repo] = _constant_provider(repo)
    app.dependency_overrides[get_storage] = _constant_provider(storage)
    app.dependency_overrides[get_task_runner] = _constant_provider(task_runner)


def clear_runtime_dependencies(app: FastAPI) -> None:
    app.dependency_overrides.pop(get_settings, None)
    app.dependency_overrides.pop(get_repo, None)
    app.dependency_overrides.pop(get_storage, None)
    app.dependency_overrides.pop(get_task_runner, None)


def _constant_provider(value: _T) -> Callable[[], _T]:
    def _provider() -> _T:
        return value

    return _provider
