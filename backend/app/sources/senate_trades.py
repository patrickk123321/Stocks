"""Congressional trades — Senate Periodic Transaction Reports (PTRs).

Source: Financial Modeling Prep's `/stable/senate-latest` endpoint, NOT a
direct scrape of efdsearch.senate.gov. That site is a login-gated interactive
search form behind Akamai bot protection with no bulk-download path (unlike
the House Clerk, which publishes an actual XML/ZIP index — see
congress_trades.py) — there's no legitimate "opt in" a personal script can
use to get past that, so FMP (who has already solved that problem) is used
as a data source instead. FMP's response includes a `link` back to the real
efdsearch.senate.gov filing page, so rows still carry a genuine primary-source
URL for verification, not just an FMP citation.

Verified live against a real API key (2026-08-21):
- `/api/v4/senate-trading` and `/api/v4/senate-disclosure` are dead legacy
  endpoints (403, "no longer supported").
- `/stable/senate-latest` is current and works.
- Free tier constraints (confirmed empirically, not documented anywhere we
  could reach): `page` is locked to 0, explicit `limit` values above 25 are
  rejected — but omitting `limit` entirely returns ~100 rows, which is more
  than an explicit 25 would allow. So this always fetches one fixed "latest"
  batch rather than passing an explicit limit.
- No `symbol`/name-based filtering endpoint is available on the free tier
  (`/stable/senate-trades?symbol=` returns 402) — irrelevant to us, since
  ticker/member filtering already happens in our own DB once rows are stored.

Real limitation worth knowing: because `page` is locked to 0, this can only
ever see the most recent ~100 disclosure line items at call time — there is
no way to backfill older Senate history on the free tier. A row that scrolls
off that "latest 100" window before we ever fetch it is simply never seen.
Calling this periodically (e.g. the existing daily job) keeps up with new
disclosures in practice, but this is not a full historical archive the way
the House data is.
"""

import logging
import re

import httpx

from app.config import FMP_API_KEY
from app.db import insert_rows

logger = logging.getLogger("stocks.sources.senate_trades")

SENATE_LATEST_URL = "https://financialmodelingprep.com/stable/senate-latest"
DOC_ID_RE = re.compile(r"/ptr/([a-f0-9-]+)/?")


class FmpNotConfiguredError(Exception):
    """Raised when FMP_API_KEY isn't set — a clean, expected condition (this
    is an optional data source), not a crash."""


def _extract_doc_id(link: str, senate_id: str, transaction_date: str) -> str:
    """The filing UUID in the `link` URL is the closest thing to a per-filing
    id FMP gives us (`senateID` is the *senator's* id, shared across all their
    filings). Falls back to a senator+date composite if a link is ever missing
    or in an unexpected shape, rather than dropping the row."""
    match = DOC_ID_RE.search(link or "")
    if match:
        return match.group(1)
    return f"{senate_id}-{transaction_date}"


def _parse_row(entry: dict) -> dict | None:
    transaction_date = (entry.get("transactionDate") or "").strip()
    if not transaction_date:
        return None

    link = entry.get("link") or ""
    member_name = f"{entry.get('firstName', '')} {entry.get('lastName', '')}".strip()

    return {
        "doc_id": _extract_doc_id(link, entry.get("senateID", ""), transaction_date),
        "chamber": "senate",
        "member_name": member_name,
        "state_district": (entry.get("district") or "").strip(),
        "filing_date": (entry.get("disclosureDate") or "").strip(),
        "ticker": (entry.get("symbol") or "").strip(),
        "asset_description": (entry.get("assetDescription") or "").strip(),
        "transaction_type": (entry.get("type") or "").strip(),
        "transaction_date": transaction_date,
        "notification_date": None,  # FMP doesn't expose a distinct notification date
        "amount_range": (entry.get("amount") or "").strip(),
        "pdf_url": link or None,  # not literally a PDF, but the same "primary source" role as the House column
    }


def refresh_senate_trades() -> tuple[int, int]:
    """Fetches the latest Senate PTR disclosures and stores their trade rows.
    Returns (rows inserted, entries that failed to parse)."""
    if not FMP_API_KEY:
        raise FmpNotConfiguredError("FMP_API_KEY is not set — add it to .env to enable Senate trade tracking.")

    with httpx.Client(timeout=30.0) as client:
        resp = client.get(SENATE_LATEST_URL, params={"apikey": FMP_API_KEY})
        resp.raise_for_status()
        entries = resp.json()

    if not isinstance(entries, list):
        logger.warning("unexpected senate-latest response shape: %r", entries)
        return 0, 1

    rows = []
    error_count = 0
    for entry in entries:
        row = _parse_row(entry)
        if row is None or not row["ticker"]:
            error_count += 1
            continue
        rows.append(row)

    inserted = insert_rows("congress_trades", rows)
    return inserted, error_count
