"""Regression tests for ExtractedHolding's validation — the Claude output schema
mirrors HoldingInput's sanity checks (see test_portfolio_router.py) so a bad
extraction can't slip a negative number straight through to the review table.
"""

import pytest
from pydantic import ValidationError

from app.sources.portfolio_vision import ExtractedHolding


def test_extracted_holding_accepts_valid_values():
    h = ExtractedHolding(ticker="AAPL", shares=10, value=1500.0)
    assert h.shares == 10
    assert h.value == 1500.0


def test_extracted_holding_rejects_negative_shares():
    with pytest.raises(ValidationError):
        ExtractedHolding(ticker="AAPL", shares=-1, value=100)


def test_extracted_holding_rejects_negative_value():
    with pytest.raises(ValidationError):
        ExtractedHolding(ticker="AAPL", shares=1, value=-100)


def test_extracted_holding_allows_cash_ticker_with_no_shares():
    h = ExtractedHolding(ticker="CASH", value=2500.0)
    assert h.ticker == "CASH"
    assert h.shares is None
