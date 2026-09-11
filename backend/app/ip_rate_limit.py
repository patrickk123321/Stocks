"""Dependency-free per-IP sliding-window rate limiter for every route, layered
on top of (not replacing) the existing per-endpoint cooldown in rate_limit.py.
No Redis — a single uvicorn process (see Procfile, no --workers) means an
in-memory dict is enough and needs no locks: nothing here awaits between
reading and updating a given IP's request log, so each check-and-record is
atomic with respect to other requests on the event loop.
"""

import time
from collections import deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

WINDOW_SECONDS = 60
MAX_REQUESTS_PER_WINDOW = 100
EXEMPT_PATHS = {"/api/health"}  # Railway's own poller, not real traffic

_hits: dict[str, deque[float]] = {}


def reset() -> None:
    """Test-only: clear all rate-limit state between test cases."""
    _hits.clear()


def _client_ip(request: Request) -> str:
    # Railway terminates TLS at its edge and proxies every request here,
    # setting X-Forwarded-For itself — the app is never reached any other
    # way, so the first (leftmost) entry is trustworthy. If ever deployed
    # behind a different/untrusted proxy, this needs to change.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, max_requests: int = MAX_REQUESTS_PER_WINDOW, window_seconds: float = WINDOW_SECONDS):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def dispatch(self, request: Request, call_next):
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        ip = _client_ip(request)
        now = time.monotonic()
        hits = _hits.setdefault(ip, deque())
        while hits and now - hits[0] > self.window_seconds:
            hits.popleft()

        if len(hits) >= self.max_requests:
            retry_after = max(1, int(self.window_seconds - (now - hits[0])) + 1)
            return JSONResponse(
                {"detail": f"Too many requests — retry after {retry_after}s."},
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )

        hits.append(now)
        return await call_next(request)
