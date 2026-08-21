import logging
import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.routers import congress, institutions, insiders
from app.scheduler import backfill_if_empty, start_scheduler

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Stocks API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
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
