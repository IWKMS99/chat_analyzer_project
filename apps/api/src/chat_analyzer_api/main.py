from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from chat_analyzer_api.api.dependencies import clear_runtime_dependencies, configure_runtime_dependencies
from chat_analyzer_api.api.router import router as analyses_router
from chat_analyzer_api.core.config import get_settings as load_settings
from chat_analyzer_api.db.connection import SQLiteConnectionFactory
from chat_analyzer_api.db.repo import AnalysisRepository
from chat_analyzer_api.middleware.rate_limit import InMemoryRateLimiter, RateLimitMiddleware
from chat_analyzer_api.middleware.request_logging import RequestLoggingMiddleware
from chat_analyzer_api.storage.file_storage import FileStorage
from chat_analyzer_api.workers.task_queue import TaskRunner


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()

    repo = AnalysisRepository(SQLiteConnectionFactory(settings.sqlite_path))
    repo.mark_running_as_failed()

    storage = FileStorage(base_dir=settings.storage_base_dir)

    runner = TaskRunner(
        repo=repo,
        storage=storage,
        workers=settings.task_workers,
        cleanup_interval_seconds=settings.cleanup_interval_seconds,
    )

    configure_runtime_dependencies(app, settings=settings, repo=repo, storage=storage, task_runner=runner)
    await runner.start()

    try:
        yield
    finally:
        clear_runtime_dependencies(app)
        await runner.stop()


settings = load_settings()
app = FastAPI(title=settings.app_name, version=settings.app_version, debug=settings.debug, lifespan=lifespan)

logging.basicConfig(level=logging.INFO, format="%(message)s")

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_middleware(
    RateLimitMiddleware,
    limiter=InMemoryRateLimiter(
        max_requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    ),
)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(analyses_router, prefix="/api")
