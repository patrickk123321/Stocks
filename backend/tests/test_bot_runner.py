"""Tests for trading_engine.run_bot_once — the orchestrator that talks to a
real (temp) DB and a mocked Alpaca client. Mirrors test_scheduler.py's
temp_db fixture pattern.
"""

from datetime import date
from unittest.mock import patch

import pytest

from app import alpaca_client, db, trading_engine


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()


def _enable_bot(max_trade_dollars=1000.0, max_trades_per_day=5, cash_buffer_pct=0.0):
    db.save_bot_config(
        enabled=True,
        max_trade_dollars=max_trade_dollars,
        max_trades_per_day=max_trades_per_day,
        cash_buffer_pct=cash_buffer_pct,
    )


def _set_risk_profile():
    db.save_risk_profile(
        time_horizon=None, risk_tolerance="moderate", primary_goal=None,
        target_stock_pct=60.0, target_bond_pct=30.0, target_cash_pct=10.0,
    )


def test_run_bot_once_is_a_noop_when_disabled(temp_db):
    _set_risk_profile()
    # bot_config defaults to enabled=0 via ensure_default_bot_config
    inserted, errors = trading_engine.run_bot_once()
    assert (inserted, errors) == (0, 0)
    assert db.list_bot_trades()[1] == 0


def test_run_bot_once_is_a_noop_without_a_risk_profile(temp_db):
    _enable_bot()
    # no risk profile saved
    inserted, errors = trading_engine.run_bot_once()
    assert (inserted, errors) == (0, 0)


def test_run_bot_once_is_a_noop_when_alpaca_not_configured(temp_db):
    _enable_bot()
    _set_risk_profile()
    with patch("app.alpaca_client.get_account", side_effect=alpaca_client.AlpacaNotConfiguredError("x")):
        inserted, errors = trading_engine.run_bot_once()
    assert (inserted, errors) == (0, 0)


def test_run_bot_once_places_trades_and_logs_them(temp_db):
    _enable_bot()
    _set_risk_profile()
    with patch("app.alpaca_client.get_account", return_value={"cash": 10000.0, "buying_power": 10000.0, "equity": 10000.0, "portfolio_value": 10000.0}), \
         patch("app.alpaca_client.get_positions", return_value=[{"ticker": "CASH", "shares": 1, "value": 10000.0}]), \
         patch("app.alpaca_client.submit_market_buy", return_value={"id": "order-1", "status": "accepted"}), \
         patch("app.alpaca_client.get_recent_orders", return_value=[]):
        inserted, errors = trading_engine.run_bot_once()

    assert inserted > 0
    assert errors == 0
    trades = db.get_trades_for_run_date(date.today().isoformat())
    assert len(trades) == inserted
    assert all(t["status"] == "submitted" for t in trades)
    assert all(t["alpaca_order_id"] == "order-1" for t in trades)


def test_run_bot_once_one_failed_order_does_not_abort_the_rest(temp_db):
    _enable_bot(max_trade_dollars=100.0, max_trades_per_day=5)
    _set_risk_profile()

    call_count = {"n": 0}

    def flaky_submit(ticker, notional):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise alpaca_client.AlpacaOrderError("insufficient buying power")
        return {"id": f"order-{call_count['n']}", "status": "accepted"}

    with patch("app.alpaca_client.get_account", return_value={"cash": 10000.0, "buying_power": 10000.0, "equity": 10000.0, "portfolio_value": 10000.0}), \
         patch("app.alpaca_client.get_positions", return_value=[{"ticker": "CASH", "shares": 1, "value": 10000.0}]), \
         patch("app.alpaca_client.submit_market_buy", side_effect=flaky_submit), \
         patch("app.alpaca_client.get_recent_orders", return_value=[]):
        inserted, errors = trading_engine.run_bot_once()

    assert errors == 1
    assert inserted >= 1  # at least the second decision still went through
    trades = db.get_trades_for_run_date(date.today().isoformat())
    statuses = {t["status"] for t in trades}
    assert "failed" in statuses
    assert "submitted" in statuses


def test_run_bot_once_second_call_same_day_is_a_noop(temp_db):
    _enable_bot()
    _set_risk_profile()
    with patch("app.alpaca_client.get_account", return_value={"cash": 10000.0, "buying_power": 10000.0, "equity": 10000.0, "portfolio_value": 10000.0}), \
         patch("app.alpaca_client.get_positions", return_value=[{"ticker": "CASH", "shares": 1, "value": 10000.0}]), \
         patch("app.alpaca_client.submit_market_buy", return_value={"id": "order-1", "status": "accepted"}), \
         patch("app.alpaca_client.get_recent_orders", return_value=[]):
        first_inserted, _ = trading_engine.run_bot_once()
        second_inserted, second_errors = trading_engine.run_bot_once()

    assert first_inserted > 0
    assert (second_inserted, second_errors) == (0, 0)
    # no new rows from the second call
    _, total = db.list_bot_trades()
    assert total == first_inserted
