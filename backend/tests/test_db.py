"""Tests for db.py's query_rows (search/sort/pagination) and scrape-run tracking,
run against a throwaway SQLite file so they never touch the real stocks.db.
"""

import pytest

from app import db


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()


def test_query_rows_search_matches_any_field(temp_db):
    db.insert_rows("insider_transactions", [
        {"accession_no": "1", "issuer_ticker": "AAPL", "issuer_name": "Apple Inc.", "owner_name": "Alice", "transaction_date": "2026-01-01"},
        {"accession_no": "2", "issuer_ticker": "MSFT", "issuer_name": "Microsoft", "owner_name": "Bob", "transaction_date": "2026-01-02"},
    ])
    rows, total = db.query_rows(
        "insider_transactions", ["issuer_ticker", "issuer_name", "owner_name"], "aapl",
        "transaction_date", set(), limit=10, offset=0,
    )
    assert total == 1
    assert rows[0]["issuer_ticker"] == "AAPL"


def test_query_rows_sort_and_order(temp_db):
    db.insert_rows("insider_transactions", [
        {"accession_no": "1", "owner_name": "Alice", "shares": 100, "transaction_date": "2026-01-01"},
        {"accession_no": "2", "owner_name": "Bob", "shares": 50, "transaction_date": "2026-01-02"},
    ])
    rows, total = db.query_rows(
        "insider_transactions", [], None, "transaction_date", {"shares"},
        sort="shares", order="asc", limit=10, offset=0,
    )
    assert total == 2
    assert [r["owner_name"] for r in rows] == ["Bob", "Alice"]


def test_query_rows_disallowed_sort_field_falls_back_safely(temp_db):
    """A sort field outside allowed_sort_fields must fall back to date_field rather
    than being interpolated into the ORDER BY clause — this is also what keeps
    arbitrary/attacker-controlled `sort` query params from being SQL-injectable."""
    db.insert_rows("insider_transactions", [
        {"accession_no": "1", "issuer_ticker": "AAPL", "transaction_date": "2026-01-01"},
        {"accession_no": "2", "issuer_ticker": "MSFT", "transaction_date": "2026-01-02"},
    ])
    rows, total = db.query_rows(
        "insider_transactions", [], None, "transaction_date", set(),
        sort="issuer_ticker; DROP TABLE insider_transactions;--", limit=10, offset=0,
    )
    assert total == 2
    assert rows[0]["issuer_ticker"] == "MSFT"  # falls back to transaction_date desc


def test_query_rows_pagination(temp_db):
    db.insert_rows("insider_transactions", [
        {"accession_no": str(i), "transaction_date": f"2026-01-{i:02d}"} for i in range(1, 6)
    ])
    page, total = db.query_rows("insider_transactions", [], None, "transaction_date", set(), limit=2, offset=2)
    assert total == 5
    assert len(page) == 2


def test_table_is_empty(temp_db):
    assert db.table_is_empty("insider_transactions") is True
    db.insert_rows("insider_transactions", [{"accession_no": "1"}])
    assert db.table_is_empty("insider_transactions") is False


def test_scrape_run_tracking(temp_db):
    assert db.get_last_scrape_run("insiders") is None
    db.record_scrape_run("insiders", inserted=5, error_count=1)
    last = db.get_last_scrape_run("insiders")
    assert last["inserted"] == 5
    assert last["error_count"] == 1


def test_query_rows_exact_filter_is_precise_not_fuzzy(temp_db):
    """The `exact` filter backs entity drill-down (click a name to see only their
    rows) — it must not fuzzy-match the way `q` does, or clicking "Jane Doe" could
    also pull in an unrelated "Jane Doelittle"."""
    db.insert_rows("insider_transactions", [
        {"accession_no": "1", "owner_name": "Jane Doe", "transaction_date": "2026-01-01"},
        {"accession_no": "2", "owner_name": "Jane Doelittle", "transaction_date": "2026-01-02"},
    ])
    rows, total = db.query_rows(
        "insider_transactions", [], None, "transaction_date", set(),
        limit=10, offset=0, exact={"owner_name": "Jane Doe"},
    )
    assert total == 1
    assert rows[0]["owner_name"] == "Jane Doe"


def test_query_rows_date_range_is_inclusive(temp_db):
    db.insert_rows("insider_transactions", [
        {"accession_no": "1", "transaction_date": "2026-01-01"},
        {"accession_no": "2", "transaction_date": "2026-01-15"},
        {"accession_no": "3", "transaction_date": "2026-01-31"},
    ])
    rows, total = db.query_rows(
        "insider_transactions", [], None, "transaction_date", set(),
        limit=10, offset=0, date_from="2026-01-01", date_to="2026-01-15",
    )
    assert total == 2
    assert {r["accession_no"] for r in rows} == {"1", "2"}


def test_query_all_rows_ignores_pagination_and_respects_cap(temp_db, monkeypatch):
    monkeypatch.setattr(db, "EXPORT_ROW_CAP", 3)
    db.insert_rows("insider_transactions", [
        {"accession_no": str(i), "transaction_date": f"2026-01-{i:02d}"} for i in range(1, 6)
    ])
    rows = db.query_all_rows("insider_transactions", [], None, "transaction_date", set())
    assert len(rows) == 3  # capped, not the full 5 — export is a safety-capped dump, not true pagination
