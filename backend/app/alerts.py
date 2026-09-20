"""Buy-event-driven watchlist alerts. Right after each congress-trade refresh
finds new rows (see app/scheduler.py's run_congress_refresh), check_and_notify
checks whether any of them are purchases in a watchlisted ticker and records
an alert for every matching user — there's no separate time-based alert
schedule; alerting is driven entirely by new-buy events, at whatever cadence
the refresh runs.

The in-app alert (alerts_sent row, surfaced via /api/watchlist/alerts) is the
source of truth and is recorded regardless of email outcome. Email
(app/notifications/email.py) is a best-effort bonus on top — it currently
no-ops (logs and skips) whenever RESEND_API_KEY/RESEND_FROM_EMAIL aren't
configured, which is fine; a failed or skipped send never blocks the in-app
alert from showing up.
"""

import logging

from app.db import filter_unalerted, get_watchlist_matches, record_alerts_sent
from app.notifications.email import send_email

logger = logging.getLogger("stocks.alerts")

# A set, not a single hardcoded string, so widening alerts to sales/exchanges
# later is a one-line change here rather than a rewrite of check_and_notify.
ALERT_TRANSACTION_TYPES = {"Purchase"}


def check_and_notify(new_rows: list[dict]) -> None:
    purchases = [row for row in new_rows if row.get("transaction_type") in ALERT_TRANSACTION_TYPES and row.get("ticker")]
    if not purchases:
        return

    tickers = list({row["ticker"] for row in purchases})
    matches = get_watchlist_matches(tickers)
    if not matches:
        return

    by_ticker: dict[str, list[dict]] = {}
    for row in purchases:
        by_ticker.setdefault(row["ticker"], []).append(row)

    candidates: list[tuple[str, str, dict]] = []  # (user_id, email, row)
    for match in matches:
        for row in by_ticker.get(match["ticker"], []):
            candidates.append((match["user_id"], match["email"], row))

    to_send = filter_unalerted([(user_id, row["id"]) for user_id, _, row in candidates])
    if not to_send:
        return

    by_user: dict[str, dict] = {}
    for user_id, email, row in candidates:
        if (user_id, row["id"]) not in to_send:
            continue
        entry = by_user.setdefault(user_id, {"email": email, "rows": []})
        entry["rows"].append(row)

    for user_id, entry in by_user.items():
        if not _send_alert_email(entry["email"], entry["rows"]):
            logger.info("alert email skipped/failed for user %s — in-app alert is recorded regardless", user_id)

    record_alerts_sent(list(to_send))


def _send_alert_email(email: str, rows: list[dict]) -> bool:
    lines = "".join(
        f"<li><strong>{row['member_name']}</strong> ({row['chamber'].title()}) bought "
        f"<strong>{row['ticker']}</strong> — {row.get('amount_range') or 'amount unknown'} "
        f"on {row.get('transaction_date') or 'an unknown date'}</li>"
        for row in rows
    )
    subject = f"Watchlist alert: {len(rows)} new congress buy{'s' if len(rows) != 1 else ''}"
    html = f"<p>New politician buys in your watchlist:</p><ul>{lines}</ul>"
    return send_email(email, subject, html)
