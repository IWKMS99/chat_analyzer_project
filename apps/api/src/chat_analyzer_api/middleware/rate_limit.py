from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


@dataclass
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int


class InMemoryRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max(1, max_requests)
        self.window_seconds = max(1, window_seconds)
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, key: str, now: float | None = None) -> RateLimitDecision:
        current = now if now is not None else time.monotonic()
        async with self._lock:
            events = self._events[key]
            threshold = current - self.window_seconds
            while events and events[0] <= threshold:
                events.popleft()

            if len(events) >= self.max_requests:
                retry_after = int(max(1, self.window_seconds - (current - events[0])))
                return RateLimitDecision(allowed=False, retry_after_seconds=retry_after)

            events.append(current)
            return RateLimitDecision(allowed=True, retry_after_seconds=0)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limiter: InMemoryRateLimiter):
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "OPTIONS" or request.url.path.endswith("/healthz"):
            return await call_next(request)

        client_ip = _client_ip(request)
        decision = await self.limiter.check(client_ip)
        if not decision.allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(decision.retry_after_seconds)},
            )

        return await call_next(request)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"
