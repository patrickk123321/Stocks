"""Tests for the Alpaca client wrapper — mocked, never a real network call.
TradingClient itself is patched; the real (lightweight, pure-data) request/enum
classes from alpaca-py are used as-is, same spirit as mocking pdfplumber.open
in test_congress_trades.py rather than mocking every downstream data class.
"""

from unittest.mock import MagicMock, patch

import pytest

from app import alpaca_client


@pytest.fixture(autouse=True)
def _configured_keys(monkeypatch):
    monkeypatch.setattr(alpaca_client, "ALPACA_API_KEY", "test-key")
    monkeypatch.setattr(alpaca_client, "ALPACA_SECRET_KEY", "test-secret")


def test_get_account_raises_when_not_configured(monkeypatch):
    monkeypatch.setattr(alpaca_client, "ALPACA_API_KEY", "")
    monkeypatch.setattr(alpaca_client, "ALPACA_SECRET_KEY", "")
    with pytest.raises(alpaca_client.AlpacaNotConfiguredError):
        alpaca_client.get_account()


def test_get_positions_raises_when_not_configured(monkeypatch):
    monkeypatch.setattr(alpaca_client, "ALPACA_API_KEY", "")
    with pytest.raises(alpaca_client.AlpacaNotConfiguredError):
        alpaca_client.get_positions()


def test_get_account_maps_fields():
    fake_account = MagicMock(cash="1000.50", buying_power="2000.25", equity="3000.75", portfolio_value="3000.75")
    with patch("alpaca.trading.client.TradingClient") as MockClient:
        MockClient.return_value.get_account.return_value = fake_account
        result = alpaca_client.get_account()
    assert result == {"cash": 1000.50, "buying_power": 2000.25, "equity": 3000.75, "portfolio_value": 3000.75}


def test_get_positions_maps_symbol_qty_market_value():
    fake_position = MagicMock(symbol="VTI", qty="5.5", market_value="1234.56")
    with patch("alpaca.trading.client.TradingClient") as MockClient:
        MockClient.return_value.get_all_positions.return_value = [fake_position]
        result = alpaca_client.get_positions()
    assert result == [{"ticker": "VTI", "shares": 5.5, "value": 1234.56}]


def test_is_market_open_reads_clock():
    fake_clock = MagicMock(is_open=True)
    with patch("alpaca.trading.client.TradingClient") as MockClient:
        MockClient.return_value.get_clock.return_value = fake_clock
        assert alpaca_client.is_market_open() is True


def test_submit_market_buy_returns_id_and_status_on_success():
    fake_order = MagicMock(id="order-123")
    fake_order.status.value = "accepted"
    with patch("alpaca.trading.client.TradingClient") as MockClient:
        MockClient.return_value.submit_order.return_value = fake_order
        result = alpaca_client.submit_market_buy("VTI", 100.0)
    assert result == {"id": "order-123", "status": "accepted"}


def test_submit_market_buy_wraps_sdk_error_as_alpaca_order_error():
    with patch("alpaca.trading.client.TradingClient") as MockClient:
        MockClient.return_value.submit_order.side_effect = RuntimeError("insufficient buying power")
        with pytest.raises(alpaca_client.AlpacaOrderError, match="insufficient buying power"):
            alpaca_client.submit_market_buy("VTI", 100.0)


def test_submit_market_sell_notional_path():
    fake_order = MagicMock(id="order-456")
    fake_order.status.value = "accepted"
    with patch("alpaca.trading.client.TradingClient") as MockClient:
        MockClient.return_value.submit_order.return_value = fake_order
        result = alpaca_client.submit_market_sell("AAPL", notional=250.0)
    assert result == {"id": "order-456", "status": "accepted"}


def test_submit_market_sell_qty_path():
    fake_order = MagicMock(id="order-789")
    fake_order.status.value = "accepted"
    with patch("alpaca.trading.client.TradingClient") as MockClient:
        MockClient.return_value.submit_order.return_value = fake_order
        result = alpaca_client.submit_market_sell("AAPL", qty=10)
    assert result == {"id": "order-789", "status": "accepted"}


def test_submit_market_sell_requires_exactly_one_of_notional_or_qty():
    with pytest.raises(ValueError):
        alpaca_client.submit_market_sell("AAPL")
    with pytest.raises(ValueError):
        alpaca_client.submit_market_sell("AAPL", notional=100.0, qty=5)


def test_submit_market_sell_wraps_sdk_error_as_alpaca_order_error():
    with patch("alpaca.trading.client.TradingClient") as MockClient:
        MockClient.return_value.submit_order.side_effect = RuntimeError("position not found")
        with pytest.raises(alpaca_client.AlpacaOrderError, match="position not found"):
            alpaca_client.submit_market_sell("AAPL", qty=10)


def test_get_recent_orders_maps_fields():
    fake_order = MagicMock(id="order-1", symbol="VTI", filled_avg_price="150.25")
    fake_order.status.value = "filled"
    fake_order.filled_at.isoformat.return_value = "2026-08-23T12:00:00+00:00"
    with patch("alpaca.trading.client.TradingClient") as MockClient:
        MockClient.return_value.get_orders.return_value = [fake_order]
        result = alpaca_client.get_recent_orders()
    assert result == [{
        "id": "order-1",
        "symbol": "VTI",
        "status": "filled",
        "filled_at": "2026-08-23T12:00:00+00:00",
        "filled_avg_price": 150.25,
    }]
