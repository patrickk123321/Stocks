import logging
import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ALLOWED_ORIGINS
from app.db import get_last_scrape_run, init_db
from app.ip_rate_limit import RateLimitMiddleware
from app.routers import congress, institutions, insiders
from app.scheduler import backfill_if_empty, start_scheduler
from app.security_headers import SecurityHeadersMiddleware

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="ToTheMoon API")

# Starlette applies the *last-added* middleware as the *outermost* layer (sees the
# request first, response last) — added in reverse order here so CORS still attaches
# its headers even to a 429/error from an inner layer; otherwise the browser would
# treat that response as CORS-blocked and the frontend couldn't read it.
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    # Browsers only expose the CORS-safelisted response headers to JS by default —
    # these carry the CSV export truncation signal, so they need to opt in explicitly.
    expose_headers=["X-Total-Matched", "X-Export-Row-Count", "X-Export-Truncated"],
)

app.include_router(insiders.router)
app.include_router(institutions.router)
app.include_router(congress.router)


@app.on_event("startup")
def on_startup():
    init_db()
    # Runs in the background so a fresh/empty database doesn't block the server
    # from accepting requests for however long the first full backfill takes.
    threading.Thread(target=backfill_if_empty, daemon=True).start()
    app.state.scheduler = start_scheduler()


@app.on_event("shutdown")
def on_shutdown():
    app.state.scheduler.shutdown(wait=False)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/status")
def status():
    """Last scrape attempt per category, so a silently-failed scheduled run
    (previously visible only in stdout logs) is surfaced to the frontend. Purely
    informational (no trade/financial data) — deliberately left open, unlike the
    /refresh endpoints (see app/auth.py)."""
    return {
        category: get_last_scrape_run(category)
        for category in ("insiders", "institutions", "congress")
    }
