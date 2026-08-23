import re
from pathlib import Path

import app.data.ticker_reference as ticker_reference_module
from app.data.ticker_reference import TICKER_REFERENCE, get_ticker_info


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


def test_coverage_is_broad_enough_for_a_real_portfolio():
    # Regression guard for the coverage-expansion pass — v1 shipped with ~275
    # tickers, which the audit flagged as too thin for a real portfolio.
    assert len(TICKER_REFERENCE) >= 600


def test_no_ticker_silently_reclassified_by_a_later_add_call():
    # Every _add() call should be the only place a given ticker is assigned —
    # a duplicate with a different (asset_class, sector) means one entry is
    # silently overwriting another to the wrong classification.
    source = Path(ticker_reference_module.__file__).read_text()
    calls = re.findall(r'_add\("(\w+)",\s*"([^"]+)",([^)]+)\)', source, re.S)
    seen: dict[str, tuple[str, str]] = {}
    conflicts = []
    for asset_class, sector, tickers_str in calls:
        for ticker in re.findall(r'"(\w+)"', tickers_str):
            if ticker in seen and seen[ticker] != (asset_class, sector):
                conflicts.append((ticker, seen[ticker], (asset_class, sector)))
            seen[ticker] = (asset_class, sector)
    assert conflicts == []


def test_mid_cap_international_and_mutual_fund_tickers_are_covered():
    assert get_ticker_info("TSM") == {"asset_class": "stock", "sector": "International — Technology"}
    assert get_ticker_info("SOFI") == {"asset_class": "stock", "sector": "Financials"}
    assert get_ticker_info("VTSAX") == {"asset_class": "stock", "sector": "US Broad Market"}
