"""Verifies Clerk session tokens sent as `Authorization: Bearer <token>` by the
frontend, so backend routes can identify which user is calling — the backend
had no user concept before the watchlist feature (see app/auth.py's
require_admin_key, a shared-secret gate for admin-only endpoints, which is a
separate, unrelated mechanism).

Verification is done locally via Clerk's public JWKS (no CLERK_SECRET_KEY or
per-request call to Clerk's API needed) — the same approach Clerk documents
for backends outside their first-party SDKs.

Requires the Clerk Dashboard's session token to include an `email` custom
claim: Dashboard -> Sessions -> Customize session token -> add
`"email": "{{user.primary_email_address}}"`. Clerk's default session claims
don't include email, and this avoids an extra Clerk Backend API call per
request just to look it up.
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
        raise HTTPException(status_code=401, detail="Invalid or expired session token.") from exc

    user_id = claims.get("sub")
    email = claims.get("email")
    if not user_id or not email:
        raise HTTPException(
            status_code=401,
            detail="Session token missing sub/email claim — check the Clerk Dashboard's session token customization.",
        )

    upsert_user(user_id, email)
    return {"id": user_id, "email": email}
