from __future__ import annotations

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status

from chat_analyzer_api.api.dependencies import get_repo, get_settings, get_storage, get_task_runner
from chat_analyzer_api.api.uploads import managed_upload_temp_file
from chat_analyzer_api.core.config import Settings
from chat_analyzer_api.core.schemas import (
    AnalysisCreatedResponse,
    AnalysisListItem,
    AnalysisListResponse,
    AnalysisStatusResponse,
    DashboardResponse,
    HealthResponse,
)
from chat_analyzer_api.db.repo import AnalysisRepository, STATUS_DONE
from chat_analyzer_api.storage.base import StorageBackend
from chat_analyzer_api.utils.validators import normalize_timezone, validate_analysis_id
from chat_analyzer_api.workers.task_queue import TaskRunner


router = APIRouter(tags=["analyses"])


@router.post("/analyses", response_model=AnalysisCreatedResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_analysis(
    file: UploadFile = File(...),
    timezone: str = Form("UTC"),
    settings: Settings = Depends(get_settings),
    repo: AnalysisRepository = Depends(get_repo),
    storage: StorageBackend = Depends(get_storage),
    task_runner: TaskRunner = Depends(get_task_runner),
) -> AnalysisCreatedResponse:
    analysis_id = uuid.uuid4().hex
    upload_path = f"uploads/{analysis_id}.json"

    async with managed_upload_temp_file(file, settings.max_upload_bytes) as (temp_upload_path, _):
        storage.copy_file(upload_path, temp_upload_path)

        created = repo.create_analysis(
            analysis_id=analysis_id,
            timezone_name=normalize_timezone(timezone),
            upload_path=upload_path,
            ttl_seconds=settings.task_ttl_seconds,
        )
        await task_runner.enqueue(analysis_id)
        return AnalysisCreatedResponse(
            analysis_id=analysis_id,
            status=created["status"],
            created_at=datetime.fromisoformat(created["created_at"]),
        )


@router.get("/analyses", response_model=AnalysisListResponse)
def list_analyses(
    limit: int = Query(20, ge=1, le=200),
    repo: AnalysisRepository = Depends(get_repo),
) -> AnalysisListResponse:
    rows = repo.list_recent_analyses(limit=limit)
    return AnalysisListResponse(
        items=[
            AnalysisListItem(
                analysis_id=row["id"],
                status=row["status"],
                phase=row["phase"],
                progress_pct=int(row["progress_pct"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            for row in rows
        ]
    )


@router.get("/analyses/{analysis_id}/status", response_model=AnalysisStatusResponse)
def get_analysis_status(analysis_id: str, repo: AnalysisRepository = Depends(get_repo)) -> AnalysisStatusResponse:
    safe_analysis_id = validate_analysis_id(analysis_id)
    row = repo.get_analysis(safe_analysis_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    return AnalysisStatusResponse(
        analysis_id=row["id"],
        status=row["status"],
        phase=row["phase"],
        progress_pct=int(row["progress_pct"]),
        eta_sec=row.get("eta_sec"),
        warnings=row.get("warnings", []),
        error_code=row.get("error_code"),
        error_message=row.get("error_message"),
    )


@router.get("/analyses/{analysis_id}/dashboard", response_model=DashboardResponse)
def get_analysis_dashboard(
    analysis_id: str,
    repo: AnalysisRepository = Depends(get_repo),
    storage: StorageBackend = Depends(get_storage),
) -> DashboardResponse:
    safe_analysis_id = validate_analysis_id(analysis_id)
    row = repo.get_analysis(safe_analysis_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    if row["status"] != STATUS_DONE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Analysis is not completed yet")

    result_path = row.get("result_path")
    if not result_path or not storage.exists(result_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard payload not found")

    try:
        payload = storage.read_json(result_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard payload not found") from exc
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Dashboard payload is corrupted") from exc
    except OSError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to read dashboard payload") from exc

    return DashboardResponse(**payload)


@router.delete("/analyses/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_analysis(
    analysis_id: str,
    repo: AnalysisRepository = Depends(get_repo),
    storage: StorageBackend = Depends(get_storage),
) -> Response:
    safe_analysis_id = validate_analysis_id(analysis_id)
    row = repo.get_analysis(safe_analysis_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    storage.remove_path(row.get("upload_path"))
    storage.remove_path(row.get("result_path"))
    repo.delete_analysis(safe_analysis_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/healthz", response_model=HealthResponse)
def healthz(
    repo: AnalysisRepository = Depends(get_repo),
    storage: StorageBackend = Depends(get_storage),
) -> HealthResponse:
    repo_ok = repo.healthcheck()
    storage_ok = storage.healthcheck()
    status_value = "ok" if repo_ok and storage_ok else "degraded"
    return HealthResponse(status=status_value, sqlite_ok=repo_ok, storage_ok=storage_ok)
