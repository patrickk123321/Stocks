"""Congressional trades — House Periodic Transaction Reports (PTRs).

Source: the House Clerk's official bulk financial disclosure data
(https://disclosures-clerk.house.gov), which is public under the STOCK Act.
Verified live: https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}FD.zip
is an XML index of every filing; PTR filings (FilingType == "P") link to a PDF at
https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{year}/{DocID}.pdf

Senate trades are handled separately, in sibling module senate_trades.py, via
a third-party API rather than scraping efdsearch.senate.gov directly (see that
module's docstring for why).

PTR PDFs are semi-structured (not a real data table), so row extraction below
is a best-effort regex over pdfplumber's extracted text. Expect to refine this
as real-world filings turn up formats it doesn't handle.
"""

import io
import logging
import re
import zipfile
from datetime import date, datetime
import xml.etree.ElementTree as ET

import httpx
import pdfplumber

from app.config import HOUSE_CLERK_USER_AGENT
from app.db import insert_rows
from app.sources.senate_trades import FmpNotConfiguredError, refresh_senate_trades

logger = logging.getLogger("stocks.sources.congress_trades")

INDEX_URL = "https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}FD.zip"
PDF_URL = "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{year}/{doc_id}.pdf"

# The transaction-type/date/date/amount block is a reliable compact anchor.
# The "(TICKER)" isn't always right before it — for long asset names the PDF
# wraps the ticker onto the following short line, i.e. AFTER the amount — so
# ticker is located separately below rather than baked into this pattern.
FIELDS_RE = re.compile(
    r"(P|S \(partial\)|S \(full\)|S|E)\s+"
    r"(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+"
    r"(\$[\d,]+(?:\s*-\s*\$[\d,]+|\+)?)"
)
TICKER_RE = re.compile(r"\(([A-Z]{1,6})\)")

# The PTR PDF template's field labels ("Filing Status:", "Sub-Holding Of:") are set in
# a font pdfplumber can't map to Unicode, so those specific words extract as NUL bytes
# — e.g. "Filing Status: New Sub-Holding Of:" comes out as
# "F\x00\x00\x00\x00\x00 S\x00\x00\x00\x00\x00: New S\x00\x00\x00\x00\x00\x00\x00\x00\x00 O\x00:".
# The label itself carries no per-filing information, so drop it; keep whatever real
# value follows (e.g. an account/trust name like "Growth Partners Roth IRA").
BOILERPLATE_LABEL_RE = re.compile(
    r"\[[A-Z]{2,4}\]\s*F\x00+\s*S\x00+:\s*(?:New|Amended?)\s*S\x00+\s*O\x00*:\s*",
    re.IGNORECASE,
)
LEADING_TICKER_RE = re.compile(r"^\([A-Z]{1,6}\)\s*")

# A second manifestation of the same font/glyph-mapping issue as BOILERPLATE_LABEL_RE
# above: sometimes the unmapped label glyphs are dropped entirely instead of coming
# through as NUL bytes, collapsing "Filing Status: New Sub-Holding Of:" straight down
# to literal "F S: New S O:" with nothing standing in for the missing letters. Verified
# against ~310 real stored rows. A leaked share-count number (from the previous field's
# text window) sometimes lands right before it, e.g. "50,000 F S: New S O: ..." — that's
# swept up in the same match since it's never meaningful on its own here. Keep whatever
# real value follows: a sub-holding account/trust name, a "D:" comment, an ownership
# code (SP/JT/DC), all of which are genuine filing content, not boilerplate.
BOILERPLATE_LABEL_PLAIN_RE = re.compile(
    r"(?:[\d,]+\s+)?F\s+S:\s*(?:New|Amended?)\b\s*(?:S\s+O:\s*)?",
    re.IGNORECASE,
)
# A stray leaked ticker can also show up wrapped as "Common Stock (TICKER)" or
# "Stock (TICKER)", not just the bare "(TICKER)" LEADING_TICKER_RE handles.
LEADING_TICKER_WRAPPED_RE = re.compile(r"^(?:Common\s+)?Stock\s*\([A-Z]{1,6}\)\s*", re.IGNORECASE)
# Asset-type bracket tags (e.g. "[ST]", "[OP]") that survive the label strip above
# with nothing left to attach to are leftover noise, not useful on their own.
STRAY_BRACKET_TAG_RE = re.compile(r"\[[A-Z]{2,4}\]\s*")
# A superscript footnote-reference digit sometimes extracts as a literal "?" — e.g. a
# real reference number collapses to "200?". Not recoverable, so drop it as noise.
LEAKED_FOOTNOTE_REF_RE = re.compile(r"^\d+\?\s*")
# Sometimes only the second half of the label ("Sub-Holding Of:") survives as plain
# text with the "Filing Status: New" half dropped entirely, leaving a bare leading
# "S O:" once the footnote-reference noise above it is stripped. Same treatment as
# the "S O:" half of BOILERPLATE_LABEL_PLAIN_RE — drop the label, keep what follows.
LEADING_BARE_SUB_HOLDING_RE = re.compile(r"^S\s+O:\s*", re.IGNORECASE)
# And sometimes the extraction window truncates the boilerplate label itself, chopping
# arbitrary leading characters off "F S: New S O:" — e.g. "S: New S O:", ": New S O:",
# "New S O:", even "ew S O:". Matched against the exact truncation points found live.
BOILERPLATE_LABEL_TRUNCATED_RE = re.compile(
    r"^(?:F\s*)?(?:S:\s*|:\s*)?(?:N?ew|Amended?)\b\s*S\s+O:\s*",
    re.IGNORECASE,
)


def _clean_asset_description(raw: str) -> str:
    cleaned = BOILERPLATE_LABEL_RE.sub("", raw)
    cleaned = cleaned.replace("\x00", "")
    cleaned = BOILERPLATE_LABEL_PLAIN_RE.sub("", cleaned)
    # A stray "(TICKER)" can leak in from the previous row's window; the real
    # ticker already has its own column, so drop a leading one here as noise.
    cleaned = LEADING_TICKER_WRAPPED_RE.sub("", cleaned)
    cleaned = LEADING_TICKER_RE.sub("", cleaned)
    cleaned = STRAY_BRACKET_TAG_RE.sub("", cleaned)
    cleaned = LEAKED_FOOTNOTE_REF_RE.sub("", cleaned)
    cleaned = BOILERPLATE_LABEL_TRUNCATED_RE.sub("", cleaned)
    cleaned = LEADING_BARE_SUB_HOLDING_RE.sub("", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip(" -")


def _is_valid_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%m/%d/%Y")
        return True
    except ValueError:
        return False


def _house_client() -> httpx.Client:
    return httpx.Client(headers={"User-Agent": HOUSE_CLERK_USER_AGENT}, timeout=30.0)


def _fetch_ptr_index(year: int, client: httpx.Client) -> list[dict]:
    resp = client.get(INDEX_URL.format(year=year))
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        xml_name = next(n for n in zf.namelist() if n.endswith(".xml"))
        xml_bytes = zf.read(xml_name)

    root = ET.fromstring(xml_bytes)
    entries = []
    for member in root.findall("Member"):
        filing_type = (member.findtext("FilingType") or "").strip()
        if filing_type != "P":
            continue
        last = (member.findtext("Last") or "").strip()
        first = (member.findtext("First") or "").strip()
        entries.append({
            "doc_id": (member.findtext("DocID") or "").strip(),
            "member_name": f"{first} {last}".strip(),
            "state_district": (member.findtext("StateDst") or "").strip(),
            "filing_date": (member.findtext("FilingDate") or "").strip(),
        })
    return entries


def _parse_ptr_pdf(pdf_bytes: bytes) -> list[dict]:
    rows: list[dict] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        full_text = "\n".join(page.extract_text(layout=True) or "" for page in pdf.pages)
    full_text = re.sub(r"[ \t]*\n[ \t]*", " ", full_text)

    matches = list(FIELDS_RE.finditer(full_text))
    prev_end = 0
    for i, match in enumerate(matches):
        tx_type, tx_date, notif_date, amount = match.groups()
        next_start = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)

        before = full_text[max(prev_end, match.start() - 160):match.start()]
        after = full_text[match.end():min(next_start, match.end() + 40)]

        ticker = None
        ticker_pos_in_before = None
        before_tickers = list(TICKER_RE.finditer(before))
        if before_tickers:
            ticker = before_tickers[-1].group(1)
            ticker_pos_in_before = before_tickers[-1].start()
        else:
            after_ticker = TICKER_RE.search(after)
            if after_ticker:
                ticker = after_ticker.group(1)

        # Asset name precedes the ticker (or the fields, if the ticker wrapped
        # onto the line after); trim at the previous row's trailing "$" amount
        # so its multi-line "F/S/O/D" footnote doesn't bleed into this name.
        name_window = before[:ticker_pos_in_before] if ticker_pos_in_before is not None else before
        last_dollar = name_window.rfind("$")
        if last_dollar != -1:
            name_window = name_window[last_dollar + 1:]
        asset_description = _clean_asset_description(name_window)
        prev_end = match.end()

        # Validation layer: never store a trade whose ticker or dates didn't
        # extract cleanly — a malformed row would otherwise look like a real
        # trade on a bad date rather than being visibly absent.
        if not ticker or not _is_valid_date(tx_date) or not _is_valid_date(notif_date):
            continue

        rows.append({
            "ticker": ticker,
            "asset_description": asset_description,
            "transaction_type": tx_type,
            "transaction_date": tx_date,
            "notification_date": notif_date,
            "amount_range": amount.strip(),
        })
    return rows


def refresh_congress_trades(year: int, limit: int | None = None, since_date: str | None = None) -> tuple[int, int]:
    """Fetches House PTR filings for a given year and stores their trade rows.

    `since_date` (ISO "YYYY-MM-DD") restricts to filings filed on/after that date —
    used for the daily job so it doesn't re-download every PTR PDF for the year
    on each run. Omit it for a full-year backfill.

    Returns (rows inserted, filings that failed to fetch/parse).
    """
    with _house_client() as client:
        entries = _fetch_ptr_index(year, client)

        if since_date:
            cutoff = date.fromisoformat(since_date)

            def _filed_on_or_after_cutoff(entry: dict) -> bool:
                try:
                    return datetime.strptime(entry["filing_date"], "%m/%d/%Y").date() >= cutoff
                except ValueError:
                    return True  # keep unparseable dates rather than silently drop them

            entries = [e for e in entries if _filed_on_or_after_cutoff(e)]

        if limit:
            entries = entries[:limit]

        total_inserted = 0
        error_count = 0
        for entry in entries:
            pdf_url = PDF_URL.format(year=year, doc_id=entry["doc_id"])
            try:
                resp = client.get(pdf_url)
                resp.raise_for_status()
                trade_rows = _parse_ptr_pdf(resp.content)
            except Exception:
                logger.warning("failed to fetch/parse PTR doc_id %s", entry["doc_id"], exc_info=True)
                error_count += 1
                continue

            rows = [
                {
                    "doc_id": entry["doc_id"],
                    "chamber": "house",
                    "member_name": entry["member_name"],
                    "state_district": entry["state_district"],
                    "filing_date": entry["filing_date"],
                    "pdf_url": pdf_url,
                    **trade_row,
                }
                for trade_row in trade_rows
            ]
            total_inserted += insert_rows("congress_trades", rows)
        return total_inserted, error_count


def refresh_all_congress_trades(year: int, limit: int | None = None, since_date: str | None = None) -> tuple[int, int]:
    """Runs both the House PTR refresh (above) and the Senate refresh
    (senate_trades.py), combined into one result — the two chambers share a
    single Congress tab/tracked category in the rest of the app, and one
    chamber failing shouldn't stop the other from inserting its rows."""
    total_inserted = 0
    total_errors = 0

    try:
        inserted, errors = refresh_congress_trades(year=year, limit=limit, since_date=since_date)
        total_inserted += inserted
        total_errors += errors
    except Exception:
        logger.exception("House congress refresh failed")
        total_errors += 1

    try:
        inserted, errors = refresh_senate_trades()
        total_inserted += inserted
        total_errors += errors
    except FmpNotConfiguredError:
        logger.info("Senate refresh skipped — FMP_API_KEY not configured")
    except Exception:
        logger.exception("Senate congress refresh failed")
        total_errors += 1

    return total_inserted, total_errors
