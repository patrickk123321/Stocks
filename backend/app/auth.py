"""Shared-secret gate for the handful of endpoints that trigger a live external
scrape + DB write (the three /refresh endpoints) or expose internal scrape-run
metadata (/api/status). Deliberately returns the same 401 whether the server
has no ADMIN_API_KEY configured or the caller sent a missing/wrong one —
distinguishing the two would tell an attacker whether the key is even set.
"""

import hmac

from fastapi import Header, HTTPException

from app.config import ADMIN_API_KEY


def require_admin_key(x_admin_key: str | None = Header(default=None)) -> None:
    if not ADMIN_API_KEY or not x_admin_key or not hmac.compare_digest(x_admin_key, ADMIN_API_KEY):
        raise HTTPException(status_code=401, detail="Missing or invalid admin key.")
