from fastapi import FastAPI
from fastapi.testclient import TestClient

from chat_analyzer_api.middleware.rate_limit import InMemoryRateLimiter, RateLimitMiddleware


def test_rate_limit_blocks_after_threshold():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, limiter=InMemoryRateLimiter(max_requests=2, window_seconds=60))

    @app.get("/ping")
    def ping():
        return {"ok": True}

    client = TestClient(app)
    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 200

    blocked = client.get("/ping")
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers
