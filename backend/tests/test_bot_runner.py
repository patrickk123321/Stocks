"""Tests for trading_engine.run_bot_once — the orchestrator that talks to a
real (temp) DB and a mocked Alpaca client. Mirrors test_scheduler.py's
temp_db fixture pattern.

Every Alpaca function run_bot_once can reach is mocked in every test here —
confirmed live that a partially-mocked Alpaca surface lets an unmocked call
reach the real API when real keys are configured in .env (see the comment in
test_bot_router.py's test_get_account_returns_503_when_not_configured, which
hung the suite for 36 minutes this exact way).
"""

from datetime import date, timedelta
from unittest.mock import patch

import pytest

from app import alpaca_client, db, trading_engine

ACCOUNT = {"cash": 10000.0, "buying_power": 10000.0, "equity": 10000.0, "portfolio_value": 10000.0}


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()


def _enable_bot(max_trades_per_day=5, cash_buffer_pct=0.0, standard_trade_pct=10.0, high_conviction_trade_pct=20.0, position_cap_pct=20.0):
    db.save_bot_config(
        enabled=True,
        max_trades_per_day=max_trades_per_day,
        cash_buffer_pct=cash_buffer_pct,
        standard_trade_pct=standard_trade_pct,
        high_conviction_trade_pct=high_conviction_trade_pct,
        position_cap_pct=position_cap_pct,
    )


def _set_risk_profile():
    db.save_risk_profile(
        time_horizon=None, risk_tolerance="moderate", primary_goal=None,
        target_stock_pct=60.0, target_bond_pct=30.0, target_cash_pct=10.0,
    )


def _mock_alpaca(get_positions=None, submit_buy=None, submit_sell=None):
    """A context-manager-returning helper bundling every Alpaca surface
    run_bot_once can reach, so no test can accidentally leave one unmocked."""
    return patch.multiple(
        "app.alpaca_client",
        get_account=lambda: ACCOUNT,
        get_positions=lambda: get_positions if get_positions is not None else [],
        get_recent_orders=lambda limit=100: [],
        submit_market_buy=submit_buy or (lambda ticker, notional: {"id": "order-1", "status": "accepted"}),
        submit_market_sell=submit_sell or (lambda ticker, notional=None, qty=None: {"id": "order-1", "status": "accepted"}),
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


def test_run_bot_once_first_time_seeing_a_gap_only_logs_it_no_trade_yet(temp_db):
    # v2's persistence rule: a gap/signal candidate is never acted on the
    # first day it's observed — only cap-breach trades (tier a) skip this gate.
    _enable_bot()
    _set_risk_profile()
    with _mock_alpaca():
        inserted, errors = trading_engine.run_bot_once()
    assert (inserted, errors) == (0, 0)

    today = date.today().isoformat()
    keys = db.get_observed_candidate_keys(today)
    assert "gap_underweight:stock" in keys  # logged...
    assert db.get_trades_for_run_date(today) == []  # ...but not traded on yet


def test_run_bot_once_trades_a_gap_that_persisted_from_the_prior_logged_day(temp_db):
    _enable_bot()
    _set_risk_profile()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    # Pre-seed the exact candidate today's real gap detection will also
    # produce for an all-cash account vs. a moderate 60% stock target.
    db.log_bot_candidates(yesterday, [{
        "candidate_key": "gap_underweight:stock", "candidate_type": "gap_underweight",
        "ticker": None, "asset_class": "stock", "signal_strength": None, "diff_pct": -60.0,
        "detail": {"message": "stock underweight", "suggested_funds": ["VTI (Vanguard Total Stock Market ETF)"]},
    }])

    with _mock_alpaca():
        inserted, errors = trading_engine.run_bot_once()

    assert inserted > 0
    assert errors == 0
    trades = db.get_trades_for_run_date(date.today().isoformat())
    assert any(t["ticker"] == "VTI" and t["trigger_type"] == "gap_underweight" for t in trades)


def test_run_bot_once_cap_breach_trades_immediately_no_persistence_needed(temp_db):
    # Tier (a) is explicitly NOT persistence-gated — must fire on the very
    # first run, unlike gap/signal-driven trades.
    _enable_bot()
    _set_risk_profile()
    positions = [{"ticker": "AAPL", "shares": 10, "value": 3000.0}]  # 30% of a $10k account
    with _mock_alpaca(get_positions=positions):
        inserted, errors = trading_engine.run_bot_once()
    assert inserted >= 1
    trades = db.get_trades_for_run_date(date.today().isoformat())
    assert any(t["ticker"] == "AAPL" and t["trigger_type"] == "cap_breach" for t in trades)


def test_run_bot_once_one_failed_order_does_not_abort_the_rest(temp_db):
    _enable_bot()
    _set_risk_profile()
    # Two individual stocks simultaneously over the 20% cap -> two decisions
    # on the first run (cap-breach isn't persistence-gated), no setup needed.
    # Zero cash so the percentages aren't diluted by the account's mocked cash.
    positions = [
        {"ticker": "AAPL", "shares": 10, "value": 3000.0},
        {"ticker": "MSFT", "shares": 10, "value": 3000.0},
    ]

    call_count = {"n": 0}

    def flaky_sell(ticker, notional=None, qty=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise alpaca_client.AlpacaOrderError("insufficient shares")
        return {"id": f"order-{call_count['n']}", "status": "accepted"}

    with patch.multiple(
        "app.alpaca_client",
        get_account=lambda: {"cash": 0.0, "buying_power": 0.0, "equity": 6000.0, "portfolio_value": 6000.0},
        get_positions=lambda: positions,
        get_recent_orders=lambda limit=100: [],
        submit_market_buy=lambda ticker, notional: {"id": "order-1", "status": "accepted"},
        submit_market_sell=flaky_sell,
    ):
        inserted, errors = trading_engine.run_bot_once()

    assert errors == 1
    assert inserted >= 1
    trades = db.get_trades_for_run_date(date.today().isoformat())
    statuses = {t["status"] for t in trades}
    assert "failed" in statuses
    assert "submitted" in statuses


def test_run_bot_once_second_call_same_day_is_a_noop(temp_db):
    _enable_bot()
    _set_risk_profile()
    positions = [{"ticker": "AAPL", "shares": 10, "value": 3000.0}]
    with _mock_alpaca(get_positions=positions):
        first_inserted, _ = trading_engine.run_bot_once()
        second_inserted, second_errors = trading_engine.run_bot_once()

    assert first_inserted > 0
    assert (second_inserted, second_errors) == (0, 0)
    _, total = db.list_bot_trades()
    assert total == first_inserted


def test_run_bot_once_trades_from_uninvested_cash_on_a_fresh_account(temp_db):
    # Regression test: get_all_positions() never includes cash as a
    # "position" (confirmed against Alpaca's real API — a fresh paper account
    # returns positions=[] even with $100k sitting in it). Without folding
    # account["cash"] into the holdings decide_trades sees, total_value comes
    # out to $0 and every gap silently rounds to a $0 trade.
    _enable_bot()
    _set_risk_profile()
    positions = [{"ticker": "AAPL", "shares": 10, "value": 30000.0}]  # 30% of $100k -> cap breach, day-1 actionable
    with patch.multiple(
        "app.alpaca_client",
        get_account=lambda: {"cash": 70000.0, "buying_power": 400000.0, "equity": 100000.0, "portfolio_value": 100000.0},
        get_positions=lambda: positions,
        get_recent_orders=lambda limit=100: [],
        submit_market_buy=lambda ticker, notional: {"id": "order-1", "status": "accepted"},
        submit_market_sell=lambda ticker, notional=None, qty=None: {"id": "order-1", "status": "accepted"},
    ):
        inserted, errors = trading_engine.run_bot_once()

    assert inserted > 0
    assert errors == 0
