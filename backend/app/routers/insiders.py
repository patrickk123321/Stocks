from fastapi import APIRouter

from app.db import query_rows, record_scrape_run
from app.sources.edgar_common import filing_index_url
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
    for row in rows:
        row["source_url"] = (
            filing_index_url(row["filer_cik"], row["accession_no"])
            if row.get("filer_cik") and row.get("accession_no")
            else None
        )
    return {"rows": rows, "total": total}


@router.post("/refresh")
def refresh(count: int = 100):
    inserted, errors = refresh_form4(count=count)
    record_scrape_run("insiders", inserted, errors)
    return {"inserted": inserted, "errors": errors}
