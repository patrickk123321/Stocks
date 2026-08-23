"""A minimal, dependency-free per-endpoint cooldown guard. This is NOT
authentication or real rate-limiting infrastructure — this app has neither, and
the audit that flagged this explicitly framed real auth as a "before this is
ever exposed beyond localhost" concern, not urgent for a single-user local tool.
What IS worth guarding against even locally: an accidental client-side bug (or a
double-click) looping a call to an endpoint that either hammers an external
source (SEC/House Clerk/FMP) or burns real Anthropic API spend per call.
"""

import time

from fastapi import HTTPException

_last_call: dict[str, float] = {}


def reset() -> None:
    """Test-only: clear all cooldown state between test cases."""
    _last_call.clear()


def cooldown(key: str, seconds: float):
    """FastAPI dependency factory: rejects a call with 429 if the same `key`
    was called within the last `seconds`."""

    def dependency() -> None:
        now = time.monotonic()
        last = _last_call.get(key)
        if last is not None and (now - last) < seconds:
            remaining = seconds - (now - last)
            raise HTTPException(
                status_code=429,
                detail=f"Please wait {remaining:.0f}s before trying again.",
            )
        _last_call[key] = now

    return dependency
