from fastapi import APIRouter

from app.db import query_rows
from app.sources.congress_trades import refresh_congress_trades

router = APIRouter(prefix="/api/congress", tags=["congress"])


@router.get("")
def list_congress_trades(
    ticker: str | None = None,
    name: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
):
    return query_rows(
        "congress_trades", "ticker", ticker, "member_name", name,
        start_date, end_date, "transaction_date",
    )


@router.post("/refresh")
def refresh(year: int, limit: int | None = None):
    inserted = refresh_congress_trades(year=year, limit=limit)
    return {"inserted": inserted}
