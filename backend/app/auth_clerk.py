"""Verifies Clerk session tokens sent as `Authorization: Bearer <token>` by the
frontend, so backend routes can identify which user is calling — the backend
had no user concept before the watchlist feature (see app/auth.py's
require_admin_key, a shared-secret gate for admin-only endpoints, which is a
separate, unrelated mechanism).

Verification is done locally via Clerk's public JWKS (no CLERK_SECRET_KEY or
per-request call to Clerk's API needed) — the same approach Clerk documents
for backends outside their first-party SDKs.

The `email` claim is optional — Clerk's default session claims don't include
it, and pulling it in would require a Clerk Dashboard session-token
customization plus an extra Backend API call. It's not worth requiring: the
only consumer is app/alerts.py's Resend email path, which is currently
inactive (RESEND_API_KEY unset), so a missing email just means no bonus
email gets sent — it never blocks auth.
"""

import base64

import jwt
from fastapi import Header, HTTPException
from jwt import PyJWKClient

from app.config import CLERK_PUBLISHABLE_KEY
from app.db import upsert_user


def _clerk_frontend_api_host(publishable_key: str) -> str:
    """Same derivation as frontend/next.config.ts's clerkFrontendApiHost:
    Clerk's publishable key is `pk_<env>_<base64>`, where the base64 payload
    decodes to the Frontend API host, with a trailing "$" to strip."""
    encoded = publishable_key.split("_", 2)[-1]
    padded = encoded + "=" * (-len(encoded) % 4)
    return base64.b64decode(padded).decode("utf-8").rstrip("$")


_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        if not CLERK_PUBLISHABLE_KEY:
            raise RuntimeError("CLERK_PUBLISHABLE_KEY must be set to verify Clerk session tokens.")
        host = _clerk_frontend_api_host(CLERK_PUBLISHABLE_KEY)
        # PyJWKClient caches keys in-memory and only re-fetches on a kid miss,
        # so this isn't a per-request network call.
        _jwks_client = PyJWKClient(f"https://{host}/.well-known/jwks.json")
    return _jwks_client


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    """FastAPI dependency: verifies the bearer token and returns
    {"id": <clerk user id>, "email": <email>}, upserting the user into the
    local `users` table on every call so alerts.py always has an up-to-date
    email to send to."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    token = authorization.removeprefix("Bearer ").strip()

    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(token, signing_key.key, algorithms=["RS256"], options={"verify_aud": False})
    except Exception as exc:
        # Temporarily includes the real exception (class + message) instead of a
        # generic "Invalid or expired session token." — a production 401 here
        # gave no signal on *why* verification failed (expired vs. bad signature
        # vs. JWKS lookup failure), which blocked diagnosing the watchlist outage.
        raise HTTPException(status_code=401, detail=f"Session token verification failed: {type(exc).__name__}: {exc}") from exc

    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Session token missing sub claim.")
    email = claims.get("email") or ""

    upsert_user(user_id, email)
    return {"id": user_id, "email": email}
