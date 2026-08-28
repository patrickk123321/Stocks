"""Trading-decision logic for Product 3 (Auto-Trading Bot) — v2.

v1 was buy-only and only reacted to Product 2's allocation gaps. v2 adds:
individual-stock buying/selling driven by Product 1 (insider/congress trading
cluster) signals, a 20%-of-portfolio position concentration cap enforced by
selling, and full rebalancing (both directions of Product 2's allocation gaps,
not just underweight). No candidate — gap or signal — is acted on the first day
it's observed; it must persist across 2 consecutive daily runs first (see
db.bot_signal_observations / get_prior_observation_run_date).

Five decision tiers, evaluated in priority order every run; a ticker gets at
most one decision per run (tracked via `decided_tickers`, checked at each tier):
  (a) 20% position-cap breach — sell the excess, not persistence-gated (a
      safety cap shouldn't wait for confirmation). Restricted to individual
      stocks bought via signal (tiers b/e) — the fixed diversified funds
      Product 2 rebalances into (VTI, BND, etc.) are deliberately EXEMPT: since
      tier (d) always buys the same first-choice fund for a whole asset class,
      a passive 60% stock target would otherwise permanently fight the cap,
      buying and immediately re-selling the same core holding every run.
  (b) negative Product 1 signal on a held stock -> full exit (thesis broken).
  (c) overweight allocation-gap rebalancing — sell the weakest-signal position
      in that asset class first.
  (d) underweight allocation-gap buys (v1's core logic, now persistence-gated
      and position-cap-aware).
  (e) Product 1 cluster-buy candidates — new individual-stock buys, sized by a
      10%/20% conviction split.

decide_trades() stays a pure function (plain dicts in, list of decisions out,
same testability convention as portfolio_engine.py and v1) — it takes the
already persistence-filtered candidates and a signal-strength lookup as plain
data rather than touching the DB or Product 1 tables itself. gather_candidates()
is the I/O step that builds those candidates. run_bot_once() is the top-level
orchestrator (Alpaca + DB I/O) the scheduler and the manual "run now" endpoint
both call.
"""

import logging
import re
from datetime import date, datetime, timedelta, timezone

from app import alpaca_client, db, signal_engine
from app.data.ticker_reference import get_ticker_info
from app.portfolio_engine import SUGGESTED_FUNDS, compute_allocation, compute_recommendations

logger = logging.getLogger("stocks.trading_engine")

# Below this, a trade isn't worth placing (small enough to not meaningfully
# move a position, and close to Alpaca's own practical notional minimum).
MIN_TRADE_DOLLARS = 1.0

_TICKER_PREFIX_RE = re.compile(r"^([A-Z]{1,6})\s*\(")


def resolve_ticker(suggested_fund: str) -> str | None:
    """'VTI (Vanguard Total Stock Market ETF)' -> 'VTI'. Returns None for the
    non-ETF cash-class strings in SUGGESTED_FUNDS ('a high-yield savings
    account or money market fund') — not tradable via Alpaca, must be skipped
    rather than silently mis-mapped onto some other ticker."""
    match = _TICKER_PREFIX_RE.match(suggested_fund.strip())
    return match.group(1) if match else None


# The fixed set of diversified funds Product 2 rebalances into — resolved once
# at import time. Exempt from the 20% position cap (see tier (a) above).
_DIVERSIFIED_FUND_TICKERS = {
    ticker
    for by_goal in SUGGESTED_FUNDS.values()
    for funds in by_goal.values()
    for fund in funds
    if (ticker := resolve_ticker(fund))
}


def rank_holdings_for_overweight_sell(holdings_in_class: list[dict], signal_map: dict[str, dict[str, int]]) -> list[dict]:
    """Sorts a single asset class's holdings sell-first to sell-last: no recent
    Product 1 activity (includes diversified funds like VTI/BND, which
    structurally can never have per-company insider/congress data) sells
    before a position with a fresh negative signal, which sells before one
    with a fresh positive signal — tiebroken by largest position first within
    each tier."""
    def tier(ticker: str) -> int:
        s = signal_map.get(ticker, {"buy_strength": 0, "sell_strength": 0})
        if s["buy_strength"] > 0:
            return 2
        if s["sell_strength"] > 0:
            return 1
        return 0

    return sorted(holdings_in_class, key=lambda h: (tier(h["ticker"]), -(h.get("value") or 0)))


def gather_candidates(holdings: list[dict], positions: list[dict], risk_profile: dict) -> list[dict]:
    """I/O: computes Product 2's allocation gaps (both directions) and Product 1
    signal candidates (buy candidates across all tickers, sell signals
    restricted to currently-held tickers). Returns the normalized candidate
    list — NOT yet filtered by persistence, see run_bot_once for that step.
    Testable against a temp DB with seeded insider/congress rows; no Alpaca
    access needed."""
    candidates: list[dict] = []

    recs = compute_recommendations(
        holdings,
        risk_profile.get("risk_tolerance", "moderate"),
        risk_profile.get("time_horizon"),
        risk_profile.get("primary_goal"),
    )
    for gap in recs["gaps"]:
        candidate_type = "gap_underweight" if gap["direction"] == "underweight" else "gap_overweight"
        candidates.append({
            "candidate_key": f"{candidate_type}:{gap['asset_class']}",
            "candidate_type": candidate_type,
            "ticker": None,
            "asset_class": gap["asset_class"],
            "signal_strength": None,
            "diff_pct": gap["diff_pct"],
            "detail": {"message": gap["message"], "suggested_funds": gap.get("suggested_funds", [])},
        })

    lookback_start = (date.today() - timedelta(days=signal_engine.SIGNAL_LOOKBACK_DAYS)).isoformat()
    held_tickers = [p["ticker"] for p in positions if p.get("ticker")]

    for c in signal_engine.get_buy_candidates(lookback_start):
        candidates.append({
            "candidate_key": f"stock_buy:{c['ticker']}",
            "candidate_type": "stock_buy",
            "ticker": c["ticker"],
            "asset_class": "stock",
            "signal_strength": c["signal_strength"],
            "diff_pct": None,
            "detail": {"insiders": c["insiders"], "congress": c["congress"]},
        })

    for c in signal_engine.get_sell_signals_for_held(lookback_start, held_tickers):
        candidates.append({
            "candidate_key": f"stock_sell:{c['ticker']}",
            "candidate_type": "stock_sell",
            "ticker": c["ticker"],
            "asset_class": "stock",
            "signal_strength": c["signal_strength"],
            "diff_pct": None,
            "detail": {"insiders": c["insiders"], "congress": c["congress"]},
        })

    return candidates


def decide_trades(
    positions: list[dict],
    buying_power: float,
    risk_profile: dict,
    bot_config: dict,
    already_traded_today: list[dict],
    persisted_candidates: list[dict],
    signal_strength_map: dict[str, dict[str, int]],
) -> list[dict]:
    """Returns a list of trade decisions across the 5 priority tiers described
    in the module docstring. Pure — persisted_candidates and
    signal_strength_map are plain data (see gather_candidates / signal_engine),
    no DB or Alpaca access happens here. `positions` includes a synthesized
    CASH holding (see run_bot_once) so total_value reflects the whole account."""
    if not bot_config.get("enabled"):
        return []
    if already_traded_today:
        return []  # day-level idempotency — the bot runs at most once per calendar day

    allocation = compute_allocation(positions)
    total_value = allocation["total_value"]
    if total_value <= 0:
        return []
    positions_by_ticker = {p["ticker"]: p for p in positions if p.get("ticker")}

    cash_buffer_pct = bot_config.get("cash_buffer_pct", 0.0)
    investable_cash = buying_power * (1 - cash_buffer_pct / 100)

    standard_pct = bot_config.get("standard_trade_pct", 10.0)
    high_conviction_pct = bot_config.get("high_conviction_trade_pct", 20.0)
    position_cap_pct = bot_config.get("position_cap_pct", 20.0)

    def trade_cap_dollars(pct: float) -> float:
        return pct / 100 * buying_power

    decisions: list[dict] = []
    decided_tickers: set[str] = set()
    remaining_trades = bot_config.get("max_trades_per_day", 0) - len(already_traded_today)

    def budget_left() -> bool:
        return remaining_trades > 0

    # --- Tier (a): 20% position-cap breach on an individual stock ---
    for ticker, pos in positions_by_ticker.items():
        if not budget_left():
            break
        if ticker == "CASH" or ticker in decided_tickers or ticker in _DIVERSIFIED_FUND_TICKERS:
            continue
        value = pos.get("value") or 0
        pct = value / total_value * 100
        if pct <= position_cap_pct:
            continue
        excess = value - (position_cap_pct / 100 * total_value)
        if excess < MIN_TRADE_DOLLARS:
            continue
        decisions.append({
            "ticker": ticker, "side": "sell", "notional": round(excess, 2), "qty": None,
            "asset_class": "stock", "trigger_type": "cap_breach", "signal_strength": None,
            "rationale": f"Trimming {ticker} from {pct:.0f}% to {position_cap_pct:.0f}% of portfolio (position cap).",
        })
        decided_tickers.add(ticker)
        remaining_trades -= 1

    # --- Tier (b): negative Product 1 signal on a held stock -> full exit ---
    for c in persisted_candidates:
        if not budget_left():
            break
        if c["candidate_type"] != "stock_sell":
            continue
        ticker = c["ticker"]
        if ticker in decided_tickers:
            continue
        pos = positions_by_ticker.get(ticker)
        if not pos or not pos.get("shares"):
            continue  # not actually held (or no share count) — nothing to sell
        decisions.append({
            "ticker": ticker, "side": "sell", "notional": round(pos.get("value") or 0, 2), "qty": pos["shares"],
            "asset_class": "stock", "trigger_type": "signal_sell", "signal_strength": c["signal_strength"],
            "rationale": f"Exiting {ticker} in full — {c['signal_strength']} insiders/congress members sold within the last 30 days.",
        })
        decided_tickers.add(ticker)
        remaining_trades -= 1

    # --- Tier (c): overweight allocation-gap rebalancing ---
    for c in persisted_candidates:
        if not budget_left():
            break
        if c["candidate_type"] != "gap_overweight":
            continue
        asset_class = c["asset_class"]
        gap_dollars = abs(c["diff_pct"]) / 100 * total_value
        class_positions = [
            p for t, p in positions_by_ticker.items()
            if t not in decided_tickers and t != "CASH" and get_ticker_info(t)["asset_class"] == asset_class
        ]
        ranked = rank_holdings_for_overweight_sell(class_positions, signal_strength_map)
        remaining_gap = gap_dollars
        for p in ranked:
            if not budget_left() or remaining_gap < MIN_TRADE_DOLLARS:
                break
            sell_amount = min(trade_cap_dollars(standard_pct), remaining_gap, p.get("value") or 0)
            if sell_amount < MIN_TRADE_DOLLARS:
                continue
            decisions.append({
                "ticker": p["ticker"], "side": "sell", "notional": round(sell_amount, 2), "qty": None,
                "asset_class": asset_class, "trigger_type": "gap_overweight", "signal_strength": None,
                "rationale": f"Trimming {p['ticker']} to close {asset_class} overweight ({c['detail'].get('message', '')}).",
            })
            decided_tickers.add(p["ticker"])
            remaining_gap -= sell_amount
            remaining_trades -= 1

    # --- Tier (d): underweight allocation-gap buys ---
    for c in persisted_candidates:
        if not budget_left():
            break
        if c["candidate_type"] != "gap_underweight":
            continue
        asset_class = c["asset_class"]
        gap_dollars = abs(c["diff_pct"]) / 100 * total_value
        suggested_funds = c["detail"].get("suggested_funds", [])
        suggested = suggested_funds[0] if suggested_funds else None
        ticker = resolve_ticker(suggested) if suggested else None
        if not ticker or ticker in decided_tickers:
            # A cash-class gap ("a high-yield savings account...") is
            # structurally unactionable for this bot — skipped deliberately.
            if not ticker:
                logger.info("skipping unactionable gap (no tradable ticker): %s", asset_class)
            continue
        current_value = (positions_by_ticker.get(ticker) or {}).get("value") or 0
        room_under_cap = max(0.0, (position_cap_pct / 100 * total_value) - current_value)
        trade_amount = min(trade_cap_dollars(standard_pct), investable_cash, gap_dollars, room_under_cap)
        if trade_amount < MIN_TRADE_DOLLARS:
            continue
        decisions.append({
            "ticker": ticker, "side": "buy", "notional": round(trade_amount, 2), "qty": None,
            "asset_class": asset_class, "trigger_type": "gap_underweight", "signal_strength": None,
            "rationale": f"Closing {asset_class} underweight ({c['detail'].get('message', '')}).",
        })
        decided_tickers.add(ticker)
        investable_cash -= trade_amount
        remaining_trades -= 1

    # --- Tier (e): Product 1 cluster-buy candidates ---
    for c in persisted_candidates:
        if not budget_left():
            break
        if c["candidate_type"] != "stock_buy":
            continue
        ticker = c["ticker"]
        if ticker in decided_tickers:
            continue
        current_value = (positions_by_ticker.get(ticker) or {}).get("value") or 0
        room_under_cap = max(0.0, (position_cap_pct / 100 * total_value) - current_value)
        if room_under_cap < MIN_TRADE_DOLLARS:
            continue
        pct = high_conviction_pct if c["signal_strength"] >= signal_engine.HIGH_CONVICTION_THRESHOLD else standard_pct
        trade_amount = min(trade_cap_dollars(pct), investable_cash, room_under_cap)
        if trade_amount < MIN_TRADE_DOLLARS:
            continue
        decisions.append({
            "ticker": ticker, "side": "buy", "notional": round(trade_amount, 2), "qty": None,
            "asset_class": "stock", "trigger_type": "signal_buy", "signal_strength": c["signal_strength"],
            "rationale": f"Buying {ticker} — {c['signal_strength']} insiders/congress members bought within the last 30 days.",
        })
        decided_tickers.add(ticker)
        investable_cash -= trade_amount
        remaining_trades -= 1

    return decisions


def refresh_pending_trade_statuses() -> None:
    """Polls Alpaca for the real status of trades still marked "submitted" and
    updates them — there's no inbound webhook in this app, so this is how a
    fill eventually shows up in the trade history."""
    pending = db.get_submitted_bot_trades()
    if not pending:
        return
    try:
        recent_orders = {o["id"]: o for o in alpaca_client.get_recent_orders(limit=100)}
    except alpaca_client.AlpacaNotConfiguredError:
        return
    for trade in pending:
        order = recent_orders.get(trade["alpaca_order_id"])
        if not order:
            continue
        if order["status"] == "filled":
            db.update_bot_trade_status(
                trade["id"], "filled",
                filled_at=order["filled_at"], filled_avg_price=order["filled_avg_price"],
            )
        elif order["status"] in ("rejected", "canceled", "expired"):
            db.update_bot_trade_status(trade["id"], "rejected")


def run_bot_once() -> tuple[int, int]:
    """Orchestrator: refreshes pending fill statuses, gathers and logs today's
    candidates, filters to ones that also persisted from the prior logged run,
    decides today's trades (if enabled and not already run today), submits
    them one at a time — a failure on one must not abort the rest — and logs
    every attempt. Returns (inserted, errors), shaped to plug directly into
    scheduler._run_refresh."""
    refresh_pending_trade_statuses()

    today = date.today().isoformat()
    bot_config = db.get_bot_config()
    risk_profile = db.get_risk_profile()
    if not bot_config or not bot_config.get("enabled") or not risk_profile:
        return 0, 0  # bot off, or no risk profile set up yet — nothing to do, not a failure

    already_traded_today = db.get_trades_for_run_date(today)
    try:
        account = alpaca_client.get_account()
        positions = alpaca_client.get_positions()
    except alpaca_client.AlpacaNotConfiguredError:
        return 0, 0  # not configured — same "nothing to do" treatment, not a failure

    # get_all_positions() only returns invested positions — a brand-new (or
    # partially-cash) paper account's uninvested cash isn't a "position" at
    # all, so without this compute_allocation's total_value would exclude it
    # entirely (see this exact bug found live-testing v1).
    holdings = positions + [{"ticker": "CASH", "shares": None, "value": account["cash"]}]

    today_candidates = gather_candidates(holdings, positions, risk_profile)
    db.log_bot_candidates(today, today_candidates)

    prior_date = db.get_prior_observation_run_date(today)
    prior_keys = db.get_observed_candidate_keys(prior_date) if prior_date else set()
    persisted_candidates = [c for c in today_candidates if c["candidate_key"] in prior_keys]

    lookback_start = (date.today() - timedelta(days=signal_engine.SIGNAL_LOOKBACK_DAYS)).isoformat()
    held_tickers = [p["ticker"] for p in positions if p.get("ticker")]
    signal_strength_map = signal_engine.get_signal_strength_map(lookback_start, held_tickers)

    decisions = decide_trades(
        holdings, account["buying_power"], risk_profile, bot_config,
        already_traded_today, persisted_candidates, signal_strength_map,
    )

    inserted = 0
    errors = 0
    for decision in decisions:
        placed_at = datetime.now(timezone.utc).isoformat()
        base_row = {
            "run_date": today,
            "ticker": decision["ticker"],
            "side": decision["side"],
            "notional": decision["notional"],
            "asset_class": decision["asset_class"],
            "rationale": decision["rationale"],
            "placed_at": placed_at,
            "trigger_type": decision["trigger_type"],
            "signal_strength": decision["signal_strength"],
        }
        try:
            if decision["side"] == "buy":
                order = alpaca_client.submit_market_buy(decision["ticker"], decision["notional"])
            elif decision.get("qty") is not None:
                order = alpaca_client.submit_market_sell(decision["ticker"], qty=decision["qty"])
            else:
                order = alpaca_client.submit_market_sell(decision["ticker"], notional=decision["notional"])
            db.insert_bot_trade({**base_row, "status": "submitted", "alpaca_order_id": order["id"]})
            inserted += 1
        except alpaca_client.AlpacaOrderError as e:
            db.insert_bot_trade({**base_row, "status": "failed", "error_message": str(e)})
            errors += 1

    return inserted, errors
