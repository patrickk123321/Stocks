from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.csv_export import rows_to_csv
from app.db import query_all_rows, query_rows, record_scrape_run
from app.sources.congress_trades import refresh_congress_trades

router = APIRouter(prefix="/api/congress", tags=["congress"])

SEARCH_FIELDS = ["ticker", "member_name", "asset_description"]
SORT_FIELDS = {
    "member_name", "state_district", "ticker", "asset_description", "transaction_type",
    "amount_range", "transaction_date",
}
EXPORT_COLUMNS = [
    "member_name", "state_district", "ticker", "asset_description", "transaction_type",
    "amount_range", "transaction_date", "notification_date", "filing_date", "source_url",
]


def _attach_source_url(rows: list[dict]) -> list[dict]:
    for row in rows:
        row["source_url"] = row.get("pdf_url")
    return rows


def _exact_filter(actor: str | None, ticker: str | None) -> dict[str, str] | None:
    exact: dict[str, str] = {}
    if actor:
        exact["member_name"] = actor
    if ticker:
        exact["ticker"] = ticker
    return exact or None


@router.get("")
def list_congress_trades(
    q: str | None = None,
    sort: str | None = None,
    order: str = "desc",
    limit: int = 50,
    offset: int = 0,
    date_from: str | None = None,
    date_to: str | None = None,
    actor: str | None = None,
    ticker: str | None = None,
):
    exact = _exact_filter(actor, ticker)
    rows, total = query_rows(
        "congress_trades", SEARCH_FIELDS, q, "transaction_date", SORT_FIELDS,
        sort, order, limit, offset, date_from, date_to, exact,
    )
    return {"rows": _attach_source_url(rows), "total": total}


@router.get("/export")
def export_congress_trades(
    q: str | None = None,
    sort: str | None = None,
    order: str = "desc",
    date_from: str | None = None,
    date_to: str | None = None,
    actor: str | None = None,
    ticker: str | None = None,
):
    exact = _exact_filter(actor, ticker)
    rows = query_all_rows(
        "congress_trades", SEARCH_FIELDS, q, "transaction_date", SORT_FIELDS,
        sort, order, date_from, date_to, exact,
    )
    csv_text = rows_to_csv(_attach_source_url(rows), EXPORT_COLUMNS)
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=congress_trades.csv"},
    )


@router.post("/refresh")
def refresh(year: int, limit: int | None = None, since_date: str | None = None):
    inserted, errors = refresh_congress_trades(year=year, limit=limit, since_date=since_date)
    record_scrape_run("congress", inserted, errors)
    return {"inserted": inserted, "errors": errors}
