"""Tests for insider/congress trading-cluster signal detection, against a real
(temp) SQLite DB seeded with real-shaped rows — mirrors test_db.py's temp_db
fixture pattern.
"""

import pytest

from app import db, signal_engine

LOOKBACK_START = "2026-01-01"
OLD_DATE = "2025-01-01"  # outside any lookback window used below


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()


def _insider(accession_no, owner_name, ticker, code, acq_disp, date="2026-01-15"):
    return {
        "accession_no": accession_no, "owner_name": owner_name, "issuer_ticker": ticker,
        "transaction_code": code, "acquired_disposed": acq_disp, "transaction_date": date,
        "security_title": "Common Stock", "shares": 100,
    }


def _congress(doc_id, member_name, ticker, transaction_type, date="2026-01-15"):
    return {
        "doc_id": doc_id, "chamber": "house", "member_name": member_name, "ticker": ticker,
        "transaction_type": transaction_type, "transaction_date": date, "amount_range": "$1,001 - $15,000",
    }


def test_get_buy_candidates_counts_distinct_insiders(temp_db):
    db.insert_rows("insider_transactions", [
        _insider("1", "Alice", "AAPL", "P", "A"),
        _insider("2", "Bob", "AAPL", "P", "A"),
    ])
    candidates = signal_engine.get_buy_candidates(LOOKBACK_START)
    c = next(x for x in candidates if x["ticker"] == "AAPL")
    assert c["signal_strength"] == 2
    assert set(c["insiders"]) == {"Alice", "Bob"}


def test_get_buy_candidates_excludes_grants_gifts_and_option_exercises(temp_db):
    # Only P+A is a genuine open-market purchase — A (grant), G (gift), M
    # (option exercise) must not count toward conviction.
    db.insert_rows("insider_transactions", [
        _insider("1", "Alice", "AAPL", "P", "A"),
        _insider("2", "Bob", "AAPL", "A", "A"),   # grant/award
        _insider("3", "Carol", "AAPL", "G", "A"),  # gift
        _insider("4", "Dave", "AAPL", "M", "A"),   # option exercise
    ])
    candidates = signal_engine.get_buy_candidates(LOOKBACK_START)
    c = next((x for x in candidates if x["ticker"] == "AAPL"), None)
    assert c is None  # only 1 genuine buyer (Alice) — below the threshold of 2


def test_get_buy_candidates_excludes_rows_outside_lookback_window(temp_db):
    db.insert_rows("insider_transactions", [
        _insider("1", "Alice", "AAPL", "P", "A", date=OLD_DATE),
        _insider("2", "Bob", "AAPL", "P", "A", date=OLD_DATE),
    ])
    candidates = signal_engine.get_buy_candidates(LOOKBACK_START)
    assert all(c["ticker"] != "AAPL" for c in candidates)


def test_get_buy_candidates_mixes_insider_and_congress_actors(temp_db):
    db.insert_rows("insider_transactions", [_insider("1", "Alice", "GDRX", "P", "A")])
    db.insert_rows("congress_trades", [_congress("d1", "Jane Doe", "GDRX", "Purchase")])
    candidates = signal_engine.get_buy_candidates(LOOKBACK_START)
    c = next(x for x in candidates if x["ticker"] == "GDRX")
    assert c["signal_strength"] == 2  # 1 insider + 1 congress member qualifies
    assert c["insiders"] == ["Alice"]
    assert c["congress"] == ["Jane Doe"]


def test_get_buy_candidates_excludes_congress_exchange_transactions(temp_db):
    db.insert_rows("congress_trades", [
        _congress("d1", "Jane Doe", "GDRX", "Exchange"),
        _congress("d2", "John Roe", "GDRX", "Exchange"),
    ])
    candidates = signal_engine.get_buy_candidates(LOOKBACK_START)
    assert all(c["ticker"] != "GDRX" for c in candidates)


def test_get_sell_signals_for_held_only_returns_held_tickers(temp_db):
    db.insert_rows("insider_transactions", [
        _insider("1", "Alice", "AAPL", "S", "D"),
        _insider("2", "Bob", "AAPL", "S", "D"),
        _insider("3", "Carol", "MSFT", "S", "D"),
        _insider("4", "Dave", "MSFT", "S", "D"),
    ])
    candidates = signal_engine.get_sell_signals_for_held(LOOKBACK_START, held_tickers=["AAPL"])
    tickers = {c["ticker"] for c in candidates}
    assert tickers == {"AAPL"}  # MSFT has an equally strong signal but isn't held


def test_get_sell_signals_excludes_dispositions_that_are_not_open_market_sales(temp_db):
    # acquired_disposed='D' with a non-'S' code (e.g. 'F', tax withholding)
    # must not count as a genuine sell signal.
    db.insert_rows("insider_transactions", [
        _insider("1", "Alice", "AAPL", "S", "D"),
        _insider("2", "Bob", "AAPL", "F", "D"),  # tax withholding, not a genuine sale
    ])
    candidates = signal_engine.get_sell_signals_for_held(LOOKBACK_START, held_tickers=["AAPL"])
    assert all(c["signal_strength"] < 2 for c in candidates if c["ticker"] == "AAPL")


def test_get_signal_strength_map_returns_zero_for_no_activity(temp_db):
    result = signal_engine.get_signal_strength_map(LOOKBACK_START, ["AAPL"])
    assert result["AAPL"] == {"buy_strength": 0, "sell_strength": 0}


def test_get_signal_strength_map_is_unfiltered_by_threshold(temp_db):
    # A single insider buying is below CLUSTER_BUY_THRESHOLD (2), but the
    # strength map must still report it (it's used for ranking, not gating).
    db.insert_rows("insider_transactions", [_insider("1", "Alice", "AAPL", "P", "A")])
    result = signal_engine.get_signal_strength_map(LOOKBACK_START, ["AAPL"])
    assert result["AAPL"]["buy_strength"] == 1


def test_cluster_strength_sums_insiders_and_congress():
    assert signal_engine.cluster_strength({"insiders": {"A", "B"}, "congress": {"C"}}) == 3
