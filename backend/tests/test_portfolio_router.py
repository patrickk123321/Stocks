"""Regression tests for HoldingInput's validation — added after the audit found
no sanity-checking anywhere on holding values, letting an accidental extra zero
in shares/value silently produce a wildly wrong allocation with no warning.
"""

import pytest
from pydantic import ValidationError

from app.routers.portfolio import HoldingInput


def test_holding_input_accepts_valid_values():
    h = HoldingInput(ticker="aapl", shares=10, value=1500.0)
    assert h.ticker == "AAPL"
    assert h.shares == 10
    assert h.value == 1500.0


def test_holding_input_rejects_negative_shares():
    with pytest.raises(ValidationError):
        HoldingInput(ticker="AAPL", shares=-5, value=100)


def test_holding_input_rejects_negative_value():
    with pytest.raises(ValidationError):
        HoldingInput(ticker="AAPL", shares=5, value=-100)


def test_holding_input_rejects_empty_ticker():
    with pytest.raises(ValidationError):
        HoldingInput(ticker="   ", shares=5, value=100)


def test_holding_input_trims_and_uppercases_ticker():
    h = HoldingInput(ticker="  cash ", shares=None, value=500)
    assert h.ticker == "CASH"


def test_holding_input_allows_null_shares_and_value():
    h = HoldingInput(ticker="CASH")
    assert h.shares is None
    assert h.value is None
