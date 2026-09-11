"""Tests for the shared-secret admin-key gate (app/auth.py) — added after the
audit found the three /refresh endpoints and /api/status fully open to any
caller who knows the URL, guarded only by a cooldown explicitly documented as
not authentication (see rate_limit.py).
"""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app import auth
from app.auth import require_admin_key


@pytest.fixture
def _app_with_key(monkeypatch):
    monkeypatch.setattr(auth, "ADMIN_API_KEY", "secret123")

    app = FastAPI()

    @app.get("/thing", dependencies=[Depends(require_admin_key)])
    def thing():
        return {"ok": True}

    return TestClient(app)


def test_missing_header_rejected(_app_with_key):
    res = _app_with_key.get("/thing")
    assert res.status_code == 401


def test_wrong_key_rejected(_app_with_key):
    res = _app_with_key.get("/thing", headers={"X-Admin-Key": "wrong"})
    assert res.status_code == 401


def test_correct_key_allowed(_app_with_key):
    res = _app_with_key.get("/thing", headers={"X-Admin-Key": "secret123"})
    assert res.status_code == 200
    assert res.json() == {"ok": True}


def test_unset_admin_key_always_rejects(monkeypatch):
    # Leaving ADMIN_API_KEY unset must lock the endpoint, not skip the check —
    # a caller can't distinguish "not configured" from "wrong key" either way.
    monkeypatch.setattr(auth, "ADMIN_API_KEY", "")

    app = FastAPI()

    @app.get("/thing", dependencies=[Depends(require_admin_key)])
    def thing():
        return {"ok": True}

    client = TestClient(app)
    res = client.get("/thing", headers={"X-Admin-Key": "anything"})
    assert res.status_code == 401
