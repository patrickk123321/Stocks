import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from app.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS insider_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    accession_no TEXT NOT NULL,
    filer_cik TEXT,
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

-- One row per scrape attempt, so a failed/partial scheduled run is visible to the
-- user instead of only appearing in stdout logs (see scheduler.py / sources/*.py).
CREATE TABLE IF NOT EXISTS scrape_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    ran_at TEXT NOT NULL,
    inserted INTEGER NOT NULL,
    error_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_insider_ticker ON insider_transactions(issuer_ticker);
CREATE INDEX IF NOT EXISTS idx_insider_owner ON insider_transactions(owner_name);
CREATE INDEX IF NOT EXISTS idx_insider_date ON insider_transactions(transaction_date);

CREATE INDEX IF NOT EXISTS idx_institution_cusip ON institutional_holdings(cusip);
CREATE INDEX IF NOT EXISTS idx_institution_filer_name ON institutional_holdings(filer_name);
CREATE INDEX IF NOT EXISTS idx_institution_filer_cik ON institutional_holdings(filer_cik);
CREATE INDEX IF NOT EXISTS idx_institution_period ON institutional_holdings(period_of_report);

CREATE INDEX IF NOT EXISTS idx_congress_ticker ON congress_trades(ticker);
CREATE INDEX IF NOT EXISTS idx_congress_member ON congress_trades(member_name);
CREATE INDEX IF NOT EXISTS idx_congress_date ON congress_trades(transaction_date);

CREATE INDEX IF NOT EXISTS idx_scrape_runs_category_ran_at ON scrape_runs(category, ran_at DESC);
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


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, coltype: str) -> None:
    """Adds `column` to `table` if it's missing — CREATE TABLE IF NOT EXISTS only
    covers brand-new databases, so existing ones need this to pick up new columns."""
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        _ensure_column(conn, "insider_transactions", "filer_cik", "TEXT")


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


def query_rows(
    table: str,
    search_fields: list[str],
    q: str | None,
    date_field: str,
    allowed_sort_fields: set[str],
    sort: str | None = None,
    order: str = "desc",
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Returns a page of rows (most recent first by default), optionally filtered by a
    single search term matched against any of `search_fields`, and sorted by `sort`
    (falling back to `date_field` if `sort` isn't in `allowed_sort_fields` — this is
    also what keeps the ORDER BY column safe to interpolate). Also returns the total
    row count matching the filter, so the caller can page through results."""
    sort_field = sort if sort in allowed_sort_fields else date_field
    order_sql = "ASC" if order == "asc" else "DESC"

    where = ""
    params: dict = {}
    if q:
        clauses = [f"{field} LIKE :q" for field in search_fields]
        where = f"WHERE {' OR '.join(clauses)}"
        params["q"] = f"%{q}%"

    count_sql = f"SELECT COUNT(*) FROM {table} {where}"
    sql = f"SELECT * FROM {table} {where} ORDER BY {sort_field} {order_sql} LIMIT :limit OFFSET :offset"
    with get_conn() as conn:
        total = conn.execute(count_sql, params).fetchone()[0]
        rows = conn.execute(sql, {**params, "limit": limit, "offset": offset}).fetchall()
        return [dict(row) for row in rows], total


def table_is_empty(table: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone()
        return row is None


def record_scrape_run(category: str, inserted: int, error_count: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO scrape_runs (category, ran_at, inserted, error_count) VALUES (:category, :ran_at, :inserted, :error_count)",
            {
                "category": category,
                "ran_at": datetime.now(timezone.utc).isoformat(),
                "inserted": inserted,
                "error_count": error_count,
            },
        )


def get_last_scrape_run(category: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT ran_at, inserted, error_count FROM scrape_runs WHERE category = :category ORDER BY ran_at DESC LIMIT 1",
            {"category": category},
        ).fetchone()
        return dict(row) if row else None
