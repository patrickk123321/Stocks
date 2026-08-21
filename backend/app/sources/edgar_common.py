import re
import xml.etree.ElementTree as ET

import httpx

from app.config import SEC_USER_AGENT

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
ACCESSION_RE = re.compile(r"/data/(\d+)/(\d+)/")


def sec_client() -> httpx.Client:
    return httpx.Client(headers={"User-Agent": SEC_USER_AGENT}, timeout=30.0)


def fetch_recent_filings(form_type: str, count: int, client: httpx.Client) -> list[dict]:
    """Returns deduped filings from the EDGAR 'latest filings' atom feed.

    Each entry: {cik, accession_no, accession_nodashes, index_url, filed_at}
    """
    url = (
        "https://www.sec.gov/cgi-bin/browse-edgar"
        f"?action=getcurrent&type={form_type}&company=&dateb=&owner=include"
        f"&count={count}&output=atom"
    )
    resp = client.get(url)
    resp.raise_for_status()
    root = ET.fromstring(resp.text)

    seen: dict[str, dict] = {}
    for entry in root.findall("atom:entry", ATOM_NS):
        link_el = entry.find("atom:link", ATOM_NS)
        updated_el = entry.find("atom:updated", ATOM_NS)
        if link_el is None:
            continue
        href = link_el.get("href", "")
        match = ACCESSION_RE.search(href)
        if not match:
            continue
        cik, accession_nodashes = match.groups()
        accession_no = (
            f"{accession_nodashes[:10]}-{accession_nodashes[10:12]}-{accession_nodashes[12:]}"
        )
        if accession_no in seen:
            continue
        seen[accession_no] = {
            "cik": cik,
            "accession_no": accession_no,
            "accession_nodashes": accession_nodashes,
            "index_url": (
                f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_nodashes}/index.json"
            ),
            "filed_at": updated_el.text if updated_el is not None else None,
        }
    return list(seen.values())


def filing_index_url(cik: str, accession_no: str) -> str:
    """Builds a link to the filing's official index page on sec.gov, so a user can
    open the primary-source document directly and confirm a stored row against it."""
    accession_nodashes = accession_no.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_nodashes}/{accession_no}-index.htm"


def filing_documents(filing: dict, client: httpx.Client) -> list[str]:
    """Returns absolute URLs to every document filed under this accession."""
    resp = client.get(filing["index_url"])
    resp.raise_for_status()
    data = resp.json()
    base = (
        f"https://www.sec.gov/Archives/edgar/data/{filing['cik']}/"
        f"{filing['accession_nodashes']}"
    )
    return [f"{base}/{item['name']}" for item in data["directory"]["item"]]


def text(el: ET.Element | None) -> str | None:
    if el is None or el.text is None:
        return None
    value = el.text.strip()
    return value or None


def local_findall(parent: ET.Element, tag: str) -> list[ET.Element]:
    """Namespace-agnostic findall: matches on local tag name, ignoring any prefix/URI."""
    return [el for el in parent.iter() if el.tag.rsplit("}", 1)[-1] == tag and el is not parent]


def local_find(parent: ET.Element, tag: str) -> ET.Element | None:
    matches = local_findall(parent, tag)
    return matches[0] if matches else None
