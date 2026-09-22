from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth_clerk import get_current_user
from app.db import (
    add_watchlist_actor,
    add_watchlist_item,
    get_unread_alert_count,
    list_alerts_for_user,
    list_watchlist_actors,
    list_watchlist_items,
    mark_alerts_seen,
    remove_watchlist_actor,
    remove_watchlist_item,
    search_actors,
    search_tickers,
)

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])

ActorType = Literal["congress", "institution"]


class WatchlistAdd(BaseModel):
    ticker: str


class WatchlistActorAdd(BaseModel):
    actor_type: ActorType
    actor_name: str


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


# Search endpoints are unauthenticated — they're read-only lookups against
# already-public trade data, not tied to any user's identity.
@router.get("/search/tickers")
def get_ticker_search(q: str = Query(default="", max_length=20)):
    return {"tickers": search_tickers(q)}


@router.get("/search/actors")
def get_actor_search(actor_type: ActorType = Query(alias="type"), q: str = Query(default="", max_length=100)):
    return {"names": search_actors(actor_type, q)}


@router.get("/actors")
def get_watchlist_actors(user: dict = Depends(get_current_user)):
    return {"actors": list_watchlist_actors(user["id"])}


@router.post("/actors")
def add_to_watchlist_actors(body: WatchlistActorAdd, user: dict = Depends(get_current_user)):
    actor_name = body.actor_name.strip()
    if not actor_name:
        raise HTTPException(status_code=422, detail="actor_name is required.")
    add_watchlist_actor(user["id"], body.actor_type, actor_name)
    return {"actors": list_watchlist_actors(user["id"])}


@router.delete("/actors/{actor_type}/{actor_name}")
def remove_from_watchlist_actors(actor_type: ActorType, actor_name: str, user: dict = Depends(get_current_user)):
    remove_watchlist_actor(user["id"], actor_type, actor_name.strip())
    return {"actors": list_watchlist_actors(user["id"])}
