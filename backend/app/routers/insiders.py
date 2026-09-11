from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.auth import require_admin_key
from app.csv_export import export_headers, rows_to_csv
from app.db import query_all_rows, query_rows, record_scrape_run
from app.rate_limit import cooldown
from app.sources.edgar_common import filing_index_url
from app.sources.edgar_form4 import refresh_form4

REFRESH_COOLDOWN_SECONDS = 10

router = APIRouter(prefix="/api/insiders", tags=["insiders"])

SEARCH_FIELDS = ["issuer_ticker", "issuer_name", "owner_name"]
SORT_FIELDS = {
    "issuer_ticker", "issuer_name", "owner_name", "officer_title", "transaction_code",
    "acquired_disposed", "shares", "price_per_share", "transaction_date",
}
EXPORT_COLUMNS = [
    "issuer_ticker", "issuer_name", "owner_name", "officer_title", "transaction_code",
    "acquired_disposed", "shares", "price_per_share", "transaction_date", "filed_at", "source_url",
]


def _attach_source_url(rows: list[dict]) -> list[dict]:
    for row in rows:
        row["source_url"] = (
            filing_index_url(row["filer_cik"], row["accession_no"])
            if row.get("filer_cik") and row.get("accession_no")
            else None
        )
    return rows


def _exact_filter(actor: str | None, ticker: str | None) -> dict[str, str] | None:
    exact: dict[str, str] = {}
    if actor:
        exact["owner_name"] = actor
    if ticker:
        exact["issuer_ticker"] = ticker
    return exact or None


@router.get("")
def list_insider_trades(
    q: str | None = None,
    sort: str | None = None,
    order: str = "desc",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0, le=1_000_000),
    date_from: str | None = None,
    date_to: str | None = None,
    actor: str | None = None,
    ticker: str | None = None,
):
    exact = _exact_filter(actor, ticker)
    rows, total = query_rows(
        "insider_transactions", SEARCH_FIELDS, q, "transaction_date", SORT_FIELDS,
        sort, order, limit, offset, date_from, date_to, exact,
    )
    return {"rows": _attach_source_url(rows), "total": total}


@router.get("/export")
def export_insider_trades(
    q: str | None = None,
    sort: str | None = None,
    order: str = "desc",
    date_from: str | None = None,
    date_to: str | None = None,
    actor: str | None = None,
    ticker: str | None = None,
):
    exact = _exact_filter(actor, ticker)
    rows, total = query_all_rows(
        "insider_transactions", SEARCH_FIELDS, q, "transaction_date", SORT_FIELDS,
        sort, order, date_from, date_to, exact,
    )
    csv_text = rows_to_csv(_attach_source_url(rows), EXPORT_COLUMNS)
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers=export_headers("insider_trades.csv", len(rows), total),
    )


@router.post(
    "/refresh",
    dependencies=[Depends(require_admin_key), Depends(cooldown("insiders_refresh", REFRESH_COOLDOWN_SECONDS))],
)
def refresh(count: int = Query(100, ge=1, le=500)):
    inserted, errors = refresh_form4(count=count)
    record_scrape_run("insiders", inserted, errors)
    return {"inserted": inserted, "errors": errors}
