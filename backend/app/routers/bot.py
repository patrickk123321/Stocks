from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import alpaca_client, db, trading_engine
from app.rate_limit import cooldown

router = APIRouter(prefix="/api/bot", tags=["bot"])

# Longer than the refresh endpoints' cooldown — this one can place real
# (paper) orders and hit an external API, so it needs a stronger guard against
# an accidental double-click than a plain re-scrape does.
RUN_COOLDOWN_SECONDS = 30


class BotConfigInput(BaseModel):
    enabled: bool
    max_trade_dollars: float = Field(gt=0)
    max_trades_per_day: int = Field(gt=0, le=20)
    cash_buffer_pct: float = Field(ge=0, le=100)


@router.get("/config")
def read_config():
    return db.get_bot_config()


@router.post("/config")
def write_config(payload: BotConfigInput):
    db.save_bot_config(
        enabled=payload.enabled,
        max_trade_dollars=payload.max_trade_dollars,
        max_trades_per_day=payload.max_trades_per_day,
        cash_buffer_pct=payload.cash_buffer_pct,
    )
    return db.get_bot_config()


@router.get("/account")
def read_account():
    try:
        account = alpaca_client.get_account()
        positions = alpaca_client.get_positions()
        market_open = alpaca_client.is_market_open()
    except alpaca_client.AlpacaNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {"account": account, "positions": positions, "market_open": market_open}


@router.get("/trades")
def list_trades(limit: int = 50, offset: int = 0):
    rows, total = db.list_bot_trades(limit, offset)
    return {"rows": rows, "total": total}


@router.post("/run", dependencies=[Depends(cooldown("bot_run", RUN_COOLDOWN_SECONDS))])
def run_now():
    """Manual trigger — runs the same orchestrator as the daily scheduled job.
    Respects the same day-level idempotency: if the bot already ran today,
    this returns a "skipped" response rather than silently no-op-ing or
    bypassing the once-per-day limit. Still refreshes pending fill statuses
    first either way, so trades from an earlier run today show current status."""
    trading_engine.refresh_pending_trade_statuses()

    already_ran = db.get_trades_for_run_date(date.today().isoformat())
    if already_ran:
        return {"skipped": "already ran today", "trades": already_ran}

    inserted, errors = trading_engine.run_bot_once()
    rows = db.get_trades_for_run_date(date.today().isoformat())
    return {"inserted": inserted, "errors": errors, "trades": rows}
