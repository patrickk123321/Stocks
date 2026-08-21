from fastapi import APIRouter

from app.db import query_rows
from app.sources.edgar_form4 import refresh_form4

router = APIRouter(prefix="/api/insiders", tags=["insiders"])

SEARCH_FIELDS = ["issuer_ticker", "issuer_name", "owner_name"]


@router.get("")
def list_insider_trades(q: str | None = None):
    return query_rows("insider_transactions", SEARCH_FIELDS, q, "transaction_date")


@router.post("/refresh")
def refresh(count: int = 100):
    inserted = refresh_form4(count=count)
    return {"inserted": inserted}
