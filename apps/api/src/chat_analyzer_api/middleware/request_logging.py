from __future__ import annotations

import json
import logging
import re
import time
import uuid
from urllib.parse import parse_qsl, urlencode

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("api.request")

_SENSITIVE_QUERY_KEYS = {
    "token",
    "access_token",
    "refresh_token",
    "id_token",
    "api_key",
    "apikey",
    "key",
    "auth",
    "authorization",
    "password",
    "passwd",
    "secret",
}


def _sanitize_query(raw_query: str) -> str:
    if not raw_query:
        return ""

    pairs = parse_qsl(raw_query, keep_blank_values=True)
    sanitized: list[tuple[str, str]] = []
    for key, value in pairs:
        normalized_key = re.sub(r"[^a-z0-9_]", "", key.lower())
        if normalized_key in _SENSITIVE_QUERY_KEYS:
            sanitized.append((key, "[redacted]"))
        else:
            sanitized.append((key, value))
    return urlencode(sanitized)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex
        start = time.perf_counter()

        response: Response | None = None
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-Id"] = request_id
            return response
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 3)
            payload = {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query": _sanitize_query(request.url.query),
                "client_ip": _client_ip(request),
                "user_agent": request.headers.get("user-agent", ""),
                "status_code": status_code,
                "duration_ms": duration_ms,
            }
            logger.info(json.dumps(payload, ensure_ascii=False))


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"
