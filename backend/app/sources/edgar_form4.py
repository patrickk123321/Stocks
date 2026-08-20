"""Corporate insider trades — SEC Form 4 (ownership change reports).

Source: SEC EDGAR 'latest filings' feed + individual Form 4 XML documents.
Schema verified against live filings, e.g.:
https://www.sec.gov/Archives/edgar/data/1663090/000122520826007237/doc4.xml
"""

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


def _parse_transaction(tx: ET.Element, issuer_name, issuer_ticker, owner_name,
                        officer_title, is_officer, is_director, is_ten_pct,
                        is_derivative: bool, accession_no: str, filed_at: str) -> dict | None:
    security_title = text(local_find(local_find(tx, "securityTitle"), "value"))
    tx_date = text(local_find(local_find(tx, "transactionDate"), "value"))
    coding = local_find(tx, "transactionCoding")
    tx_code = text(local_find(coding, "transactionCode")) if coding is not None else None
    amounts = local_find(tx, "transactionAmounts")
    shares = text(local_find(local_find(amounts, "transactionShares"), "value")) if amounts is not None else None
    price = text(local_find(local_find(amounts, "transactionPricePerShare"), "value")) if amounts is not None else None
    acq_disp = text(local_find(local_find(amounts, "transactionAcquiredDisposedCode"), "value")) if amounts is not None else None
    post = local_find(tx, "postTransactionAmounts")
    shares_after = text(local_find(local_find(post, "sharesOwnedFollowingTransaction"), "value")) if post is not None else None

    if not tx_date or not tx_code:
        return None

    return {
        "accession_no": accession_no,
        "issuer_name": issuer_name,
        "issuer_ticker": issuer_ticker,
        "owner_name": owner_name,
        "officer_title": officer_title,
        "is_director": is_director,
        "is_officer": is_officer,
        "is_ten_percent_owner": is_ten_pct,
        "security_title": security_title,
        "is_derivative": int(is_derivative),
        "transaction_date": tx_date,
        "transaction_code": tx_code,
        "shares": float(shares) if shares else None,
        "price_per_share": float(price) if price else None,
        "acquired_disposed": acq_disp,
        "shares_owned_after": float(shares_after) if shares_after else None,
        "filed_at": filed_at,
    }


def _parse_ownership_document(xml_bytes: bytes, accession_no: str, filed_at: str) -> list[dict]:
    root = ET.fromstring(xml_bytes)

    issuer = local_find(root, "issuer")
    issuer_name = text(local_find(issuer, "issuerName")) if issuer is not None else None
    issuer_ticker = text(local_find(issuer, "issuerTradingSymbol")) if issuer is not None else None

    rows: list[dict] = []
    for owner in local_findall(root, "reportingOwner"):
        owner_id = local_find(owner, "reportingOwnerId")
        owner_name = text(local_find(owner_id, "rptOwnerName")) if owner_id is not None else None
        rel = local_find(owner, "reportingOwnerRelationship")
        is_officer = text(local_find(rel, "isOfficer")) if rel is not None else None
        is_director = text(local_find(rel, "isDirector")) if rel is not None else None
        is_ten_pct = text(local_find(rel, "isTenPercentOwner")) if rel is not None else None
        officer_title = text(local_find(rel, "officerTitle")) if rel is not None else None

        for tx in local_findall(root, "nonDerivativeTransaction"):
            row = _parse_transaction(
                tx, issuer_name, issuer_ticker, owner_name, officer_title,
                is_officer, is_director, is_ten_pct, False, accession_no, filed_at,
            )
            if row:
                rows.append(row)

        for tx in local_findall(root, "derivativeTransaction"):
            row = _parse_transaction(
                tx, issuer_name, issuer_ticker, owner_name, officer_title,
                is_officer, is_director, is_ten_pct, True, accession_no, filed_at,
            )
            if row:
                rows.append(row)

    return rows


def refresh_form4(count: int = 100) -> int:
    """Fetches the latest Form 4 filings and stores their transactions. Returns rows inserted."""
    with sec_client() as client:
        filings = fetch_recent_filings("4", count, client)
        total_inserted = 0
        for filing in filings:
            try:
                doc_urls = [u for u in filing_documents(filing, client) if u.endswith(".xml")]
            except Exception:
                continue
            for doc_url in doc_urls:
                try:
                    resp = client.get(doc_url)
                    resp.raise_for_status()
                    rows = _parse_ownership_document(
                        resp.content, filing["accession_no"], filing["filed_at"]
                    )
                except Exception:
                    continue
                total_inserted += insert_rows("insider_transactions", rows)
        return total_inserted
