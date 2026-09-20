"""Thin wrapper around Resend's REST API for watchlist-alert emails — uses
the existing httpx dependency directly rather than adding Resend's SDK.
"""

import logging

import httpx

from app.config import RESEND_API_KEY, RESEND_FROM_EMAIL

logger = logging.getLogger("stocks.notifications.email")

RESEND_URL = "https://api.resend.com/emails"


def send_email(to: str, subject: str, html: str) -> bool:
    if not RESEND_API_KEY or not RESEND_FROM_EMAIL:
        logger.warning("RESEND_API_KEY/RESEND_FROM_EMAIL not configured — skipping email to %s", to)
        return False
    try:
        resp = httpx.post(
            RESEND_URL,
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            json={"from": RESEND_FROM_EMAIL, "to": [to], "subject": subject, "html": html},
            timeout=15.0,
        )
        resp.raise_for_status()
        return True
    except Exception:
        logger.exception("failed to send watchlist alert email to %s", to)
        return False
