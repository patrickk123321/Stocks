"""Institutional holdings — SEC Form 13F-HR.

Source: SEC EDGAR 'latest filings' feed + the filing's info-table XML document.
Schema verified against a live filing, e.g.:
https://www.sec.gov/Archives/edgar/data/1633037/000163303726000003/06302026rehmann13f.xml
Note: the info-table filename is chosen by the filer (not fixed), so it is
identified as "the .xml document that isn't primary_doc.xml".
"""

import logging
import xml.etree.ElementTree as ET

from app.db import insert_rows
from app.sources.edgar_common import (
    fetch_recent_filings,
    filing_documents,
    local_find,
    local_findall,
    sec_client,
    text,
)

logger = logging.getLogger("stocks.sources.edgar_13f")


def _parse_primary_doc(xml_bytes: bytes) -> tuple[str | None, str | None]:
    root = ET.fromstring(xml_bytes)
    filer_name = text(local_find(root, "name"))
    period = text(local_find(root, "periodOfReport"))
    return filer_name, period


def _parse_info_table(xml_bytes: bytes, accession_no: str, filer_name: str | None,
                       filer_cik: str, period: str | None, filed_at: str) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    rows: list[dict] = []
    for entry in local_findall(root, "infoTable"):
        issuer_name = text(local_find(entry, "nameOfIssuer"))
        cusip = text(local_find(entry, "cusip"))
        value = text(local_find(entry, "value"))
        shrs = local_find(entry, "shrsOrPrnAmt")
        shares = text(local_find(shrs, "sshPrnamt")) if shrs is not None else None
        share_type = text(local_find(shrs, "sshPrnamtType")) if shrs is not None else None
        discretion = text(local_find(entry, "investmentDiscretion"))

        rows.append({
            "accession_no": accession_no,
            "filer_name": filer_name,
            "filer_cik": filer_cik,
            "period_of_report": period,
            "issuer_name": issuer_name,
            "cusip": cusip,
            "value": float(value) if value else None,
            "shares": float(shares) if shares else None,
            "share_type": share_type,
            "investment_discretion": discretion,
            "filed_at": filed_at,
        })
    return rows


def refresh_13f(count: int = 50) -> tuple[int, int]:
    """Fetches the latest 13F-HR filings and stores their holdings.
    Returns (rows inserted, filings that failed to fetch/parse)."""
    with sec_client() as client:
        filings = fetch_recent_filings("13F-HR", count, client)
        total_inserted = 0
        error_count = 0
        for filing in filings:
            try:
                doc_urls = filing_documents(filing, client)
            except Exception:
                logger.warning("failed to list documents for accession %s", filing["accession_no"], exc_info=True)
                error_count += 1
                continue

            primary_url = next((u for u in doc_urls if u.endswith("primary_doc.xml")), None)
            info_table_url = next(
                (u for u in doc_urls if u.endswith(".xml") and not u.endswith("primary_doc.xml")),
                None,
            )
            if not info_table_url:
                continue

            # Non-fatal: the info table below still carries the CUSIP/value data even
            # without a filer name/period, so this is worth logging but not a full failure.
            filer_name, period = None, None
            if primary_url:
                try:
                    resp = client.get(primary_url)
                    resp.raise_for_status()
                    filer_name, period = _parse_primary_doc(resp.content)
                except Exception:
                    logger.warning("failed to fetch/parse primary doc for accession %s", filing["accession_no"], exc_info=True)

            try:
                resp = client.get(info_table_url)
                resp.raise_for_status()
                rows = _parse_info_table(
                    resp.content, filing["accession_no"], filer_name,
                    filing["cik"], period, filing["filed_at"],
                )
            except Exception:
                logger.warning("failed to fetch/parse info table for accession %s", filing["accession_no"], exc_info=True)
                error_count += 1
                continue
            total_inserted += insert_rows("institutional_holdings", rows)
        return total_inserted, error_count
