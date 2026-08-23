"""Tests for the minimal per-endpoint cooldown guard (app/rate_limit.py) — added
after the audit found zero guardrails on the endpoints that either hammer an
external source (SEC/House Clerk/FMP) or burn real Anthropic API spend per call.
"""

import time

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from app import rate_limit
from app.rate_limit import cooldown


@pytest.fixture(autouse=True)
def _reset_rate_limit_state():
    rate_limit.reset()
    yield
    rate_limit.reset()


def test_cooldown_allows_first_call():
    guard = cooldown("key-first-call", 10)
    guard()  # must not raise


def test_cooldown_rejects_second_call_within_window():
    guard = cooldown("key-second-call", 10)
    guard()
    with pytest.raises(HTTPException) as exc_info:
        guard()
    assert exc_info.value.status_code == 429
    assert "wait" in exc_info.value.detail.lower()


def test_cooldown_allows_call_after_window_elapses():
    guard = cooldown("key-elapsed", 0.05)
    guard()
    time.sleep(0.08)
    guard()  # must not raise, window has passed


def test_cooldown_keys_are_independent():
    guard_a = cooldown("key-independent-a", 10)
    guard_b = cooldown("key-independent-b", 10)
    guard_a()
    guard_b()  # different key, must not raise


def test_cooldown_wired_into_a_real_endpoint_returns_429():
    app = FastAPI()

    @app.post("/thing", dependencies=[Depends(cooldown("endpoint-integration", 10))])
    def thing():
        return {"ok": True}

    client = TestClient(app)
    first = client.post("/thing")
    assert first.status_code == 200

    second = client.post("/thing")
    assert second.status_code == 429
    assert "wait" in second.json()["detail"].lower()
