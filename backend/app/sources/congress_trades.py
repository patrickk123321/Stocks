"""Congressional trades — House Periodic Transaction Reports (PTRs).

Source: the House Clerk's official bulk financial disclosure data
(https://disclosures-clerk.house.gov), which is public under the STOCK Act.
Verified live: https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}FD.zip
is an XML index of every filing; PTR filings (FilingType == "P") link to a PDF at
https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{year}/{DocID}.pdf

Senate trades are NOT included yet: efdsearch.senate.gov blocks non-browser
requests (Akamai bot protection returns 403), so it needs a real session/cookie
flow to access — left as a follow-up rather than working around the block here.

PTR PDFs are semi-structured (not a real data table), so row extraction below
is a best-effort regex over pdfplumber's extracted text. Expect to refine this
as real-world filings turn up formats it doesn't handle.
"""

import io
import re
import zipfile
from datetime import date, datetime
import xml.etree.ElementTree as ET

import httpx
import pdfplumber

from app.config import HOUSE_CLERK_USER_AGENT
from app.db import insert_rows

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
        asset_description = re.sub(r"\s+", " ", name_window).strip(" -")
        prev_end = match.end()

        if not ticker:
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


def refresh_congress_trades(year: int, limit: int | None = None, since_date: str | None = None) -> int:
    """Fetches House PTR filings for a given year and stores their trade rows.

    `since_date` (ISO "YYYY-MM-DD") restricts to filings filed on/after that date —
    used for the daily job so it doesn't re-download every PTR PDF for the year
    on each run. Omit it for a full-year backfill.
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
        for entry in entries:
            pdf_url = PDF_URL.format(year=year, doc_id=entry["doc_id"])
            try:
                resp = client.get(pdf_url)
                resp.raise_for_status()
                trade_rows = _parse_ptr_pdf(resp.content)
            except Exception:
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
        return total_inserted
