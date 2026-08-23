"""Tests for the pure trading-decision logic (Product 3). No I/O — same
testability shape as test_portfolio_engine.py, plain dicts in, list out.
"""

from app.trading_engine import decide_trades, resolve_ticker

ENABLED_CONFIG = {"enabled": True, "max_trade_dollars": 1000.0, "max_trades_per_day": 5, "cash_buffer_pct": 10.0}
MODERATE_PROFILE = {"risk_tolerance": "moderate", "time_horizon": None, "primary_goal": None}


def test_resolve_ticker_parses_leading_symbol():
    assert resolve_ticker("VTI (Vanguard Total Stock Market ETF)") == "VTI"
    assert resolve_ticker("SCHD (Schwab US Dividend Equity ETF)") == "SCHD"


def test_resolve_ticker_returns_none_for_non_etf_cash_suggestion():
    assert resolve_ticker("a high-yield savings account or money market fund") is None


def test_decide_trades_returns_nothing_when_disabled():
    config = {**ENABLED_CONFIG, "enabled": False}
    positions = [{"ticker": "CASH", "shares": 1, "value": 10000.0}]
    assert decide_trades(positions, 10000.0, MODERATE_PROFILE, config, []) == []


def test_decide_trades_returns_nothing_if_already_traded_today():
    positions = [{"ticker": "CASH", "shares": 1, "value": 10000.0}]
    already = [{"id": 1, "ticker": "VTI", "notional": 100.0}]
    assert decide_trades(positions, 10000.0, MODERATE_PROFILE, ENABLED_CONFIG, already) == []


def test_decide_trades_buys_toward_underweight_stock_gap():
    # all cash vs. moderate target (60% stock) -> stock heavily underweight
    positions = [{"ticker": "CASH", "shares": 1, "value": 10000.0}]
    decisions = decide_trades(positions, 10000.0, MODERATE_PROFILE, ENABLED_CONFIG, [])
    stock_decision = next(d for d in decisions if d["asset_class"] == "stock")
    assert stock_decision["ticker"] == "VTI"
    assert stock_decision["notional"] > 0
    assert "underweight" in stock_decision["rationale"]


def test_decide_trades_never_produces_an_overweight_decision():
    # 100% stock vs. a conservative target (30% stock) -> stock is heavily
    # OVERWEIGHT, not underweight — a buy-only bot must never act on this.
    positions = [{"ticker": "AAPL", "shares": 10, "value": 10000.0}]
    conservative_profile = {**MODERATE_PROFILE, "risk_tolerance": "conservative"}
    decisions = decide_trades(positions, 500.0, conservative_profile, ENABLED_CONFIG, [])
    assert all(d["asset_class"] != "stock" for d in decisions)


def test_decide_trades_caps_at_max_trade_dollars():
    positions = [{"ticker": "CASH", "shares": 1, "value": 100000.0}]
    config = {**ENABLED_CONFIG, "max_trade_dollars": 50.0}
    decisions = decide_trades(positions, 100000.0, MODERATE_PROFILE, config, [])
    assert all(d["notional"] <= 50.0 for d in decisions)


def test_decide_trades_respects_cash_buffer():
    positions = [{"ticker": "CASH", "shares": 1, "value": 1000.0}]
    # 100% buffer -> zero investable cash -> no trades regardless of gaps
    config = {**ENABLED_CONFIG, "cash_buffer_pct": 100.0}
    assert decide_trades(positions, 1000.0, MODERATE_PROFILE, config, []) == []


def test_decide_trades_respects_max_trades_per_day_including_prior_trades():
    positions = [{"ticker": "CASH", "shares": 1, "value": 10000.0}]
    config = {**ENABLED_CONFIG, "max_trades_per_day": 1}
    # already_traded_today non-empty means decide_trades returns [] entirely
    # (day-level idempotency) — max_trades_per_day only matters within one run.
    decisions = decide_trades(positions, 10000.0, MODERATE_PROFILE, config, [])
    assert len(decisions) <= 1


def test_decide_trades_handles_multiple_simultaneous_underweight_gaps():
    # all cash vs. moderate target (60/30/10 stock/bond/cash) -> both stock and
    # bond are underweight simultaneously.
    positions = [{"ticker": "CASH", "shares": 1, "value": 10000.0}]
    config = {**ENABLED_CONFIG, "max_trades_per_day": 5, "max_trade_dollars": 5000.0}
    decisions = decide_trades(positions, 10000.0, MODERATE_PROFILE, config, [])
    asset_classes = {d["asset_class"] for d in decisions}
    assert "stock" in asset_classes
    assert "bond" in asset_classes


def test_decide_trades_skips_when_investable_cash_is_below_minimum_trade_amount():
    # A real, large gap exists (100% cash vs. a 60% stock target), but almost
    # no buying power is available to act on it — shouldn't produce a
    # near-zero trade.
    positions = [{"ticker": "CASH", "shares": 1, "value": 10000.0}]
    config = {**ENABLED_CONFIG, "cash_buffer_pct": 0.0}
    decisions = decide_trades(positions, 0.50, MODERATE_PROFILE, config, [])
    assert decisions == []
