from fastapi import APIRouter

from app.db import query_rows
from app.sources.edgar_13f import refresh_13f
from app.sources.edgar_common import filing_index_url

router = APIRouter(prefix="/api/institutions", tags=["institutions"])

# 13F filings report CUSIP, not ticker symbols, so search matches company/filer name and CUSIP.
SEARCH_FIELDS = ["issuer_name", "filer_name", "cusip"]
SORT_FIELDS = {
    "issuer_name", "cusip", "filer_name", "value", "shares", "investment_discretion", "period_of_report",
}


@router.get("")
def list_institutional_holdings(q: str | None = None, sort: str | None = None, order: str = "desc", limit: int = 50, offset: int = 0):
    rows, total = query_rows("institutional_holdings", SEARCH_FIELDS, q, "filed_at", SORT_FIELDS, sort, order, limit, offset)
    for row in rows:
        row["source_url"] = (
            filing_index_url(row["filer_cik"], row["accession_no"])
            if row.get("filer_cik") and row.get("accession_no")
            else None
        )
    return {"rows": rows, "total": total}


@router.post("/refresh")
def refresh(count: int = 50):
    inserted = refresh_13f(count=count)
    return {"inserted": inserted}
