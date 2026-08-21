from fastapi import APIRouter

from app.db import query_rows
from app.sources.edgar_form4 import refresh_form4

router = APIRouter(prefix="/api/insiders", tags=["insiders"])

SEARCH_FIELDS = ["issuer_ticker", "issuer_name", "owner_name"]
SORT_FIELDS = {
    "issuer_ticker", "issuer_name", "owner_name", "officer_title", "transaction_code",
    "acquired_disposed", "shares", "price_per_share", "transaction_date",
}


@router.get("")
def list_insider_trades(q: str | None = None, sort: str | None = None, order: str = "desc", limit: int = 50, offset: int = 0):
    rows, total = query_rows("insider_transactions", SEARCH_FIELDS, q, "transaction_date", SORT_FIELDS, sort, order, limit, offset)
    return {"rows": rows, "total": total}


@router.post("/refresh")
def refresh(count: int = 100):
    inserted = refresh_form4(count=count)
    return {"inserted": inserted}
