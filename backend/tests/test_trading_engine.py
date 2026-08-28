"""Tests for the pure trading-decision logic (Product 3 v2). No I/O — same
testability shape as test_portfolio_engine.py, plain dicts in, list out.
"""

from app.trading_engine import decide_trades, rank_holdings_for_overweight_sell, resolve_ticker

ENABLED_CONFIG = {
    "enabled": True,
    "max_trades_per_day": 5,
    "cash_buffer_pct": 10.0,
    "standard_trade_pct": 10.0,
    "high_conviction_trade_pct": 20.0,
    "position_cap_pct": 20.0,
}
MODERATE_PROFILE = {"risk_tolerance": "moderate", "time_horizon": None, "primary_goal": None}
NO_SIGNALS: dict = {}


def gap_candidate(direction: str, asset_class: str, diff_pct: float, suggested_funds=None) -> dict:
    candidate_type = "gap_underweight" if direction == "underweight" else "gap_overweight"
    return {
        "candidate_key": f"{candidate_type}:{asset_class}",
        "candidate_type": candidate_type,
        "ticker": None,
        "asset_class": asset_class,
        "signal_strength": None,
        "diff_pct": diff_pct,
        "detail": {"message": f"{asset_class} {direction}", "suggested_funds": suggested_funds or ["VTI (Vanguard Total Stock Market ETF)"]},
    }


def stock_candidate(direction: str, ticker: str, strength: int) -> dict:
    candidate_type = "stock_buy" if direction == "buy" else "stock_sell"
    return {
        "candidate_key": f"{candidate_type}:{ticker}",
        "candidate_type": candidate_type,
        "ticker": ticker,
        "asset_class": "stock",
        "signal_strength": strength,
        "diff_pct": None,
        "detail": {"insiders": ["Alice"], "congress": ["Bob"]},
    }


def test_resolve_ticker_parses_leading_symbol():
    assert resolve_ticker("VTI (Vanguard Total Stock Market ETF)") == "VTI"
    assert resolve_ticker("SCHD (Schwab US Dividend Equity ETF)") == "SCHD"


def test_resolve_ticker_returns_none_for_non_etf_cash_suggestion():
    assert resolve_ticker("a high-yield savings account or money market fund") is None


def test_decide_trades_returns_nothing_when_disabled():
    config = {**ENABLED_CONFIG, "enabled": False}
    positions = [{"ticker": "CASH", "shares": 1, "value": 10000.0}]
    candidates = [gap_candidate("underweight", "stock", -60.0)]
    assert decide_trades(positions, 10000.0, MODERATE_PROFILE, config, [], candidates, NO_SIGNALS) == []


def test_decide_trades_returns_nothing_if_already_traded_today():
    positions = [{"ticker": "CASH", "shares": 1, "value": 10000.0}]
    already = [{"id": 1, "ticker": "VTI", "notional": 100.0}]
    candidates = [gap_candidate("underweight", "stock", -60.0)]
    assert decide_trades(positions, 10000.0, MODERATE_PROFILE, ENABLED_CONFIG, already, candidates, NO_SIGNALS) == []


def test_decide_trades_ignores_a_gap_that_is_not_in_persisted_candidates():
    # Not persistence-confirmed yet (first day seen) — must not trade on it.
    positions = [{"ticker": "CASH", "shares": 1, "value": 10000.0}]
    assert decide_trades(positions, 10000.0, MODERATE_PROFILE, ENABLED_CONFIG, [], [], NO_SIGNALS) == []


# --- Tier (d): underweight gap buys ---

def test_decide_trades_buys_toward_persisted_underweight_gap():
    positions = [{"ticker": "CASH", "shares": 1, "value": 10000.0}]
    candidates = [gap_candidate("underweight", "stock", -60.0)]
    decisions = decide_trades(positions, 10000.0, MODERATE_PROFILE, ENABLED_CONFIG, [], candidates, NO_SIGNALS)
    stock_decision = next(d for d in decisions if d["asset_class"] == "stock")
    assert stock_decision["ticker"] == "VTI"
    assert stock_decision["side"] == "buy"
    assert stock_decision["trigger_type"] == "gap_underweight"
    assert stock_decision["notional"] > 0


def test_decide_trades_underweight_buy_respects_position_cap_room():
    # Already holding VTI at exactly the 20% cap -> no room to buy more.
    positions = [
        {"ticker": "VTI", "shares": 10, "value": 2000.0},
        {"ticker": "CASH", "shares": 1, "value": 8000.0},
    ]
    candidates = [gap_candidate("underweight", "stock", -60.0)]
    decisions = decide_trades(positions, 10000.0, MODERATE_PROFILE, ENABLED_CONFIG, [], candidates, NO_SIGNALS)
    assert all(d["ticker"] != "VTI" for d in decisions if d["trigger_type"] == "gap_underweight")


def test_decide_trades_underweight_buy_caps_at_standard_trade_pct():
    positions = [{"ticker": "CASH", "shares": 1, "value": 100000.0}]
    config = {**ENABLED_CONFIG, "standard_trade_pct": 5.0}
    candidates = [gap_candidate("underweight", "stock", -60.0)]
    decisions = decide_trades(positions, 100000.0, MODERATE_PROFILE, config, [], candidates, NO_SIGNALS)
    stock_decision = next(d for d in decisions if d["asset_class"] == "stock")
    assert stock_decision["notional"] <= 0.05 * 100000.0 + 0.01


def test_decide_trades_never_acts_on_an_overweight_gap_via_tier_d():
    # 100% stock vs. a conservative target (30%) -> stock is OVERWEIGHT — the
    # underweight-buy tier must never touch it (it's tier (c)'s job, and even
    # then only sells, never buys).
    positions = [{"ticker": "AAPL", "shares": 10, "value": 10000.0}]
    conservative_profile = {**MODERATE_PROFILE, "risk_tolerance": "conservative"}
    candidates = [gap_candidate("overweight", "stock", 70.0)]
    decisions = decide_trades(positions, 500.0, conservative_profile, ENABLED_CONFIG, [], candidates, NO_SIGNALS)
    assert all(d["side"] != "buy" or d["asset_class"] != "stock" for d in decisions)


def test_decide_trades_respects_cash_buffer():
    positions = [{"ticker": "CASH", "shares": 1, "value": 1000.0}]
    config = {**ENABLED_CONFIG, "cash_buffer_pct": 100.0}  # zero investable cash
    candidates = [gap_candidate("underweight", "stock", -60.0)]
    decisions = decide_trades(positions, 1000.0, MODERATE_PROFILE, config, [], candidates, NO_SIGNALS)
    assert all(d["trigger_type"] != "gap_underweight" for d in decisions)


def test_decide_trades_respects_max_trades_per_day_including_prior_trades():
    positions = [{"ticker": "CASH", "shares": 1, "value": 10000.0}]
    config = {**ENABLED_CONFIG, "max_trades_per_day": 1}
    candidates = [gap_candidate("underweight", "stock", -60.0), gap_candidate("underweight", "bond", -30.0)]
    decisions = decide_trades(positions, 10000.0, MODERATE_PROFILE, config, [], candidates, NO_SIGNALS)
    assert len(decisions) <= 1


def test_decide_trades_handles_multiple_simultaneous_underweight_gaps():
    positions = [{"ticker": "CASH", "shares": 1, "value": 10000.0}]
    config = {**ENABLED_CONFIG, "max_trades_per_day": 5}
    candidates = [
        gap_candidate("underweight", "stock", -60.0, ["VTI (Vanguard Total Stock Market ETF)"]),
        gap_candidate("underweight", "bond", -30.0, ["BND (Vanguard Total Bond Market ETF)"]),
    ]
    decisions = decide_trades(positions, 10000.0, MODERATE_PROFILE, config, [], candidates, NO_SIGNALS)
    asset_classes = {d["asset_class"] for d in decisions}
    assert "stock" in asset_classes
    assert "bond" in asset_classes


def test_decide_trades_skips_when_investable_cash_is_below_minimum_trade_amount():
    positions = [{"ticker": "CASH", "shares": 1, "value": 10000.0}]
    config = {**ENABLED_CONFIG, "cash_buffer_pct": 0.0}
    candidates = [gap_candidate("underweight", "stock", -60.0)]
    decisions = decide_trades(positions, 0.50, MODERATE_PROFILE, config, [], candidates, NO_SIGNALS)
    assert decisions == []


# --- Tier (e): cluster-buy candidates ---

def test_decide_trades_buys_a_standard_conviction_cluster_candidate():
    positions = [{"ticker": "CASH", "shares": 1, "value": 100000.0}]
    candidates = [stock_candidate("buy", "AAPL", strength=2)]
    decisions = decide_trades(positions, 100000.0, MODERATE_PROFILE, ENABLED_CONFIG, [], candidates, NO_SIGNALS)
    d = next(x for x in decisions if x["ticker"] == "AAPL")
    assert d["side"] == "buy"
    assert d["trigger_type"] == "signal_buy"
    assert d["signal_strength"] == 2
    assert d["notional"] <= 0.10 * 100000.0 + 0.01  # standard 10% tier


def test_decide_trades_high_conviction_candidate_gets_larger_cap():
    positions = [{"ticker": "CASH", "shares": 1, "value": 100000.0}]
    candidates = [stock_candidate("buy", "AAPL", strength=5)]  # HIGH_CONVICTION_THRESHOLD
    decisions = decide_trades(positions, 100000.0, MODERATE_PROFILE, ENABLED_CONFIG, [], candidates, NO_SIGNALS)
    d = next(x for x in decisions if x["ticker"] == "AAPL")
    assert d["notional"] > 0.10 * 100000.0  # exceeds the standard 10% cap
    assert d["notional"] <= 0.20 * 100000.0 + 0.01  # within the 20% high-conviction cap


def test_decide_trades_cluster_buy_respects_position_cap():
    positions = [
        {"ticker": "AAPL", "shares": 10, "value": 1900.0},
        {"ticker": "CASH", "shares": 1, "value": 8100.0},
    ]  # AAPL already at 19% of a $10k portfolio, cap is 20%
    candidates = [stock_candidate("buy", "AAPL", strength=5)]
    decisions = decide_trades(positions, 10000.0, MODERATE_PROFILE, ENABLED_CONFIG, [], candidates, NO_SIGNALS)
    aapl_decisions = [d for d in decisions if d["ticker"] == "AAPL" and d["trigger_type"] == "signal_buy"]
    if aapl_decisions:
        assert aapl_decisions[0]["notional"] <= 100.0 + 0.01  # only ~1% of $10k room left under the cap


# --- Tier (a): 20% position-cap breach ---

def test_decide_trades_trims_an_individual_stock_over_the_cap():
    positions = [
        {"ticker": "AAPL", "shares": 10, "value": 3000.0},  # 30% of a $10k portfolio
        {"ticker": "CASH", "shares": 1, "value": 7000.0},
    ]
    decisions = decide_trades(positions, 7000.0, MODERATE_PROFILE, ENABLED_CONFIG, [], [], NO_SIGNALS)
    d = next(x for x in decisions if x["ticker"] == "AAPL")
    assert d["side"] == "sell"
    assert d["trigger_type"] == "cap_breach"
    assert d["notional"] == 1000.0  # trims 3000 -> 2000 (20% of 10000)


def test_decide_trades_cap_breach_is_not_persistence_gated():
    # No candidates passed in at all — the cap-breach check must still fire.
    positions = [
        {"ticker": "AAPL", "shares": 10, "value": 3000.0},
        {"ticker": "CASH", "shares": 1, "value": 7000.0},
    ]
    decisions = decide_trades(positions, 7000.0, MODERATE_PROFILE, ENABLED_CONFIG, [], [], NO_SIGNALS)
    assert any(d["ticker"] == "AAPL" and d["trigger_type"] == "cap_breach" for d in decisions)


def test_decide_trades_exempts_diversified_funds_from_the_position_cap():
    # VTI at 50% of the portfolio is exactly what a moderate/aggressive
    # allocation's core stock holding looks like — must NOT be trimmed, or the
    # bot would fight its own underweight-buy logic every run.
    positions = [
        {"ticker": "VTI", "shares": 10, "value": 5000.0},
        {"ticker": "CASH", "shares": 1, "value": 5000.0},
    ]
    decisions = decide_trades(positions, 5000.0, MODERATE_PROFILE, ENABLED_CONFIG, [], [], NO_SIGNALS)
    assert all(d["ticker"] != "VTI" for d in decisions)


# --- Tier (b): negative signal on a held stock -> full exit ---

def test_decide_trades_exits_a_held_stock_on_a_persisted_negative_signal():
    positions = [
        {"ticker": "AAPL", "shares": 10, "value": 1000.0},
        {"ticker": "CASH", "shares": 1, "value": 9000.0},
    ]
    candidates = [stock_candidate("sell", "AAPL", strength=3)]
    decisions = decide_trades(positions, 9000.0, MODERATE_PROFILE, ENABLED_CONFIG, [], candidates, NO_SIGNALS)
    d = next(x for x in decisions if x["ticker"] == "AAPL")
    assert d["side"] == "sell"
    assert d["trigger_type"] == "signal_sell"
    assert d["qty"] == 10  # full position, by share count, not a dollar notional
    assert d["notional"] == 1000.0  # still logged for the trade history


def test_decide_trades_negative_signal_on_unheld_ticker_produces_no_decision():
    positions = [{"ticker": "CASH", "shares": 1, "value": 10000.0}]
    candidates = [stock_candidate("sell", "AAPL", strength=3)]  # not held
    decisions = decide_trades(positions, 10000.0, MODERATE_PROFILE, ENABLED_CONFIG, [], candidates, NO_SIGNALS)
    assert all(d["ticker"] != "AAPL" for d in decisions)


# --- Same-ticker exclusion across tiers ---

def test_decide_trades_never_gives_a_ticker_two_decisions_in_one_run():
    # AAPL is simultaneously over the cap (tier a) AND has a negative signal
    # (tier b) — must only get ONE decision (the higher-priority tier a).
    positions = [
        {"ticker": "AAPL", "shares": 10, "value": 3000.0},
        {"ticker": "CASH", "shares": 1, "value": 7000.0},
    ]
    candidates = [stock_candidate("sell", "AAPL", strength=3)]
    decisions = decide_trades(positions, 7000.0, MODERATE_PROFILE, ENABLED_CONFIG, [], candidates, NO_SIGNALS)
    aapl_decisions = [d for d in decisions if d["ticker"] == "AAPL"]
    assert len(aapl_decisions) == 1
    assert aapl_decisions[0]["trigger_type"] == "cap_breach"


# --- rank_holdings_for_overweight_sell ---

def test_rank_holdings_sells_no_activity_positions_first():
    holdings = [
        {"ticker": "VTI", "value": 1000.0},
        {"ticker": "MSFT", "value": 500.0},
    ]
    signals = {"MSFT": {"buy_strength": 3, "sell_strength": 0}}  # fresh positive signal
    ranked = rank_holdings_for_overweight_sell(holdings, signals)
    assert [h["ticker"] for h in ranked] == ["VTI", "MSFT"]  # no-activity VTI sold first


def test_rank_holdings_negative_signal_sells_before_positive_signal():
    holdings = [
        {"ticker": "AAPL", "value": 500.0},  # positive signal
        {"ticker": "TSLA", "value": 500.0},  # negative signal
    ]
    signals = {
        "AAPL": {"buy_strength": 3, "sell_strength": 0},
        "TSLA": {"buy_strength": 0, "sell_strength": 2},
    }
    ranked = rank_holdings_for_overweight_sell(holdings, signals)
    assert [h["ticker"] for h in ranked] == ["TSLA", "AAPL"]


def test_rank_holdings_ties_broken_by_largest_position_first():
    holdings = [
        {"ticker": "A", "value": 100.0},
        {"ticker": "B", "value": 900.0},
    ]
    ranked = rank_holdings_for_overweight_sell(holdings, {})
    assert [h["ticker"] for h in ranked] == ["B", "A"]


# --- Tier (c): overweight gap rebalancing ---

def test_decide_trades_trims_weakest_signal_position_for_overweight_gap():
    positions = [
        {"ticker": "VTI", "shares": 10, "value": 4000.0},   # no signal data
        {"ticker": "AAPL", "shares": 10, "value": 4000.0},  # fresh positive signal
        {"ticker": "CASH", "shares": 1, "value": 2000.0},
    ]
    signals = {"AAPL": {"buy_strength": 3, "sell_strength": 0}, "VTI": {"buy_strength": 0, "sell_strength": 0}}
    candidates = [gap_candidate("overweight", "stock", 20.0)]
    decisions = decide_trades(positions, 2000.0, MODERATE_PROFILE, ENABLED_CONFIG, [], candidates, signals)
    overweight_sells = [d for d in decisions if d["trigger_type"] == "gap_overweight"]
    assert overweight_sells
    assert overweight_sells[0]["ticker"] == "VTI"  # weaker signal sold before AAPL
