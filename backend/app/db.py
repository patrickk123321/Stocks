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

-- Clerk user id (the JWT `sub` claim) plus the email pulled from the verified
-- session token — see app/auth_clerk.py. Populated lazily: a row only exists
-- once that user has made an authenticated request.
-- last_alerts_seen_at is NULL until the user's first visit to the watchlist
-- page; used to compute the unread-alert badge count in the header nav.
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_alerts_seen_at TEXT
);

CREATE TABLE IF NOT EXISTS watchlist_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(user_id, ticker)
);

-- Favorited people/entities, separate from ticker favorites above.
-- actor_type is 'congress' (matched against congress_trades.member_name) or
-- 'institution' (matched against institutional_holdings.filer_name) --
-- corporate insiders are deliberately not a supported actor_type here.
CREATE TABLE IF NOT EXISTS watchlist_actors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    actor_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(user_id, actor_type, actor_name)
);

-- Durable dedupe for watchlist alerts — an in-memory guard (like
-- app/rate_limit.py's cooldown) would double-email a user across restarts.
-- source + trade_id together identify the row that triggered the alert
-- ('congress' -> congress_trades.id, 'institutions' -> institutional_holdings.id)
-- since alerts can now come from either table (see app/alerts.py).
CREATE TABLE IF NOT EXISTS alerts_sent (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    source TEXT NOT NULL,
    trade_id INTEGER NOT NULL,
    sent_at TEXT NOT NULL,
    UNIQUE(user_id, source, trade_id)
);

CREATE INDEX IF NOT EXISTS idx_watchlist_items_user ON watchlist_items(user_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_items_ticker ON watchlist_items(ticker);
CREATE INDEX IF NOT EXISTS idx_watchlist_actors_user ON watchlist_actors(user_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_actors_lookup ON watchlist_actors(actor_type, actor_name);
CREATE INDEX IF NOT EXISTS idx_alerts_sent_user ON alerts_sent(user_id, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_sent_trade ON alerts_sent(source, trade_id);
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
        _migrate_alerts_sent_to_generic_source(conn)


def _migrate_alerts_sent_to_generic_source(conn: sqlite3.Connection) -> None:
    """alerts_sent originally hardcoded congress_trade_id, back when congress was
    the only alert source. Institutions alerts (actor favorites) need it to
    reference either table, so this renames that column to a generic trade_id
    and adds a source column, backfilling existing rows as 'congress' (the
    only source that ever existed before this migration)."""
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(alerts_sent)")}
    if "congress_trade_id" in existing and "trade_id" not in existing:
        conn.execute("ALTER TABLE alerts_sent RENAME COLUMN congress_trade_id TO trade_id")
    _ensure_column(conn, "alerts_sent", "source", "TEXT NOT NULL DEFAULT 'congress'")


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


def insert_new_rows(table: str, rows: list[dict]) -> list[dict]:
    """Same INSERT OR IGNORE semantics as insert_rows, but returns the full
    row (including the generated id) for every row actually inserted, so
    app/alerts.py knows exactly which rows are new — a plain inserted-count
    can't distinguish "these 3 rows" from "some other 3 rows" for the
    purpose of matching against watchlists. Used for both congress_trades
    and institutional_holdings, the two tables alerts can fire from.
    Executed one row at a time (rather than executemany) because sqlite3
    doesn't support fetching RETURNING results from an executemany call."""
    if not rows:
        return []
    columns = list(rows[0].keys())
    placeholders = ", ".join(f":{c}" for c in columns)
    column_list = ", ".join(columns)
    sql = f"INSERT OR IGNORE INTO {table} ({column_list}) VALUES ({placeholders}) RETURNING *"
    inserted: list[dict] = []
    with get_conn() as conn:
        for row in rows:
            result = conn.execute(sql, row).fetchone()
            if result is not None:
                inserted.append(dict(result))
    return inserted


def _build_where(
    search_fields: list[str],
    q: str | None,
    date_field: str,
    date_from: str | None = None,
    date_to: str | None = None,
    exact: dict[str, str] | None = None,
) -> tuple[str, dict]:
    """Builds a WHERE clause + params shared by query_rows and query_all_rows, so
    the two never drift apart on how filters are interpreted. `exact` keys are
    trusted column names supplied by caller code (routers pass a fixed, known
    column per category — never a raw client-controlled column name)."""
    clauses = []
    params: dict = {}

    if q:
        clauses.append("(" + " OR ".join(f"{field} LIKE :q" for field in search_fields) + ")")
        params["q"] = f"%{q}%"
    if date_from:
        clauses.append(f"{date_field} >= :date_from")
        params["date_from"] = date_from
    if date_to:
        clauses.append(f"{date_field} <= :date_to")
        params["date_to"] = date_to
    for column, value in (exact or {}).items():
        param_name = f"exact_{column}"
        clauses.append(f"{column} = :{param_name}")
        params[param_name] = value

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where, params


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
    date_from: str | None = None,
    date_to: str | None = None,
    exact: dict[str, str] | None = None,
) -> tuple[list[dict], int]:
    """Returns a page of rows (most recent first by default), optionally filtered by a
    single search term matched against any of `search_fields`, an inclusive date-range
    on `date_field`, and/or an exact-match filter (`exact`, e.g. {"owner_name": "Jane Doe"}
    for a precise entity drill-down rather than a fuzzy `q` substring match). Sorted by
    `sort` (falling back to `date_field` if `sort` isn't in `allowed_sort_fields` — this
    is also what keeps the ORDER BY column safe to interpolate). Also returns the total
    row count matching the filter, so the caller can page through results."""
    sort_field = sort if sort in allowed_sort_fields else date_field
    order_sql = "ASC" if order == "asc" else "DESC"
    where, params = _build_where(search_fields, q, date_field, date_from, date_to, exact)

    count_sql = f"SELECT COUNT(*) FROM {table} {where}"
    sql = f"SELECT * FROM {table} {where} ORDER BY {sort_field} {order_sql} LIMIT :limit OFFSET :offset"
    with get_conn() as conn:
        total = conn.execute(count_sql, params).fetchone()[0]
        rows = conn.execute(sql, {**params, "limit": limit, "offset": offset}).fetchall()
        return [dict(row) for row in rows], total


EXPORT_ROW_CAP = 20_000


def query_all_rows(
    table: str,
    search_fields: list[str],
    q: str | None,
    date_field: str,
    allowed_sort_fields: set[str],
    sort: str | None = None,
    order: str = "desc",
    date_from: str | None = None,
    date_to: str | None = None,
    exact: dict[str, str] | None = None,
) -> tuple[list[dict], int]:
    """Same filters as query_rows but returns every matching row (up to
    EXPORT_ROW_CAP, as a sane ceiling rather than true pagination) — used for
    CSV export, where a partial page would silently misrepresent the data.
    Also returns the true total matching the filter (which may exceed
    EXPORT_ROW_CAP) so the caller can tell the user when the export was
    truncated, rather than a capped file silently looking complete."""
    sort_field = sort if sort in allowed_sort_fields else date_field
    order_sql = "ASC" if order == "asc" else "DESC"
    where, params = _build_where(search_fields, q, date_field, date_from, date_to, exact)

    count_sql = f"SELECT COUNT(*) FROM {table} {where}"
    sql = f"SELECT * FROM {table} {where} ORDER BY {sort_field} {order_sql} LIMIT :limit"
    with get_conn() as conn:
        total = conn.execute(count_sql, params).fetchone()[0]
        rows = conn.execute(sql, {**params, "limit": EXPORT_ROW_CAP}).fetchall()
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


def get_position_changes(change_type: str | None = None, limit: int = 50, offset: int = 0) -> tuple[list[dict], int]:
    """Diffs each institutional filer's two most recent reporting periods to surface
    NEW positions, EXITED positions, and %-change on continued holdings — entirely
    derived from institutional_holdings rows already stored (no new scraping). A
    13F only lists an institution's CURRENT holdings, so a filer needs at least two
    distinct period_of_report values on file before it has anything to compare.

    `change_type`, if given, filters to one of "NEW" / "EXITED" / "CHANGED".
    Results are sorted by position size (value) for NEW/EXITED, or by the
    magnitude of the swing for CHANGED — "biggest movers first" either way.
    """
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT filer_cik, filer_name, cusip, issuer_name, period_of_report, shares, value, accession_no "
            "FROM institutional_holdings WHERE filer_cik IS NOT NULL AND cusip IS NOT NULL AND period_of_report IS NOT NULL"
        ).fetchall()

    by_filer: dict[str, dict[str, dict[str, dict]]] = {}
    for row in rows:
        by_filer.setdefault(row["filer_cik"], {}).setdefault(row["period_of_report"], {})[row["cusip"]] = dict(row)

    changes: list[dict] = []
    for periods in by_filer.values():
        sorted_periods = sorted(periods.keys(), reverse=True)
        if len(sorted_periods) < 2:
            continue
        latest, prior = periods[sorted_periods[0]], periods[sorted_periods[1]]

        for cusip, current in latest.items():
            previous = prior.get(cusip)
            if previous is None:
                changes.append({**current, "change_type": "NEW", "prior_shares": None, "pct_change": None})
                continue
            prior_shares = previous.get("shares") or 0
            current_shares = current.get("shares") or 0
            if prior_shares and current_shares != prior_shares:
                pct = round((current_shares - prior_shares) / prior_shares * 100, 1)
                changes.append({**current, "change_type": "CHANGED", "prior_shares": prior_shares, "pct_change": pct})

        for cusip, previous in prior.items():
            if cusip not in latest:
                changes.append({
                    **previous, "change_type": "EXITED",
                    "prior_shares": previous.get("shares"), "pct_change": None,
                })

    if change_type:
        changes = [c for c in changes if c["change_type"] == change_type]

    def sort_key(c: dict) -> float:
        if c["change_type"] == "CHANGED":
            return abs(c["pct_change"] or 0)
        return c.get("value") or 0

    changes.sort(key=sort_key, reverse=True)
    total = len(changes)
    return changes[offset:offset + limit], total


def upsert_user(user_id: str, email: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO users (id, email, created_at, updated_at) VALUES (:id, :email, :now, :now)
            ON CONFLICT(id) DO UPDATE SET email = excluded.email, updated_at = excluded.updated_at
            """,
            {"id": user_id, "email": email, "now": now},
        )


def add_watchlist_item(user_id: str, ticker: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO watchlist_items (user_id, ticker, created_at) VALUES (:user_id, :ticker, :created_at)",
            {"user_id": user_id, "ticker": ticker, "created_at": datetime.now(timezone.utc).isoformat()},
        )


def remove_watchlist_item(user_id: str, ticker: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM watchlist_items WHERE user_id = :user_id AND ticker = :ticker",
            {"user_id": user_id, "ticker": ticker},
        )


def list_watchlist_items(user_id: str) -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT ticker FROM watchlist_items WHERE user_id = :user_id ORDER BY ticker",
            {"user_id": user_id},
        ).fetchall()
        return [row["ticker"] for row in rows]


def get_watchlist_matches(tickers: list[str]) -> list[dict]:
    """Every (user_id, email, ticker) with one of `tickers` on their watchlist —
    used by app/alerts.py to find who to notify about a batch of new buys."""
    if not tickers:
        return []
    placeholders = ", ".join(f":t{i}" for i in range(len(tickers)))
    params = {f"t{i}": ticker for i, ticker in enumerate(tickers)}
    sql = f"""
        SELECT w.user_id AS user_id, u.email AS email, w.ticker AS ticker
        FROM watchlist_items w
        JOIN users u ON u.id = w.user_id
        WHERE w.ticker IN ({placeholders})
    """
    with get_conn() as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def filter_unalerted(source: str, pairs: list[tuple[str, int]]) -> set[tuple[str, int]]:
    """Given candidate (user_id, trade_id) pairs for a given source ('congress'
    or 'institutions'), returns the subset not already recorded in
    alerts_sent — the durable dedupe check that runs BEFORE sending, so a
    crash/retry never double-emails someone."""
    if not pairs:
        return set()
    trade_ids = list({trade_id for _, trade_id in pairs})
    placeholders = ", ".join(f":i{i}" for i in range(len(trade_ids)))
    params = {f"i{i}": trade_id for i, trade_id in enumerate(trade_ids)}
    params["source"] = source
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT user_id, trade_id FROM alerts_sent WHERE source = :source AND trade_id IN ({placeholders})",
            params,
        ).fetchall()
    already_sent = {(row["user_id"], row["trade_id"]) for row in rows}
    return {pair for pair in pairs if pair not in already_sent}


def record_alerts_sent(source: str, pairs: list[tuple[str, int]]) -> None:
    if not pairs:
        return
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO alerts_sent (user_id, source, trade_id, sent_at) VALUES (?, ?, ?, ?)",
            [(user_id, source, trade_id, now) for user_id, trade_id in pairs],
        )


def list_alerts_for_user(user_id: str, limit: int = 50) -> list[dict]:
    """Congress- and institutions-sourced alerts have incompatible row shapes
    (different columns), so they're queried separately and merged in Python
    rather than a SQL UNION — each result is tagged with `source` so the
    frontend knows which shape it's rendering."""
    with get_conn() as conn:
        congress_rows = conn.execute(
            """
            SELECT a.sent_at AS sent_at, 'congress' AS source, c.*
            FROM alerts_sent a
            JOIN congress_trades c ON c.id = a.trade_id
            WHERE a.user_id = :user_id AND a.source = 'congress'
            """,
            {"user_id": user_id},
        ).fetchall()
        institution_rows = conn.execute(
            """
            SELECT a.sent_at AS sent_at, 'institutions' AS source, i.*
            FROM alerts_sent a
            JOIN institutional_holdings i ON i.id = a.trade_id
            WHERE a.user_id = :user_id AND a.source = 'institutions'
            """,
            {"user_id": user_id},
        ).fetchall()
    combined = [dict(row) for row in congress_rows] + [dict(row) for row in institution_rows]
    combined.sort(key=lambda row: row["sent_at"], reverse=True)
    return combined[:limit]


def add_watchlist_actor(user_id: str, actor_type: str, actor_name: str) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO watchlist_actors (user_id, actor_type, actor_name, created_at)
            VALUES (:user_id, :actor_type, :actor_name, :created_at)
            """,
            {
                "user_id": user_id, "actor_type": actor_type, "actor_name": actor_name,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )


def remove_watchlist_actor(user_id: str, actor_type: str, actor_name: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM watchlist_actors WHERE user_id = :user_id AND actor_type = :actor_type AND actor_name = :actor_name",
            {"user_id": user_id, "actor_type": actor_type, "actor_name": actor_name},
        )


def list_watchlist_actors(user_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT actor_type, actor_name FROM watchlist_actors WHERE user_id = :user_id ORDER BY actor_name",
            {"user_id": user_id},
        ).fetchall()
        return [dict(row) for row in rows]


def get_watchlist_actor_matches(actor_type: str, names: list[str]) -> list[dict]:
    """Every (user_id, email, actor_name) favoriting one of `names` as `actor_type`
    — used by app/alerts.py to find who to notify about a batch of new
    congress/institution activity, mirroring get_watchlist_matches for tickers."""
    if not names:
        return []
    placeholders = ", ".join(f":n{i}" for i in range(len(names)))
    params = {f"n{i}": name for i, name in enumerate(names)}
    params["actor_type"] = actor_type
    sql = f"""
        SELECT w.user_id AS user_id, u.email AS email, w.actor_name AS actor_name
        FROM watchlist_actors w
        JOIN users u ON u.id = w.user_id
        WHERE w.actor_type = :actor_type AND w.actor_name IN ({placeholders})
    """
    with get_conn() as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def search_tickers(q: str, limit: int = 10) -> list[str]:
    """Distinct tickers matching `q` (case-insensitive substring) across the two
    tables that carry a real ticker symbol — institutional_holdings only has
    CUSIP, so it's excluded. Backs the Watchlist page's stock search."""
    if not q.strip():
        return []
    pattern = f"%{q.strip()}%"
    sql = """
        SELECT DISTINCT ticker FROM (
            SELECT issuer_ticker AS ticker FROM insider_transactions WHERE issuer_ticker LIKE :pattern COLLATE NOCASE
            UNION
            SELECT ticker FROM congress_trades WHERE ticker LIKE :pattern COLLATE NOCASE
        )
        WHERE ticker IS NOT NULL AND ticker != ''
        ORDER BY ticker
        LIMIT :limit
    """
    with get_conn() as conn:
        rows = conn.execute(sql, {"pattern": pattern, "limit": limit}).fetchall()
        return [row["ticker"] for row in rows]


def search_actors(actor_type: str, q: str, limit: int = 10) -> list[str]:
    """Distinct congress member or institution filer names matching `q`
    (case-insensitive substring). Backs the Watchlist page's people search."""
    if not q.strip():
        return []
    column, table = (
        ("member_name", "congress_trades") if actor_type == "congress" else ("filer_name", "institutional_holdings")
    )
    pattern = f"%{q.strip()}%"
    sql = f"""
        SELECT DISTINCT {column} AS name FROM {table}
        WHERE {column} LIKE :pattern COLLATE NOCASE AND {column} IS NOT NULL AND {column} != ''
        ORDER BY {column}
        LIMIT :limit
    """
    with get_conn() as conn:
        rows = conn.execute(sql, {"pattern": pattern, "limit": limit}).fetchall()
        return [row["name"] for row in rows]


def get_unread_alert_count(user_id: str) -> int:
    """Alerts sent since the user's last visit to the watchlist page — a NULL
    last_alerts_seen_at (never visited) counts every alert as unread."""
    sql = """
        SELECT COUNT(*) AS count
        FROM alerts_sent a
        JOIN users u ON u.id = a.user_id
        WHERE a.user_id = :user_id
          AND (u.last_alerts_seen_at IS NULL OR a.sent_at > u.last_alerts_seen_at)
    """
    with get_conn() as conn:
        row = conn.execute(sql, {"user_id": user_id}).fetchone()
        return row["count"] if row else 0


def mark_alerts_seen(user_id: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET last_alerts_seen_at = :now WHERE id = :user_id",
            {"now": datetime.now(timezone.utc).isoformat(), "user_id": user_id},
        )
