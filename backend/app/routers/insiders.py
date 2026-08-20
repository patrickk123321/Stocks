from fastapi import APIRouter

from app.db import query_rows
from app.sources.edgar_form4 import refresh_form4

router = APIRouter(prefix="/api/insiders", tags=["insiders"])


@router.get("")
def list_insider_trades(
    ticker: str | None = None,
    name: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
):
    return query_rows(
        "insider_transactions", "issuer_ticker", ticker, "owner_name", name,
        start_date, end_date, "transaction_date",
    )


@router.post("/refresh")
def refresh(count: int = 100):
    inserted = refresh_form4(count=count)
    return {"inserted": inserted}
