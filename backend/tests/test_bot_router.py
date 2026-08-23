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


def test_bot_config_input_rejects_non_positive_max_trade_dollars():
    with pytest.raises(ValidationError):
        BotConfigInput(enabled=True, max_trade_dollars=0, max_trades_per_day=3, cash_buffer_pct=10)


def test_bot_config_input_rejects_cash_buffer_out_of_range():
    with pytest.raises(ValidationError):
        BotConfigInput(enabled=True, max_trade_dollars=100, max_trades_per_day=3, cash_buffer_pct=150)


def test_bot_config_input_rejects_excessive_max_trades_per_day():
    with pytest.raises(ValidationError):
        BotConfigInput(enabled=True, max_trade_dollars=100, max_trades_per_day=21, cash_buffer_pct=10)


def test_get_config_returns_seeded_defaults(client):
    res = client.get("/api/bot/config")
    assert res.status_code == 200
    body = res.json()
    assert body["enabled"] == 0
    assert body["max_trade_dollars"] == 100.0
    assert body["max_trades_per_day"] == 3
    assert body["cash_buffer_pct"] == 10.0


def test_post_config_updates_and_persists(client):
    res = client.post("/api/bot/config", json={
        "enabled": True, "max_trade_dollars": 250.0, "max_trades_per_day": 2, "cash_buffer_pct": 15.0,
    })
    assert res.status_code == 200
    body = res.json()
    assert body["enabled"] == 1
    assert body["max_trade_dollars"] == 250.0

    followup = client.get("/api/bot/config")
    assert followup.json()["max_trade_dollars"] == 250.0


def test_post_config_rejects_invalid_payload(client):
    res = client.post("/api/bot/config", json={
        "enabled": True, "max_trade_dollars": -5, "max_trades_per_day": 3, "cash_buffer_pct": 10.0,
    })
    assert res.status_code == 422


def test_get_account_returns_503_when_not_configured(client):
    from app.alpaca_client import AlpacaNotConfiguredError
    with patch("app.routers.bot.alpaca_client.get_account", side_effect=AlpacaNotConfiguredError("not set up")):
        res = client.get("/api/bot/account")
    assert res.status_code == 503
    assert "not set up" in res.json()["detail"]


def test_get_account_returns_data_when_configured(client):
    with patch("app.routers.bot.alpaca_client.get_account", return_value={"cash": 1.0, "buying_power": 1.0, "equity": 1.0, "portfolio_value": 1.0}), \
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
