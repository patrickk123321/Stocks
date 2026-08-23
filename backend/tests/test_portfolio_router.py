"""Regression tests for HoldingInput's validation — added after the audit found
no sanity-checking anywhere on holding values, letting an accidental extra zero
in shares/value silently produce a wildly wrong allocation with no warning.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import db
from app.routers import portfolio
from app.routers.portfolio import HoldingInput


def test_holding_input_accepts_valid_values():
    h = HoldingInput(ticker="aapl", shares=10, value=1500.0)
    assert h.ticker == "AAPL"
    assert h.shares == 10
    assert h.value == 1500.0


def test_holding_input_rejects_negative_shares():
    with pytest.raises(ValidationError):
        HoldingInput(ticker="AAPL", shares=-5, value=100)


def test_holding_input_rejects_negative_value():
    with pytest.raises(ValidationError):
        HoldingInput(ticker="AAPL", shares=5, value=-100)


def test_holding_input_rejects_empty_ticker():
    with pytest.raises(ValidationError):
        HoldingInput(ticker="   ", shares=5, value=100)


def test_holding_input_trims_and_uppercases_ticker():
    h = HoldingInput(ticker="  cash ", shares=None, value=500)
    assert h.ticker == "CASH"


def test_holding_input_allows_null_shares_and_value():
    h = HoldingInput(ticker="CASH")
    assert h.shares is None
    assert h.value is None


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()


@pytest.fixture
def client(temp_db):
    app = FastAPI()
    app.include_router(portfolio.router)
    return TestClient(app)


def test_snapshot_history_endpoint_empty_with_no_uploads(client):
    res = client.get("/api/portfolio/snapshots")
    assert res.status_code == 200
    assert res.json() == {"snapshots": []}


def test_snapshot_history_endpoint_returns_uploads_most_recent_first(client):
    # Every upload after the first used to be invisible — this is the fix.
    client.post("/api/portfolio/snapshots", json=[{"ticker": "AAPL", "shares": 1, "value": 100.0}])
    client.post("/api/portfolio/snapshots", json=[{"ticker": "MSFT", "shares": 1, "value": 200.0}])

    res = client.get("/api/portfolio/snapshots")
    body = res.json()
    assert len(body["snapshots"]) == 2
    assert body["snapshots"][0]["total_value"] == 200.0
    assert body["snapshots"][1]["total_value"] == 100.0
