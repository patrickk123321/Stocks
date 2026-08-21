from fastapi import APIRouter

from app.db import query_rows
from app.sources.congress_trades import refresh_congress_trades

router = APIRouter(prefix="/api/congress", tags=["congress"])

SEARCH_FIELDS = ["ticker", "member_name", "asset_description"]


@router.get("")
def list_congress_trades(q: str | None = None):
    return query_rows("congress_trades", SEARCH_FIELDS, q, "transaction_date")


@router.post("/refresh")
def refresh(year: int, limit: int | None = None, since_date: str | None = None):
    inserted = refresh_congress_trades(year=year, limit=limit, since_date=since_date)
    return {"inserted": inserted}
