"""Buy-event-driven watchlist alerts. Right after each congress-trade or
institutions (13F) refresh finds new rows (see app/scheduler.py's
run_congress_refresh / run_daily_refresh), check_and_notify checks the new
rows against two independent kinds of favorites and records an alert for
every match — there's no separate time-based alert schedule; alerting is
driven entirely by new-row events, at whatever cadence each refresh runs.

Two match types, both handled here:
- Ticker favorites (congress only): a new Purchase in a watchlisted ticker,
  regardless of who made it.
- Actor favorites (congress + institutions): any new row at all from a
  favorited congress member or institution/filer, buy or sell — congress
  rows carry a real transaction_type; institutional_holdings rows don't
  (13F reports quarterly positions, not discrete transactions), so for
  institutions this means "a new holding was disclosed by this filer."

A single row can satisfy both a ticker and an actor favorite for the same
user (e.g. favoriting both a ticker and the member who then buys it) —
candidates are deduped by (user_id, row_id) before the durable dedupe
check, so that still produces exactly one alert.

The in-app alert (alerts_sent row, surfaced via /api/watchlist/alerts) is
the source of truth and is recorded regardless of email outcome. Email
(app/notifications/email.py) is a best-effort bonus on top — it currently
no-ops (logs and skips) whenever RESEND_API_KEY/RESEND_FROM_EMAIL aren't
configured, which is fine; a failed or skipped send never blocks the in-app
alert from showing up.
"""

import logging

from app.db import (
    filter_unalerted,
    get_watchlist_actor_matches,
    get_watchlist_matches,
    record_alerts_sent,
)
from app.notifications.email import send_email

logger = logging.getLogger("stocks.alerts")

# A set, not a single hardcoded string, so widening ticker alerts to sales/
# exchanges later is a one-line change here rather than a rewrite of
# check_and_notify. Only applies to ticker favorites — actor favorites
# already fire on any transaction type by design.
ALERT_TRANSACTION_TYPES = {"Purchase"}


def _group_by(rows: list[dict], key: str) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        value = row.get(key)
        if value:
            grouped.setdefault(value, []).append(row)
    return grouped


def check_and_notify(source: str, new_rows: list[dict]) -> None:
    if not new_rows:
        return

    # (user_id, row_id) -> (email, row) — a dict rather than a list so a row
    # matching both a ticker and an actor favorite collapses to one entry.
    candidates: dict[tuple[str, int], tuple[str, dict]] = {}

    if source == "congress":
        purchases = [row for row in new_rows if row.get("transaction_type") in ALERT_TRANSACTION_TYPES and row.get("ticker")]
        by_ticker = _group_by(purchases, "ticker")
        if by_ticker:
            for match in get_watchlist_matches(list(by_ticker.keys())):
                for row in by_ticker.get(match["ticker"], []):
                    candidates[(match["user_id"], row["id"])] = (match["email"], row)

        by_member = _group_by(new_rows, "member_name")
        if by_member:
            for match in get_watchlist_actor_matches("congress", list(by_member.keys())):
                for row in by_member.get(match["actor_name"], []):
                    candidates[(match["user_id"], row["id"])] = (match["email"], row)

    elif source == "institutions":
        by_filer = _group_by(new_rows, "filer_name")
        if by_filer:
            for match in get_watchlist_actor_matches("institution", list(by_filer.keys())):
                for row in by_filer.get(match["actor_name"], []):
                    candidates[(match["user_id"], row["id"])] = (match["email"], row)

    if not candidates:
        return

    to_send = filter_unalerted(source, list(candidates.keys()))
    if not to_send:
        return

    by_user: dict[str, dict] = {}
    for (user_id, row_id), (email, row) in candidates.items():
        if (user_id, row_id) not in to_send:
            continue
        entry = by_user.setdefault(user_id, {"email": email, "rows": []})
        entry["rows"].append(row)

    for user_id, entry in by_user.items():
        if not _send_alert_email(source, entry["email"], entry["rows"]):
            logger.info("alert email skipped/failed for user %s — in-app alert is recorded regardless", user_id)

    record_alerts_sent(source, list(to_send))


def _send_alert_email(source: str, email: str, rows: list[dict]) -> bool:
    if source == "congress":
        lines = "".join(
            f"<li><strong>{row.get('member_name') or 'Unknown member'}</strong> "
            f"({str(row.get('chamber') or '').title()}) reported a "
            f"<strong>{(row.get('transaction_type') or 'trade').lower()}</strong> of "
            f"<strong>{row.get('ticker') or 'an unknown ticker'}</strong> — "
            f"{row.get('amount_range') or 'amount unknown'} on {row.get('transaction_date') or 'an unknown date'}</li>"
            for row in rows
        )
        subject = f"Watchlist alert: {len(rows)} new congress trade{'s' if len(rows) != 1 else ''}"
        html = f"<p>New activity on a ticker or member in your watchlist:</p><ul>{lines}</ul>"
    else:
        lines = "".join(
            f"<li><strong>{row.get('filer_name') or 'Unknown filer'}</strong> disclosed a position in "
            f"<strong>{row.get('issuer_name') or row.get('cusip') or 'an unknown holding'}</strong> "
            f"for {row.get('period_of_report') or 'an unknown period'}</li>"
            for row in rows
        )
        subject = f"Watchlist alert: {len(rows)} new institutional holding{'s' if len(rows) != 1 else ''}"
        html = f"<p>New 13F activity from an institution in your watchlist:</p><ul>{lines}</ul>"
    return send_email(email, subject, html)
