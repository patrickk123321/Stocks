from fastapi import APIRouter

from app.db import query_rows
from app.sources.edgar_13f import refresh_13f

router = APIRouter(prefix="/api/institutions", tags=["institutions"])

# 13F filings report CUSIP, not ticker symbols, so search matches company/filer name and CUSIP.
SEARCH_FIELDS = ["issuer_name", "filer_name", "cusip"]


@router.get("")
def list_institutional_holdings(q: str | None = None):
    return query_rows("institutional_holdings", SEARCH_FIELDS, q, "filed_at")


@router.post("/refresh")
def refresh(count: int = 50):
    inserted = refresh_13f(count=count)
    return {"inserted": inserted}
