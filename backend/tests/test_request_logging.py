import json
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.middleware.request_logging import RequestLoggingMiddleware


def test_request_logging_sets_request_id_header():
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    client = TestClient(app)
    response = client.get("/ping")
    assert response.status_code == 200
    assert "X-Request-Id" in response.headers


def test_request_logging_redacts_sensitive_query(caplog):
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    caplog.set_level(logging.INFO, logger="api.request")
    client = TestClient(app)
    response = client.get("/ping?token=abc123&key=qwe&page=1")

    assert response.status_code == 200
    entries = [record.message for record in caplog.records if record.name == "api.request"]
    assert entries, "expected request log entry"
    payload = json.loads(entries[-1])
    assert payload["query"] == "token=%5Bredacted%5D&key=%5Bredacted%5D&page=1"


def test_request_logging_redacts_case_and_symbols(caplog):
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    caplog.set_level(logging.INFO, logger="api.request")
    client = TestClient(app)
    response = client.get("/ping?Authorization=secret&api-key=abc&auth=user&page=2")

    assert response.status_code == 200
    entries = [record.message for record in caplog.records if record.name == "api.request"]
    assert entries, "expected request log entry"
    payload = json.loads(entries[-1])
    assert payload["query"] == "Authorization=%5Bredacted%5D&api-key=%5Bredacted%5D&auth=%5Bredacted%5D&page=2"
