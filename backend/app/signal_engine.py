"""Insider/congressional trading-cluster signal detection for the auto-trading
bot (Product 3 v2). Reads Product 1's tables directly — this is the mechanism
that lets the bot pick individual stocks, not just rebalance toward Product 2's
target allocation.

A "cluster" is 2+ distinct people (insiders and/or members of Congress, counted
together) buying — or selling — the same ticker within a lookback window. Both
directions use the SAME threshold; trading_engine.py applies a higher
conviction tier (5+) only when sizing a buy, not here.

Filters are deliberately narrower than the raw transaction_code/transaction_type
columns:
- insider_transactions.transaction_code is a raw single-letter SEC Form 4 code
  (P/S/A/G/M/F/C/...). A naive `transaction_code = 'P'` would also count things
  that aren't genuine open-market buying. The correct pair for an open-market
  purchase is transaction_code='P' AND acquired_disposed='A'; for an open-market
  sale, transaction_code='S' AND acquired_disposed='D'.
- congress_trades.transaction_type is already normalized to full words (see
  sources/congress_trades.py's TRANSACTION_TYPE_LABELS): 'Purchase', 'Sale',
  'Sale (Partial)', 'Sale (Full)', 'Exchange'. 'Exchange' is excluded from both
  directions here — its direction is genuinely ambiguous.
"""

from app.db import get_conn

CLUSTER_BUY_THRESHOLD = 2
HIGH_CONVICTION_THRESHOLD = 5
SIGNAL_LOOKBACK_DAYS = 30

_INSIDER_DIRECTION_SQL = {
    "buy": "transaction_code = 'P' AND acquired_disposed = 'A'",
    "sell": "transaction_code = 'S' AND acquired_disposed = 'D'",
}
_CONGRESS_DIRECTION_SQL = {
    "buy": "transaction_type = 'Purchase'",
    "sell": "transaction_type IN ('Sale', 'Sale (Partial)', 'Sale (Full)')",
}


def _distinct_actors_by_ticker(
    direction: str, lookback_start: str, tickers: list[str] | None = None
) -> dict[str, dict[str, set[str]]]:
    """Returns {ticker: {"insiders": {owner_name, ...}, "congress": {member_name, ...}}}
    for every ticker with at least one matching trade in the window (or, if
    `tickers` is given, restricted to just those)."""
    result: dict[str, dict[str, set[str]]] = {}

    with get_conn() as conn:
        insider_sql = (
            f"SELECT issuer_ticker AS ticker, owner_name FROM insider_transactions "
            f"WHERE {_INSIDER_DIRECTION_SQL[direction]} AND transaction_date >= :lookback_start "
            f"AND issuer_ticker IS NOT NULL AND issuer_ticker != ''"
        )
        params: dict = {"lookback_start": lookback_start}
        if tickers:
            placeholders = ", ".join(f":t{i}" for i in range(len(tickers)))
            insider_sql += f" AND issuer_ticker IN ({placeholders})"
            params.update({f"t{i}": t for i, t in enumerate(tickers)})
        for row in conn.execute(insider_sql, params):
            bucket = result.setdefault(row["ticker"], {"insiders": set(), "congress": set()})
            if row["owner_name"]:
                bucket["insiders"].add(row["owner_name"])

        congress_sql = (
            f"SELECT ticker, member_name FROM congress_trades "
            f"WHERE {_CONGRESS_DIRECTION_SQL[direction]} AND transaction_date >= :lookback_start "
            f"AND ticker IS NOT NULL AND ticker != ''"
        )
        params2: dict = {"lookback_start": lookback_start}
        if tickers:
            placeholders = ", ".join(f":t{i}" for i in range(len(tickers)))
            congress_sql += f" AND ticker IN ({placeholders})"
            params2.update({f"t{i}": t for i, t in enumerate(tickers)})
        for row in conn.execute(congress_sql, params2):
            bucket = result.setdefault(row["ticker"], {"insiders": set(), "congress": set()})
            if row["member_name"]:
                bucket["congress"].add(row["member_name"])

    return result


def cluster_strength(actors: dict[str, set[str]]) -> int:
    """Insiders and congress members are disjoint name-namespaces (different
    source tables), so a straight sum of distinct counts correctly implements
    "1 insider + 1 congress member also qualifies" without cross-source dedup."""
    return len(actors["insiders"]) + len(actors["congress"])


def get_buy_candidates(lookback_start: str, min_distinct: int = CLUSTER_BUY_THRESHOLD) -> list[dict]:
    """Scans ALL tickers with recent buying activity, not just held ones — this
    is what makes individual-stock buying possible, not just rebalancing."""
    by_ticker = _distinct_actors_by_ticker("buy", lookback_start)
    candidates = []
    for ticker, actors in by_ticker.items():
        strength = cluster_strength(actors)
        if strength >= min_distinct:
            candidates.append({
                "ticker": ticker,
                "signal_strength": strength,
                "insiders": sorted(actors["insiders"]),
                "congress": sorted(actors["congress"]),
            })
    return candidates


def get_sell_signals_for_held(
    lookback_start: str, held_tickers: list[str], min_distinct: int = CLUSTER_BUY_THRESHOLD
) -> list[dict]:
    """Same shape as get_buy_candidates, sell direction, restricted to tickers
    currently held — a negative signal only matters for a position the bot owns."""
    if not held_tickers:
        return []
    by_ticker = _distinct_actors_by_ticker("sell", lookback_start, tickers=held_tickers)
    candidates = []
    for ticker, actors in by_ticker.items():
        strength = cluster_strength(actors)
        if strength >= min_distinct:
            candidates.append({
                "ticker": ticker,
                "signal_strength": strength,
                "insiders": sorted(actors["insiders"]),
                "congress": sorted(actors["congress"]),
            })
    return candidates


def get_signal_strength_map(lookback_start: str, tickers: list[str]) -> dict[str, dict[str, int]]:
    """Unfiltered by threshold — {ticker: {"buy_strength": n, "sell_strength": n}}
    for every given ticker (0 if no activity). Used only for ranking which
    position to trim first during overweight-gap rebalancing, which needs raw
    signal presence/absence, not the cluster-candidate threshold."""
    if not tickers:
        return {}
    buys = _distinct_actors_by_ticker("buy", lookback_start, tickers=tickers)
    sells = _distinct_actors_by_ticker("sell", lookback_start, tickers=tickers)
    return {
        ticker: {
            "buy_strength": cluster_strength(buys.get(ticker, {"insiders": set(), "congress": set()})),
            "sell_strength": cluster_strength(sells.get(ticker, {"insiders": set(), "congress": set()})),
        }
        for ticker in tickers
    }
