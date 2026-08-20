from fastapi import APIRouter

from app.db import query_rows
from app.sources.edgar_13f import refresh_13f

router = APIRouter(prefix="/api/institutions", tags=["institutions"])


@router.get("")
def list_institutional_holdings(
    ticker: str | None = None,
    name: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
):
    # 13F filings report CUSIP, not ticker symbols — there's no ticker column
    # to filter on, so the "ticker" search box for this category searches the
    # issuer/company name instead (see the frontend's "Company" label for it).
    return query_rows(
        "institutional_holdings", "issuer_name", ticker, "filer_name", name,
        start_date, end_date, "filed_at",
    )


@router.post("/refresh")
def refresh(count: int = 50):
    inserted = refresh_13f(count=count)
    return {"inserted": inserted}
