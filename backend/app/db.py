import json
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

-- Product 2 (Portfolio Recommendations). One row per confirmed screenshot
-- upload — holdings are stored as a JSON blob (list of {ticker, shares, value})
-- rather than a normalized table, since this is a point-in-time snapshot, not
-- something queried/filtered row-by-row the way the trade-tracker tables are.
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uploaded_at TEXT NOT NULL,
    holdings_json TEXT NOT NULL
);

-- Single-row settings table (id is always 1) — this is a single-user personal
-- app, so a full accounts/profiles system would be over-engineering.
CREATE TABLE IF NOT EXISTS risk_profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    time_horizon TEXT,
    risk_tolerance TEXT,
    primary_goal TEXT,
    target_stock_pct REAL,
    target_bond_pct REAL,
    target_cash_pct REAL,
    updated_at TEXT
);

-- Product 3 (Auto-Trading Bot). Single-row settings table, same pattern as
-- risk_profile above — one bot, one set of guardrails, for this single-user app.
CREATE TABLE IF NOT EXISTS bot_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    enabled INTEGER NOT NULL DEFAULT 0,
    max_trade_dollars REAL NOT NULL DEFAULT 100.0,
    max_trades_per_day INTEGER NOT NULL DEFAULT 3,
    cash_buffer_pct REAL NOT NULL DEFAULT 10.0,
    updated_at TEXT
);

-- One row per order the bot attempts. rationale ties it back to which
-- allocation gap it was closing, so the trade history reads as "why", not
-- just "what". status starts at submit time ("submitted"/"failed") and gets
-- refreshed by polling get_orders (no inbound webhook in this app).
CREATE TABLE IF NOT EXISTS bot_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT NOT NULL,
    ticker TEXT NOT NULL,
    side TEXT NOT NULL DEFAULT 'buy',
    notional REAL NOT NULL,
    asset_class TEXT NOT NULL,
    rationale TEXT NOT NULL,
    status TEXT NOT NULL,
    alpaca_order_id TEXT,
    error_message TEXT,
    placed_at TEXT NOT NULL,
    filled_at TEXT,
    filled_avg_price REAL
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

CREATE INDEX IF NOT EXISTS idx_bot_trades_run_date ON bot_trades(run_date);
CREATE INDEX IF NOT EXISTS idx_bot_trades_placed_at ON bot_trades(placed_at DESC);
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
    ensure_default_bot_config()


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


def save_portfolio_snapshot(holdings: list[dict]) -> int:
    """Stores a user-confirmed set of holdings (see app/routers/portfolio.py —
    holdings are only ever saved after the user reviews/corrects what the vision
    call extracted, never straight from the model's output). Returns the new
    snapshot's id."""
    with get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO portfolio_snapshots (uploaded_at, holdings_json) VALUES (:uploaded_at, :holdings_json)",
            {"uploaded_at": datetime.now(timezone.utc).isoformat(), "holdings_json": json.dumps(holdings)},
        )
        return cursor.lastrowid


def get_latest_portfolio_snapshot() -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, uploaded_at, holdings_json FROM portfolio_snapshots ORDER BY uploaded_at DESC LIMIT 1"
        ).fetchone()
        if not row:
            return None
        return {"id": row["id"], "uploaded_at": row["uploaded_at"], "holdings": json.loads(row["holdings_json"])}


def list_portfolio_snapshots(limit: int = 20) -> list[dict]:
    """Every upload after the first used to be invisible — only the latest
    snapshot was ever readable, even though the data for a full history already
    existed. Lightweight summaries only (id, upload time, holding count, total
    value), most recent first — the caller doesn't need full holdings here."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, uploaded_at, holdings_json FROM portfolio_snapshots ORDER BY uploaded_at DESC LIMIT :limit",
            {"limit": limit},
        ).fetchall()
        summaries = []
        for row in rows:
            holdings = json.loads(row["holdings_json"])
            summaries.append({
                "id": row["id"],
                "uploaded_at": row["uploaded_at"],
                "holding_count": len(holdings),
                "total_value": sum(h.get("value") or 0 for h in holdings),
            })
        return summaries


def get_risk_profile() -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM risk_profile WHERE id = 1").fetchone()
        return dict(row) if row else None


def save_risk_profile(
    time_horizon: str | None,
    risk_tolerance: str,
    primary_goal: str | None,
    target_stock_pct: float,
    target_bond_pct: float,
    target_cash_pct: float,
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO risk_profile (id, time_horizon, risk_tolerance, primary_goal, target_stock_pct, target_bond_pct, target_cash_pct, updated_at)
            VALUES (1, :time_horizon, :risk_tolerance, :primary_goal, :target_stock_pct, :target_bond_pct, :target_cash_pct, :updated_at)
            ON CONFLICT(id) DO UPDATE SET
                time_horizon = excluded.time_horizon,
                risk_tolerance = excluded.risk_tolerance,
                primary_goal = excluded.primary_goal,
                target_stock_pct = excluded.target_stock_pct,
                target_bond_pct = excluded.target_bond_pct,
                target_cash_pct = excluded.target_cash_pct,
                updated_at = excluded.updated_at
            """,
            {
                "time_horizon": time_horizon,
                "risk_tolerance": risk_tolerance,
                "primary_goal": primary_goal,
                "target_stock_pct": target_stock_pct,
                "target_bond_pct": target_bond_pct,
                "target_cash_pct": target_cash_pct,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )


# --- Product 3 (Auto-Trading Bot) ---

def get_bot_config() -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM bot_config WHERE id = 1").fetchone()
        return dict(row) if row else None


def save_bot_config(
    enabled: bool,
    max_trade_dollars: float,
    max_trades_per_day: int,
    cash_buffer_pct: float,
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO bot_config (id, enabled, max_trade_dollars, max_trades_per_day, cash_buffer_pct, updated_at)
            VALUES (1, :enabled, :max_trade_dollars, :max_trades_per_day, :cash_buffer_pct, :updated_at)
            ON CONFLICT(id) DO UPDATE SET
                enabled = excluded.enabled,
                max_trade_dollars = excluded.max_trade_dollars,
                max_trades_per_day = excluded.max_trades_per_day,
                cash_buffer_pct = excluded.cash_buffer_pct,
                updated_at = excluded.updated_at
            """,
            {
                "enabled": int(enabled),
                "max_trade_dollars": max_trade_dollars,
                "max_trades_per_day": max_trades_per_day,
                "cash_buffer_pct": cash_buffer_pct,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )


def ensure_default_bot_config() -> None:
    """Called once from init_db() so the bot always has a config row (off, with
    conservative guardrails) without needing a first-run setup flow the way
    risk_profile requires the questionnaire. INSERT OR IGNORE — never clobbers
    a row the user has already customized."""
    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO bot_config (id, enabled, max_trade_dollars, max_trades_per_day, cash_buffer_pct, updated_at)
            VALUES (1, 0, 100.0, 3, 10.0, :updated_at)
            """,
            {"updated_at": datetime.now(timezone.utc).isoformat()},
        )


def insert_bot_trade(row: dict) -> int:
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO bot_trades (run_date, ticker, side, notional, asset_class, rationale, status, alpaca_order_id, error_message, placed_at)
            VALUES (:run_date, :ticker, :side, :notional, :asset_class, :rationale, :status, :alpaca_order_id, :error_message, :placed_at)
            """,
            {
                "side": "buy",
                "alpaca_order_id": None,
                "error_message": None,
                **row,
            },
        )
        return cursor.lastrowid


def update_bot_trade_status(
    trade_id: int,
    status: str,
    alpaca_order_id: str | None = None,
    error_message: str | None = None,
    filled_at: str | None = None,
    filled_avg_price: float | None = None,
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE bot_trades
            SET status = :status,
                alpaca_order_id = COALESCE(:alpaca_order_id, alpaca_order_id),
                error_message = COALESCE(:error_message, error_message),
                filled_at = COALESCE(:filled_at, filled_at),
                filled_avg_price = COALESCE(:filled_avg_price, filled_avg_price)
            WHERE id = :trade_id
            """,
            {
                "trade_id": trade_id,
                "status": status,
                "alpaca_order_id": alpaca_order_id,
                "error_message": error_message,
                "filled_at": filled_at,
                "filled_avg_price": filled_avg_price,
            },
        )


def list_bot_trades(limit: int = 50, offset: int = 0) -> tuple[list[dict], int]:
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM bot_trades").fetchone()[0]
        rows = conn.execute(
            "SELECT * FROM bot_trades ORDER BY placed_at DESC LIMIT :limit OFFSET :offset",
            {"limit": limit, "offset": offset},
        ).fetchall()
        return [dict(row) for row in rows], total


def get_trades_for_run_date(run_date: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM bot_trades WHERE run_date = :run_date", {"run_date": run_date}
        ).fetchall()
        return [dict(row) for row in rows]


def get_submitted_bot_trades() -> list[dict]:
    """Trades still awaiting a fill-status refresh (see trading_engine.py's
    refresh_pending_trade_statuses) — status hasn't moved past "submitted" yet."""
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM bot_trades WHERE status = 'submitted'").fetchall()
        return [dict(row) for row in rows]
