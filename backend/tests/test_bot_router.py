"""Tests for the bot router — FastAPI TestClient, mirrors test_portfolio_router.py."""

from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import db, rate_limit
from app.routers import bot
from app.routers.bot import BotConfigInput


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()


@pytest.fixture
def client(temp_db):
    rate_limit.reset()
    app = FastAPI()
    app.include_router(bot.router)
    return TestClient(app)


def _valid_config_payload(**overrides):
    payload = {
        "enabled": True, "max_trades_per_day": 3, "cash_buffer_pct": 10.0,
        "standard_trade_pct": 10.0, "high_conviction_trade_pct": 20.0, "position_cap_pct": 20.0,
    }
    payload.update(overrides)
    return payload


def test_bot_config_input_rejects_non_positive_standard_trade_pct():
    with pytest.raises(ValidationError):
        BotConfigInput(**{**_valid_config_payload(), "standard_trade_pct": 0})


def test_bot_config_input_rejects_cash_buffer_out_of_range():
    with pytest.raises(ValidationError):
        BotConfigInput(**{**_valid_config_payload(), "cash_buffer_pct": 150})


def test_bot_config_input_rejects_excessive_max_trades_per_day():
    with pytest.raises(ValidationError):
        BotConfigInput(**{**_valid_config_payload(), "max_trades_per_day": 21})


def test_bot_config_input_rejects_position_cap_out_of_range():
    with pytest.raises(ValidationError):
        BotConfigInput(**{**_valid_config_payload(), "position_cap_pct": 150})


def test_get_config_returns_seeded_defaults(client):
    res = client.get("/api/bot/config")
    assert res.status_code == 200
    body = res.json()
    assert body["enabled"] == 0
    assert body["max_trades_per_day"] == 3
    assert body["cash_buffer_pct"] == 10.0
    assert body["standard_trade_pct"] == 10.0
    assert body["high_conviction_trade_pct"] == 20.0
    assert body["position_cap_pct"] == 20.0


def test_post_config_updates_and_persists(client):
    res = client.post("/api/bot/config", json=_valid_config_payload(standard_trade_pct=15.0, max_trades_per_day=2))
    assert res.status_code == 200
    body = res.json()
    assert body["enabled"] == 1
    assert body["standard_trade_pct"] == 15.0

    followup = client.get("/api/bot/config")
    assert followup.json()["standard_trade_pct"] == 15.0


def test_post_config_rejects_invalid_payload(client):
    res = client.post("/api/bot/config", json=_valid_config_payload(standard_trade_pct=-5))
    assert res.status_code == 422


def test_get_account_returns_503_when_not_configured(client):
    # The router checks ensure_configured() once, up front, before firing the
    # 3 parallel get_account/get_positions/is_market_open calls — so mocking
    # just this one check is enough, and (importantly) none of the three real
    # functions ever run. An earlier version of this test only mocked
    # get_account and relied on asyncio.gather's parallel calls each raising
    # AlpacaNotConfiguredError independently — with real keys in .env (as in
    # this environment), the other two calls ran for real instead and hung
    # the test suite for 36 minutes.
    from app.alpaca_client import AlpacaNotConfiguredError
    with patch("app.routers.bot.alpaca_client.ensure_configured", side_effect=AlpacaNotConfiguredError("not set up")):
        res = client.get("/api/bot/account")
    assert res.status_code == 503
    assert "not set up" in res.json()["detail"]


def test_get_account_returns_data_when_configured(client):
    # ensure_configured mocked as a no-op explicitly — must not depend on
    # whether this machine's real .env happens to have Alpaca keys set.
    with patch("app.routers.bot.alpaca_client.ensure_configured"), \
         patch("app.routers.bot.alpaca_client.get_account", return_value={"cash": 1.0, "buying_power": 1.0, "equity": 1.0, "portfolio_value": 1.0}), \
         patch("app.routers.bot.alpaca_client.get_positions", return_value=[]), \
         patch("app.routers.bot.alpaca_client.is_market_open", return_value=True):
        res = client.get("/api/bot/account")
    assert res.status_code == 200
    assert res.json()["market_open"] is True


def test_list_trades_empty(client):
    res = client.get("/api/bot/trades")
    assert res.status_code == 200
    assert res.json() == {"rows": [], "total": 0}


def test_run_now_cooldown_returns_429_on_second_call(client):
    with patch("app.routers.bot.trading_engine.refresh_pending_trade_statuses"), \
         patch("app.routers.bot.trading_engine.run_bot_once", return_value=(0, 0)):
        first = client.post("/api/bot/run")
        second = client.post("/api/bot/run")
    assert first.status_code == 200
    assert second.status_code == 429


def test_read_signals_empty_with_no_history(client):
    res = client.get("/api/bot/signals")
    assert res.status_code == 200
    assert res.json() == {"run_date": None, "candidates": []}


def test_read_signals_flags_persisted_vs_pending(client):
    db.log_bot_candidates("2026-08-22", [{
        "candidate_key": "stock_buy:AAPL", "candidate_type": "stock_buy", "ticker": "AAPL",
        "asset_class": "stock", "signal_strength": 2, "diff_pct": None, "detail": {},
    }])
    db.log_bot_candidates("2026-08-23", [
        {"candidate_key": "stock_buy:AAPL", "candidate_type": "stock_buy", "ticker": "AAPL",
         "asset_class": "stock", "signal_strength": 2, "diff_pct": None, "detail": {}},
        {"candidate_key": "stock_buy:MSFT", "candidate_type": "stock_buy", "ticker": "MSFT",
         "asset_class": "stock", "signal_strength": 2, "diff_pct": None, "detail": {}},
    ])
    res = client.get("/api/bot/signals")
    body = res.json()
    assert body["run_date"] == "2026-08-23"
    by_ticker = {c["ticker"]: c["persisted"] for c in body["candidates"]}
    assert by_ticker["AAPL"] is True   # seen 2026-08-22 and 2026-08-23
    assert by_ticker["MSFT"] is False  # first time seen


def test_run_now_skips_when_already_ran_today(client):
    db.insert_bot_trade({
        "run_date": date.today().isoformat(),
        "ticker": "VTI", "notional": 100.0, "asset_class": "stock",
        "rationale": "test", "status": "submitted",
        "placed_at": datetime.now(timezone.utc).isoformat(),
    })
    with patch("app.routers.bot.trading_engine.refresh_pending_trade_statuses"):
        res = client.post("/api/bot/run")
    assert res.status_code == 200
    assert res.json()["skipped"] == "already ran today"
