from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.csv_export import export_headers, rows_to_csv
from app.db import get_position_changes, query_all_rows, query_rows, record_scrape_run
from app.rate_limit import cooldown
from app.sources.edgar_13f import refresh_13f
from app.sources.edgar_common import filing_index_url

router = APIRouter(prefix="/api/institutions", tags=["institutions"])

REFRESH_COOLDOWN_SECONDS = 10

# 13F filings report CUSIP, not ticker symbols, so search matches company/filer name and CUSIP.
SEARCH_FIELDS = ["issuer_name", "filer_name", "cusip"]
SORT_FIELDS = {
    "issuer_name", "cusip", "filer_name", "value", "shares", "investment_discretion", "period_of_report",
}
EXPORT_COLUMNS = [
    "issuer_name", "cusip", "filer_name", "value", "shares", "share_type",
    "investment_discretion", "period_of_report", "filed_at", "source_url",
]


def _attach_source_url(rows: list[dict]) -> list[dict]:
    for row in rows:
        row["source_url"] = (
            filing_index_url(row["filer_cik"], row["accession_no"])
            if row.get("filer_cik") and row.get("accession_no")
            else None
        )
    return rows


@router.get("")
def list_institutional_holdings(
    q: str | None = None,
    sort: str | None = None,
    order: str = "desc",
    limit: int = 50,
    offset: int = 0,
    date_from: str | None = None,
    date_to: str | None = None,
    actor: str | None = None,
):
    exact = {"filer_name": actor} if actor else None
    rows, total = query_rows(
        "institutional_holdings", SEARCH_FIELDS, q, "filed_at", SORT_FIELDS,
        sort, order, limit, offset, date_from, date_to, exact,
    )
    return {"rows": _attach_source_url(rows), "total": total}


@router.get("/export")
def export_institutional_holdings(
    q: str | None = None,
    sort: str | None = None,
    order: str = "desc",
    date_from: str | None = None,
    date_to: str | None = None,
    actor: str | None = None,
):
    exact = {"filer_name": actor} if actor else None
    rows, total = query_all_rows(
        "institutional_holdings", SEARCH_FIELDS, q, "filed_at", SORT_FIELDS,
        sort, order, date_from, date_to, exact,
    )
    csv_text = rows_to_csv(_attach_source_url(rows), EXPORT_COLUMNS)
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers=export_headers("institutional_holdings.csv", len(rows), total),
    )


@router.get("/changes")
def list_position_changes(change_type: str | None = None, limit: int = 50, offset: int = 0):
    """NEW / EXITED / CHANGED institutional positions, derived by diffing each
    filer's two most recent 13F periods — see db.get_position_changes."""
    rows, total = get_position_changes(change_type, limit, offset)
    return {"rows": _attach_source_url(rows), "total": total}


@router.post("/refresh", dependencies=[Depends(cooldown("institutions_refresh", REFRESH_COOLDOWN_SECONDS))])
def refresh(count: int = 50):
    inserted, errors = refresh_13f(count=count)
    record_scrape_run("institutions", inserted, errors)
    return {"inserted": inserted, "errors": errors}
