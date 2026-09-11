"""Tests for the per-IP sliding-window rate limiter (app/ip_rate_limit.py) —
added after the audit found zero rate limiting on any read/list/export
endpoint, only the unrelated per-endpoint cooldown on the three /refresh routes.
"""

import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import ip_rate_limit
from app.ip_rate_limit import RateLimitMiddleware


@pytest.fixture(autouse=True)
def _reset_rate_limit_state():
    ip_rate_limit.reset()
    yield
    ip_rate_limit.reset()


def _make_client(max_requests: int, window_seconds: float) -> TestClient:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, max_requests=max_requests, window_seconds=window_seconds)

    @app.get("/thing")
    def thing():
        return {"ok": True}

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return TestClient(app)


def test_first_n_requests_allowed():
    client = _make_client(max_requests=3, window_seconds=10)
    for _ in range(3):
        assert client.get("/thing").status_code == 200


def test_request_over_limit_rejected_with_retry_after():
    client = _make_client(max_requests=2, window_seconds=10)
    client.get("/thing")
    client.get("/thing")

    res = client.get("/thing")
    assert res.status_code == 429
    assert "Retry-After" in res.headers
    assert int(res.headers["Retry-After"]) > 0


def test_limit_is_independent_per_ip():
    client = _make_client(max_requests=1, window_seconds=10)
    assert client.get("/thing", headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 200
    # A different IP has its own, unconsumed quota.
    assert client.get("/thing", headers={"X-Forwarded-For": "2.2.2.2"}).status_code == 200
    # The first IP is now over its own limit.
    assert client.get("/thing", headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 429


def test_allows_again_after_window_elapses():
    client = _make_client(max_requests=1, window_seconds=0.05)
    assert client.get("/thing").status_code == 200
    assert client.get("/thing").status_code == 429
    time.sleep(0.08)
    assert client.get("/thing").status_code == 200


def test_exempt_path_never_limited():
    client = _make_client(max_requests=1, window_seconds=10)
    for _ in range(5):
        assert client.get("/api/health").status_code == 200
