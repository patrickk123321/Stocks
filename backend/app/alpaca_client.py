"""Thin wrapper around Alpaca's paper-trading API (the alpaca-py SDK). Every
function here is close to a 1:1 pass-through to the SDK, kept deliberately dumb
so app/trading_engine.py's decision logic stays pure/mockable and this module
stays trivially mockable in tests (patch app.alpaca_client.* the same way
test_congress_trades.py patches pdfplumber.open).

paper=True is hardcoded in _client() with no parameter to override it — this is
a deliberate, load-bearing safety choice: even if a live-trading key pair were
ever pasted into ALPACA_API_KEY/ALPACA_SECRET_KEY by mistake, this codebase can
never route an order to a real brokerage account. Going live would have to be a
conscious, separate code change here, not a .env edit.

The `alpaca` package is imported inside each function rather than at module
top-level: app/main.py imports every router unconditionally at startup, and an
optional dependency failing to import shouldn't crash the whole backend (same
reasoning as config.py's comment about FMP_API_KEY/ANTHROPIC_API_KEY being
validated at call time, not at import time).
"""

import logging

from app.config import ALPACA_API_KEY, ALPACA_SECRET_KEY

logger = logging.getLogger("stocks.alpaca")


class AlpacaNotConfiguredError(Exception):
    """Raised when ALPACA_API_KEY/ALPACA_SECRET_KEY aren't set — a router-level
    503, not a crash."""


class AlpacaOrderError(Exception):
    """Raised when Alpaca is reached but rejects an order (e.g. insufficient
    buying power, symbol not tradable/fractionable). Wraps the SDK's own
    exception message so callers never need to import Alpaca's exception types."""


def _client():
    if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
        raise AlpacaNotConfiguredError(
            "ALPACA_API_KEY / ALPACA_SECRET_KEY are not set — add them to .env to enable the auto-trading bot."
        )
    from alpaca.trading.client import TradingClient

    return TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)  # paper hardcoded — not a parameter, ever


def get_account() -> dict:
    account = _client().get_account()
    return {
        "cash": float(account.cash),
        "buying_power": float(account.buying_power),
        "equity": float(account.equity),
        "portfolio_value": float(account.portfolio_value),
    }


def get_positions() -> list[dict]:
    """Shaped as {"ticker", "shares", "value"} — exactly what
    portfolio_engine.compute_allocation already consumes, so Product 3 reuses
    Product 2's allocation math directly instead of reimplementing it."""
    positions = _client().get_all_positions()
    return [
        {"ticker": p.symbol, "shares": float(p.qty), "value": float(p.market_value)}
        for p in positions
    ]


def is_market_open() -> bool:
    return bool(_client().get_clock().is_open)


def get_recent_orders(limit: int = 20) -> list[dict]:
    from alpaca.trading.enums import QueryOrderStatus
    from alpaca.trading.requests import GetOrdersRequest

    orders = _client().get_orders(filter=GetOrdersRequest(status=QueryOrderStatus.ALL, limit=limit))
    return [
        {
            "id": str(o.id),
            "symbol": o.symbol,
            "status": o.status.value if hasattr(o.status, "value") else str(o.status),
            "filled_at": o.filled_at.isoformat() if o.filled_at else None,
            "filled_avg_price": float(o.filled_avg_price) if o.filled_avg_price is not None else None,
        }
        for o in orders
    ]


def submit_market_buy(ticker: str, notional: float) -> dict:
    """Submits a dollar-denominated (notional) market buy order — a better fit
    than a share-quantity order for closing a gap sized in dollars. Returns
    {"id", "status"}. Raises AlpacaOrderError if Alpaca reaches back with a
    rejection (e.g. insufficient buying power, symbol not fractionable)."""
    from alpaca.trading.enums import OrderSide, TimeInForce
    from alpaca.trading.requests import MarketOrderRequest

    order_data = MarketOrderRequest(
        symbol=ticker,
        notional=round(notional, 2),
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY,
    )
    try:
        order = _client().submit_order(order_data=order_data)
    except Exception as e:  # Alpaca's own SDK exception types aren't imported by callers
        raise AlpacaOrderError(str(e)) from e
    return {"id": str(order.id), "status": order.status.value if hasattr(order.status, "value") else str(order.status)}
