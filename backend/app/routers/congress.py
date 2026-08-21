from fastapi import APIRouter

from app.db import query_rows
from app.sources.congress_trades import refresh_congress_trades

router = APIRouter(prefix="/api/congress", tags=["congress"])

SEARCH_FIELDS = ["ticker", "member_name", "asset_description"]
SORT_FIELDS = {
    "member_name", "state_district", "ticker", "asset_description", "transaction_type",
    "amount_range", "transaction_date",
}


@router.get("")
def list_congress_trades(q: str | None = None, sort: str | None = None, order: str = "desc", limit: int = 50, offset: int = 0):
    rows, total = query_rows("congress_trades", SEARCH_FIELDS, q, "transaction_date", SORT_FIELDS, sort, order, limit, offset)
    for row in rows:
        row["source_url"] = row.get("pdf_url")
    return {"rows": rows, "total": total}


@router.post("/refresh")
def refresh(year: int, limit: int | None = None, since_date: str | None = None):
    inserted = refresh_congress_trades(year=year, limit=limit, since_date=since_date)
    return {"inserted": inserted}
