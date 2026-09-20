from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth_clerk import get_current_user
from app.db import (
    add_watchlist_item,
    get_unread_alert_count,
    list_alerts_for_user,
    list_watchlist_items,
    mark_alerts_seen,
    remove_watchlist_item,
)

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


class WatchlistAdd(BaseModel):
    ticker: str


@router.get("")
def get_watchlist(user: dict = Depends(get_current_user)):
    return {"tickers": list_watchlist_items(user["id"])}


@router.post("")
def add_to_watchlist(body: WatchlistAdd, user: dict = Depends(get_current_user)):
    ticker = body.ticker.strip().upper()
    if not ticker:
        raise HTTPException(status_code=422, detail="ticker is required.")
    add_watchlist_item(user["id"], ticker)
    return {"tickers": list_watchlist_items(user["id"])}


@router.delete("/{ticker}")
def remove_from_watchlist(ticker: str, user: dict = Depends(get_current_user)):
    remove_watchlist_item(user["id"], ticker.strip().upper())
    return {"tickers": list_watchlist_items(user["id"])}


@router.get("/alerts")
def get_watchlist_alerts(user: dict = Depends(get_current_user)):
    return {"alerts": list_alerts_for_user(user["id"])}


@router.get("/alerts/unread-count")
def get_unread_count(user: dict = Depends(get_current_user)):
    return {"count": get_unread_alert_count(user["id"])}


@router.post("/alerts/seen")
def mark_watchlist_alerts_seen(user: dict = Depends(get_current_user)):
    mark_alerts_seen(user["id"])
    return {"count": 0}
