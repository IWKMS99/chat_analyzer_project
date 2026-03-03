from __future__ import annotations

import json
import os
import re
import tempfile
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, Response, UploadFile, status

from backend.app.core.schemas import (
    AnalysisCreatedResponse,
    AnalysisListItem,
    AnalysisListResponse,
    AnalysisStatusResponse,
    DashboardResponse,
    HealthResponse,
)
from backend.app.db.repo import AnalysisRepository, STATUS_DONE
from backend.app.services.task_runner import TaskRunner
from backend.app.storage.base import StorageBackend


router = APIRouter(tags=["analyses"])

_ANALYSIS_ID_RE = re.compile(r"^[a-f0-9]{32}$")
_MAX_TIMEZONE_LEN = 128


def _get_repo(request: Request) -> AnalysisRepository:
    return request.app.state.analysis_repo


def _get_runner(request: Request) -> TaskRunner:
    return request.app.state.task_runner


def _get_storage(request: Request) -> StorageBackend:
    return request.app.state.storage


def _validated_analysis_id(analysis_id: str) -> str:
    if not _ANALYSIS_ID_RE.fullmatch(analysis_id):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid analysis id format")
    return analysis_id


def _normalize_timezone(timezone_name: str | None) -> str:
    candidate = (timezone_name or "UTC").strip() or "UTC"
    if len(candidate) > _MAX_TIMEZONE_LEN:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Timezone is too long")
    if "\x00" in candidate:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Timezone contains forbidden characters")

    try:
        ZoneInfo(candidate)
        return candidate
    except (ZoneInfoNotFoundError, ValueError):
        return "UTC"


async def _persist_upload_to_temp(upload_file: UploadFile, max_size_bytes: int) -> tuple[str, int]:
    current_size = 0
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
        file_path = tmp.name
        while True:
            chunk = await upload_file.read(1024 * 1024)
            if not chunk:
                break
            current_size += len(chunk)
            if current_size > max_size_bytes:
                tmp.close()
                os.remove(file_path)
                raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="File exceeds upload limit")
            tmp.write(chunk)

    if current_size == 0:
        os.remove(file_path)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    return file_path, current_size


@router.post("/analyses", response_model=AnalysisCreatedResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_analysis(
    request: Request,
    file: UploadFile = File(...),
    timezone: str = Form("UTC"),
) -> AnalysisCreatedResponse:
    settings = request.app.state.settings
    temp_upload_path = None
    analysis_id = uuid.uuid4().hex
    upload_path = f"uploads/{analysis_id}.json"

    try:
        temp_upload_path, _ = await _persist_upload_to_temp(file, settings.max_upload_bytes)
        _get_storage(request).copy_file(upload_path, temp_upload_path)

        created = _get_repo(request).create_analysis(
            analysis_id=analysis_id,
            timezone_name=_normalize_timezone(timezone),
            upload_path=upload_path,
            ttl_seconds=settings.task_ttl_seconds,
        )
        await _get_runner(request).enqueue(analysis_id)
        return AnalysisCreatedResponse(
            analysis_id=analysis_id,
            status=created["status"],
            created_at=datetime.fromisoformat(created["created_at"]),
        )
    finally:
        if temp_upload_path and os.path.exists(temp_upload_path):
            os.remove(temp_upload_path)


@router.get("/analyses", response_model=AnalysisListResponse)
def list_analyses(request: Request, limit: int = Query(20, ge=1, le=200)) -> AnalysisListResponse:
    rows = _get_repo(request).list_recent_analyses(limit=limit)
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
def get_analysis_status(analysis_id: str, request: Request) -> AnalysisStatusResponse:
    safe_analysis_id = _validated_analysis_id(analysis_id)
    row = _get_repo(request).get_analysis(safe_analysis_id)
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
def get_analysis_dashboard(analysis_id: str, request: Request) -> DashboardResponse:
    safe_analysis_id = _validated_analysis_id(analysis_id)
    row = _get_repo(request).get_analysis(safe_analysis_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    if row["status"] != STATUS_DONE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Analysis is not completed yet")

    result_path = row.get("result_path")
    if not result_path or not _get_storage(request).exists(result_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard payload not found")

    try:
        payload = _get_storage(request).read_json(result_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard payload not found") from exc
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Dashboard payload is corrupted") from exc
    except OSError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to read dashboard payload") from exc

    return DashboardResponse(**payload)


@router.delete("/analyses/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_analysis(analysis_id: str, request: Request) -> Response:
    safe_analysis_id = _validated_analysis_id(analysis_id)
    row = _get_repo(request).get_analysis(safe_analysis_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    _get_storage(request).remove_path(row.get("upload_path"))
    _get_storage(request).remove_path(row.get("result_path"))
    _get_repo(request).delete_analysis(safe_analysis_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/healthz", response_model=HealthResponse)
def healthz(request: Request) -> HealthResponse:
    repo_ok = _get_repo(request).healthcheck()
    storage_ok = _get_storage(request).healthcheck()
    status_value = "ok" if repo_ok and storage_ok else "degraded"
    return HealthResponse(status=status_value, sqlite_ok=repo_ok, storage_ok=storage_ok)
