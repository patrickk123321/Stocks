"""Trading-decision logic for Product 3 (Auto-Trading Bot).

Only Product 2's allocation-gap output drives trades — Product 1 data
(insider/congress/13F) is surfaced elsewhere in the UI as read-only context and
never reaches this module. Buy-only: an overweight gap never produces a trade
decision here, by construction (see decide_trades).

decide_trades() is a pure function (plain dicts in, list of decisions out) —
same testability shape as portfolio_engine.py, no I/O, no mocks needed. It
directly reuses portfolio_engine.compute_recommendations for the actual
allocation-gap math rather than reimplementing it. run_bot_once() is the
orchestrator that performs I/O (Alpaca + the DB) and is what the scheduler and
the manual "run now" endpoint both call.
"""

import logging
import re
from datetime import date, datetime, timezone

from app import alpaca_client, db
from app.portfolio_engine import compute_recommendations

logger = logging.getLogger("stocks.trading_engine")

# Below this, a trade isn't worth placing (small enough to not meaningfully
# close a gap, and close to Alpaca's own practical notional minimum).
MIN_TRADE_DOLLARS = 1.0

_TICKER_PREFIX_RE = re.compile(r"^([A-Z]{1,6})\s*\(")


def resolve_ticker(suggested_fund: str) -> str | None:
    """'VTI (Vanguard Total Stock Market ETF)' -> 'VTI'. Returns None for the
    non-ETF cash-class strings in SUGGESTED_FUNDS ('a high-yield savings
    account or money market fund') — not tradable via Alpaca, must be skipped
    rather than silently mis-mapped onto some other ticker."""
    match = _TICKER_PREFIX_RE.match(suggested_fund.strip())
    return match.group(1) if match else None


def decide_trades(
    positions: list[dict],
    buying_power: float,
    risk_profile: dict,
    bot_config: dict,
    already_traded_today: list[dict],
) -> list[dict]:
    """Returns [{"ticker", "notional", "asset_class", "rationale"}, ...].
    Pure — already_traded_today is passed in rather than queried here, so this
    stays testable with plain dicts and no DB access."""
    if not bot_config.get("enabled"):
        return []
    if already_traded_today:
        return []  # day-level idempotency — the bot runs at most once per calendar day

    cash_buffer_pct = bot_config.get("cash_buffer_pct", 0.0)
    investable_cash = buying_power * (1 - cash_buffer_pct / 100)
    if investable_cash <= 0:
        return []

    recs = compute_recommendations(
        positions,
        risk_profile.get("risk_tolerance", "moderate"),
        risk_profile.get("time_horizon"),
        risk_profile.get("primary_goal"),
    )
    total_value = recs["allocation"]["total_value"]
    max_trade_dollars = bot_config.get("max_trade_dollars", 0.0)
    remaining_trades = bot_config.get("max_trades_per_day", 0) - len(already_traded_today)

    decisions = []
    remaining_cash = investable_cash
    # Fixed order (stock, bond, cash) — the same order compute_recommendations
    # already iterates gaps in. Simple and deterministic, not re-sorted by gap size.
    for gap in recs["gaps"]:
        if remaining_trades <= 0:
            break
        if gap["direction"] != "underweight":
            continue  # buy-only bot — never generates a decision for an overweight gap

        gap_dollars = abs(gap["diff_pct"]) / 100 * total_value
        trade_amount = min(max_trade_dollars, remaining_cash, gap_dollars)
        if trade_amount < MIN_TRADE_DOLLARS:
            continue

        suggested = gap["suggested_funds"][0] if gap["suggested_funds"] else None
        ticker = resolve_ticker(suggested) if suggested else None
        if not ticker:
            # A cash-class gap ("a high-yield savings account...") is
            # structurally unactionable for a buy-only bot against a brokerage
            # API — skipped deliberately, logged so it isn't mistaken for a bug.
            logger.info("skipping unactionable gap (no tradable ticker): %s", gap["asset_class"])
            continue

        decisions.append({
            "ticker": ticker,
            "notional": round(trade_amount, 2),
            "asset_class": gap["asset_class"],
            "rationale": f"Closing {gap['asset_class']} underweight ({gap['message']})",
        })
        remaining_cash -= trade_amount
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
    """Orchestrator: refreshes pending fill statuses, decides today's trades
    (if the bot is enabled and hasn't already run today), submits them one at
    a time — a failure on one must not abort the rest — and logs every
    attempt. Returns (inserted, errors), shaped to plug directly into
    scheduler._run_refresh (inserted = trades placed, errors = trades that
    failed to submit)."""
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
    # entirely. On an all-cash account that makes total_value 0, which makes
    # every gap's dollar-sizing round to $0 and silently skip — the single
    # most common starting state for this bot would otherwise never trade.
    holdings = positions + [{"ticker": "CASH", "shares": None, "value": account["cash"]}]

    decisions = decide_trades(holdings, account["buying_power"], risk_profile, bot_config, already_traded_today)

    inserted = 0
    errors = 0
    for decision in decisions:
        placed_at = datetime.now(timezone.utc).isoformat()
        base_row = {
            "run_date": today,
            "ticker": decision["ticker"],
            "notional": decision["notional"],
            "asset_class": decision["asset_class"],
            "rationale": decision["rationale"],
            "placed_at": placed_at,
        }
        try:
            order = alpaca_client.submit_market_buy(decision["ticker"], decision["notional"])
            db.insert_bot_trade({**base_row, "status": "submitted", "alpaca_order_id": order["id"]})
            inserted += 1
        except alpaca_client.AlpacaOrderError as e:
            db.insert_bot_trade({**base_row, "status": "failed", "error_message": str(e)})
            errors += 1

    return inserted, errors
