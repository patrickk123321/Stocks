from app.data.ticker_reference import get_ticker_info


def test_known_stock_classified_correctly():
    assert get_ticker_info("AAPL") == {"asset_class": "stock", "sector": "Technology"}


def test_known_bond_etf_classified_correctly():
    assert get_ticker_info("BND") == {"asset_class": "bond", "sector": "Aggregate/Broad Bond"}


def test_lookup_is_case_insensitive_and_trims_whitespace():
    assert get_ticker_info("  aapl ") == {"asset_class": "stock", "sector": "Technology"}


def test_unknown_ticker_is_honestly_unclassified():
    assert get_ticker_info("ZZZZNOTREAL") == {"asset_class": "Unclassified", "sector": "Unclassified"}


def test_empty_ticker_is_unclassified_not_an_error():
    assert get_ticker_info("") == {"asset_class": "Unclassified", "sector": "Unclassified"}
