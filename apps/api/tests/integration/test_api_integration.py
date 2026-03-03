from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from chat_analyzer_api.api.dependencies import configure_runtime_dependencies, get_repo, get_storage
from chat_analyzer_api.api.router import router as analyses_router
from chat_analyzer_api.core.config import Settings
from chat_analyzer_api.db.repo import PHASE_DONE, STATUS_DONE
from chat_analyzer_api.storage.file_storage import FileStorage

from apps.api.tests.helpers import build_repo

class FakeRunner:
    def __init__(self, repo, storage: FileStorage):
        self.repo = repo
        self.storage = storage

    async def enqueue(self, analysis_id: str) -> None:
        row = self.repo.get_analysis(analysis_id)
        if row is None:
            return

        dashboard = {
            "schema_version": "2.1",
            "analysis_id": analysis_id,
            "summary": {
                "total_messages": 1,
                "participants": 1,
                "start": "2026-01-01T00:00:00+00:00",
                "end": "2026-01-01T00:00:00+00:00",
                "timezone": row["timezone"],
            },
            "tabs": [{"id": "overview", "title": "Overview", "order": 0, "layout": "masonry", "default_open_sections": ["highlights"]}],
            "widgets": [
                {
                    "id": "kpi_messages",
                    "tab_id": "overview",
                    "type": "kpi",
                    "title": "Messages",
                    "priority": 1,
                    "section": "highlights",
                    "collapsed_by_default": False,
                    "value": 1,
                    "severity": "info",
                    "format": "integer",
                }
            ],
            "datasets": {},
            "dataset_meta": {},
            "metadata": {"warnings": [], "generated_at": "2026-01-01T00:00:00+00:00", "duration_sec": 0.01},
        }

        result_path = f"results/{analysis_id}.json"
        self.storage.write_json(result_path, dashboard)
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


class FakeRunnerNoop:
    async def enqueue(self, analysis_id: str) -> None:  # noqa: ARG002
        return


def _build_test_client(tmp_path: Path, max_upload_bytes: int = 1024 * 1024, complete_immediately: bool = True) -> TestClient:
    settings = Settings(
        app_name="test",
        app_version="2.0.0",
        debug=False,
        cors_origins=[],
        max_upload_bytes=max_upload_bytes,
        sqlite_path=str(tmp_path / "analyses.db"),
        storage_base_dir=str(tmp_path / "storage"),
        task_workers=1,
        task_ttl_seconds=3600,
        cleanup_interval_seconds=600,
        rate_limit_requests=100,
        rate_limit_window_seconds=60,
    )

    repo = build_repo(Path(settings.sqlite_path))
    storage = FileStorage(settings.storage_base_dir)
    runner = FakeRunner(repo, storage) if complete_immediately else FakeRunnerNoop()

    app = FastAPI()
    configure_runtime_dependencies(app, settings=settings, repo=repo, storage=storage, task_runner=runner)
    app.include_router(analyses_router, prefix="/api")
    return TestClient(app)


def test_analysis_lifecycle_success(tmp_path: Path):
    client = _build_test_client(tmp_path)

    response = client.post(
        "/api/analyses",
        data={"timezone": "UTC"},
        files={"file": ("result.json", b'{"messages": [{"type":"message","id":1,"date":"2026-01-01T00:00:00","from":"A","text":"hi"}]}', "application/json")},
    )
    assert response.status_code == 202
    analysis_id = response.json()["analysis_id"]

    status_resp = client.get(f"/api/analyses/{analysis_id}/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "done"

    dashboard = client.get(f"/api/analyses/{analysis_id}/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["analysis_id"] == analysis_id
    assert dashboard.json()["schema_version"] == "2.1"


def test_list_analyses_returns_created_item(tmp_path: Path):
    client = _build_test_client(tmp_path)
    created = client.post(
        "/api/analyses",
        data={"timezone": "UTC"},
        files={"file": ("result.json", b'{"messages": [{"type":"message","id":1,"date":"2026-01-01T00:00:00","from":"A","text":"hi"}]}', "application/json")},
    )
    analysis_id = created.json()["analysis_id"]

    listing = client.get("/api/analyses?limit=20")
    assert listing.status_code == 200
    assert any(item["analysis_id"] == analysis_id for item in listing.json()["items"])


def test_upload_limit_rejected(tmp_path: Path):
    client = _build_test_client(tmp_path, max_upload_bytes=16)
    response = client.post(
        "/api/analyses",
        data={"timezone": "UTC"},
        files={"file": ("big.json", b"x" * 32, "application/json")},
    )
    assert response.status_code == 413


def test_dashboard_conflict_when_not_done(tmp_path: Path):
    client = _build_test_client(tmp_path, complete_immediately=False)
    created = client.post(
        "/api/analyses",
        data={"timezone": "UTC"},
        files={"file": ("result.json", b'{"messages": [{"type":"message","id":1,"date":"2026-01-01T00:00:00","from":"A","text":"hi"}]}', "application/json")},
    )
    analysis_id = created.json()["analysis_id"]

    dashboard = client.get(f"/api/analyses/{analysis_id}/dashboard")
    assert dashboard.status_code == 409


def test_delete_analysis_removes_record(tmp_path: Path):
    client = _build_test_client(tmp_path)
    created = client.post(
        "/api/analyses",
        data={"timezone": "UTC"},
        files={"file": ("result.json", b'{"messages": [{"type":"message","id":1,"date":"2026-01-01T00:00:00","from":"A","text":"hi"}]}', "application/json")},
    )
    analysis_id = created.json()["analysis_id"]

    deleted = client.delete(f"/api/analyses/{analysis_id}")
    assert deleted.status_code == 204

    missing = client.get(f"/api/analyses/{analysis_id}/status")
    assert missing.status_code == 404


def test_healthz_ok(tmp_path: Path):
    client = _build_test_client(tmp_path)
    response = client.get("/api/healthz")
    assert response.status_code == 200
    assert response.json()["status"] in {"ok", "degraded"}


def test_analysis_status_rejects_invalid_id_format(tmp_path: Path):
    client = _build_test_client(tmp_path)
    response = client.get("/api/analyses/not-a-uuid/status")
    assert response.status_code == 422


def test_timezone_invalid_name_falls_back_to_utc(tmp_path: Path):
    client = _build_test_client(tmp_path)
    created = client.post(
        "/api/analyses",
        data={"timezone": "RU/Moscow"},
        files={"file": ("result.json", b'{"messages": [{"type":"message","id":1,"date":"2026-01-01T00:00:00","from":"A","text":"hi"}]}', "application/json")},
    )
    analysis_id = created.json()["analysis_id"]
    row = client.app.dependency_overrides[get_repo]().get_analysis(analysis_id)
    assert row is not None
    assert row["timezone"] == "UTC"


def test_timezone_rejects_forbidden_characters(tmp_path: Path):
    client = _build_test_client(tmp_path)
    response = client.post(
        "/api/analyses",
        data={"timezone": "UTC\x00BAD"},
        files={"file": ("result.json", b'{"messages": [{"type":"message","id":1,"date":"2026-01-01T00:00:00","from":"A","text":"hi"}]}', "application/json")},
    )
    assert response.status_code == 422


def test_dashboard_returns_500_for_corrupted_payload(tmp_path: Path):
    client = _build_test_client(tmp_path)
    created = client.post(
        "/api/analyses",
        data={"timezone": "UTC"},
        files={"file": ("result.json", b'{"messages": [{"type":"message","id":1,"date":"2026-01-01T00:00:00","from":"A","text":"hi"}]}', "application/json")},
    )
    analysis_id = created.json()["analysis_id"]
    row = client.app.dependency_overrides[get_repo]().get_analysis(analysis_id)
    assert row is not None
    client.app.dependency_overrides[get_storage]().write_bytes(row["result_path"], b'["not-an-object"]')

    response = client.get(f"/api/analyses/{analysis_id}/dashboard")
    assert response.status_code == 500


def test_timezone_too_long_is_rejected(tmp_path: Path):
    client = _build_test_client(tmp_path)
    response = client.post(
        "/api/analyses",
        data={"timezone": "A" * 129},
        files={"file": ("result.json", b'{"messages": [{"type":"message","id":1,"date":"2026-01-01T00:00:00","from":"A","text":"hi"}]}', "application/json")},
    )
    assert response.status_code == 422


def test_empty_timezone_falls_back_to_utc(tmp_path: Path):
    client = _build_test_client(tmp_path)
    created = client.post(
        "/api/analyses",
        data={"timezone": ""},
        files={"file": ("result.json", b'{"messages": [{"type":"message","id":1,"date":"2026-01-01T00:00:00","from":"A","text":"hi"}]}', "application/json")},
    )
    analysis_id = created.json()["analysis_id"]
    row = client.app.dependency_overrides[get_repo]().get_analysis(analysis_id)
    assert row is not None
    assert row["timezone"] == "UTC"
