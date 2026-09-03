import logging
import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ALLOWED_ORIGINS
from app.db import get_last_scrape_run, init_db
from app.routers import congress, institutions, insiders
from app.scheduler import backfill_if_empty, start_scheduler

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Stocks API")

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
    (previously visible only in stdout logs) is surfaced to the frontend."""
    return {
        category: get_last_scrape_run(category)
        for category in ("insiders", "institutions", "congress")
    }
