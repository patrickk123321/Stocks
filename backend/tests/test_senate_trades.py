from app.sources.senate_trades import _extract_doc_id, _parse_row


def test_extract_doc_id_from_real_link_shape():
    link = "https://efdsearch.senate.gov/search/view/ptr/f727289a-4d72-4c90-a3ea-63d5bcd23398/"
    assert _extract_doc_id(link, "B001236", "2025-04-08") == "f727289a-4d72-4c90-a3ea-63d5bcd23398"


def test_extract_doc_id_falls_back_when_link_missing():
    assert _extract_doc_id("", "B001236", "2025-04-08") == "B001236-2025-04-08"


def test_extract_doc_id_falls_back_on_unexpected_link_shape():
    assert _extract_doc_id("https://example.com/not-a-ptr-link", "B001236", "2025-04-08") == "B001236-2025-04-08"


def _sample_entry(**overrides):
    entry = {
        "symbol": "AVGO",
        "senateID": "B001236",
        "disclosureDate": "2026-08-20",
        "transactionDate": "2025-04-08",
        "firstName": "John",
        "lastName": "Boozman",
        "office": "John Boozman",
        "district": "AR",
        "owner": "Joint",
        "assetDescription": "Broadcom Inc",
        "assetType": "Stock",
        "type": "Purchase",
        "amount": "$1,001 - $15,000",
        "comment": "",
        "link": "https://efdsearch.senate.gov/search/view/ptr/f727289a-4d72-4c90-a3ea-63d5bcd23398/",
    }
    entry.update(overrides)
    return entry


def test_parse_row_maps_fields_correctly():
    row = _parse_row(_sample_entry())
    assert row["chamber"] == "senate"
    assert row["member_name"] == "John Boozman"
    assert row["state_district"] == "AR"
    assert row["ticker"] == "AVGO"
    assert row["asset_description"] == "Broadcom Inc"
    assert row["transaction_type"] == "Purchase"
    assert row["transaction_date"] == "2025-04-08"
    assert row["amount_range"] == "$1,001 - $15,000"
    assert row["doc_id"] == "f727289a-4d72-4c90-a3ea-63d5bcd23398"
    assert row["pdf_url"] == _sample_entry()["link"]
    assert row["notification_date"] is None  # FMP doesn't expose this — must not be fabricated


def test_parse_row_returns_none_when_transaction_date_missing():
    assert _parse_row(_sample_entry(transactionDate="")) is None
