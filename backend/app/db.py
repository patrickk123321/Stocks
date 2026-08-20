import sqlite3
from contextlib import contextmanager

from app.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS insider_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    accession_no TEXT NOT NULL,
    issuer_name TEXT,
    issuer_ticker TEXT,
    owner_name TEXT,
    officer_title TEXT,
    is_director INTEGER,
    is_officer INTEGER,
    is_ten_percent_owner INTEGER,
    security_title TEXT,
    is_derivative INTEGER,
    transaction_date TEXT,
    transaction_code TEXT,
    shares REAL,
    price_per_share REAL,
    acquired_disposed TEXT,
    shares_owned_after REAL,
    filed_at TEXT,
    UNIQUE(accession_no, owner_name, security_title, transaction_date, transaction_code, shares)
);

CREATE TABLE IF NOT EXISTS institutional_holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    accession_no TEXT NOT NULL,
    filer_name TEXT,
    filer_cik TEXT,
    period_of_report TEXT,
    issuer_name TEXT,
    cusip TEXT,
    value REAL,
    shares REAL,
    share_type TEXT,
    investment_discretion TEXT,
    filed_at TEXT,
    UNIQUE(accession_no, cusip, shares)
);

CREATE TABLE IF NOT EXISTS congress_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id TEXT NOT NULL,
    chamber TEXT NOT NULL,
    member_name TEXT,
    state_district TEXT,
    filing_date TEXT,
    ticker TEXT,
    asset_description TEXT,
    transaction_type TEXT,
    transaction_date TEXT,
    notification_date TEXT,
    amount_range TEXT,
    pdf_url TEXT,
    UNIQUE(doc_id, ticker, transaction_date, transaction_type, amount_range)
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def insert_rows(table: str, rows: list[dict]) -> int:
    if not rows:
        return 0
    columns = list(rows[0].keys())
    placeholders = ", ".join(f":{c}" for c in columns)
    column_list = ", ".join(columns)
    sql = f"INSERT OR IGNORE INTO {table} ({column_list}) VALUES ({placeholders})"
    with get_conn() as conn:
        cursor = conn.executemany(sql, rows)
        return cursor.rowcount


def query_rows(table: str, ticker_field: str | None, ticker: str | None,
                name_field: str | None, name: str | None,
                start_date: str | None, end_date: str | None, date_field: str) -> list[dict]:
    clauses = []
    params: dict = {}
    if ticker and ticker_field:
        clauses.append(f"{ticker_field} LIKE :ticker")
        params["ticker"] = f"%{ticker}%"
    if name and name_field:
        clauses.append(f"{name_field} LIKE :name")
        params["name"] = f"%{name}%"
    if start_date:
        clauses.append(f"{date_field} >= :start_date")
        params["start_date"] = start_date
    if end_date:
        clauses.append(f"{date_field} <= :end_date")
        params["end_date"] = end_date

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"SELECT * FROM {table} {where} ORDER BY {date_field} DESC LIMIT 500"
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
