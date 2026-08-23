"""Regression tests for the House PTR PDF text cleanup — this is the most fragile,
best-effort part of the codebase (see congress_trades.py's module docstring) and
the one place a real data-corruption bug was already found and fixed this project:
the PDF template's field labels ("Filing Status:", "Sub-Holding Of:") extract as
literal NUL bytes because pdfplumber can't map that font's glyphs to Unicode.
"""

from contextlib import contextmanager
from unittest.mock import patch

from app.sources.congress_trades import (
    TRANSACTION_TYPE_LABELS,
    _clean_asset_description,
    _is_valid_date,
    _parse_ptr_pdf,
)


class _FakePage:
    def __init__(self, text: str):
        self._text = text

    def extract_text(self, layout: bool = False) -> str:
        return self._text


@contextmanager
def _fake_pdf(text: str):
    class _FakePdf:
        pages = [_FakePage(text)]

    yield _FakePdf()


def test_clean_asset_description_strips_nul_byte_boilerplate_and_leading_ticker():
    # Exact real sample pulled from the live database before the fix — this is the
    # precise bug report this test guards against regressing.
    raw = (
        "(ADI) [ST] F\x00\x00\x00\x00\x00 S\x00\x00\x00\x00\x00: New "
        "S\x00\x00\x00\x00\x00\x00\x00\x00\x00 O\x00: Growth Partners Roth IRA Apple Inc. - Common Stock"
    )
    assert _clean_asset_description(raw) == "Growth Partners Roth IRA Apple Inc. - Common Stock"


def test_clean_asset_description_strips_nul_byte_boilerplate_no_ticker():
    raw = "[ST] F\x00\x00\x00\x00\x00 S\x00\x00\x00\x00\x00: New S\x00\x00\x00\x00\x00\x00\x00\x00\x00 O\x00: Common Stock"
    assert _clean_asset_description(raw) == "Common Stock"


def test_clean_asset_description_never_leaves_nul_bytes():
    raw = "[ST] F\x00\x00\x00\x00\x00 S\x00\x00\x00\x00\x00: New S\x00\x00\x00\x00\x00\x00\x00\x00\x00 O\x00: Some Trust"
    assert "\x00" not in _clean_asset_description(raw)


def test_clean_asset_description_passthrough_when_clean():
    assert _clean_asset_description("  Common Stock  ") == "Common Stock"


def test_clean_asset_description_strips_leading_stray_ticker_alone():
    assert _clean_asset_description("(MSFT) Microsoft Corp. - Common Stock") == "Microsoft Corp. - Common Stock"


# A second, distinct manifestation of the same root cause as the NUL-byte tests above:
# here pdfplumber drops the unmappable label glyphs entirely instead of emitting NUL
# bytes, collapsing "Filing Status: New Sub-Holding Of:" straight down to literal
# "F S: New S O:". Found live in ~310 real stored rows (see congress_trades.py).
def test_clean_asset_description_strips_plain_text_boilerplate_with_leaked_number():
    raw = (
        "50,000 F S: New S O: R.W. Allen & Associates, Inc. > RWA&A - Securities "
        "SP Netflix, Inc. - Common Stock"
    )
    assert _clean_asset_description(raw) == (
        "R.W. Allen & Associates, Inc. > RWA&A - Securities SP Netflix, Inc. - Common Stock"
    )


def test_clean_asset_description_strips_plain_text_boilerplate_wrapped_ticker_and_bracket_tag():
    raw = "Common Stock (MLM) [ST] F S: New DC PTC Inc. - Common Stock"
    assert _clean_asset_description(raw) == "DC PTC Inc. - Common Stock"


def test_clean_asset_description_strips_plain_text_boilerplate_no_sub_holding():
    raw = "[OP] F S: New D: Put Option SP Nokia Corporation Sponsored"
    assert _clean_asset_description(raw) == "D: Put Option SP Nokia Corporation Sponsored"


def test_clean_asset_description_strips_plain_text_boilerplate_amended():
    raw = (
        "50,000 F S: Amended S O: United Bank Brokerage Account 2000134517 "
        "SP Quest Diagnostics Incorporated"
    )
    assert _clean_asset_description(raw) == (
        "United Bank Brokerage Account 2000134517 SP Quest Diagnostics Incorporated"
    )


def test_clean_asset_description_strips_truncated_leaked_number_before_boilerplate():
    # A text-window boundary can cut a leaked share count down to a partial digit
    # run ("0,000" / "00" instead of "50,000" / "100") — still noise, still stripped.
    assert _clean_asset_description("0,000 F S: New S O: Registered Index Linked Annuity") == (
        "Registered Index Linked Annuity"
    )
    assert _clean_asset_description("00 F S: New S O: Registered Index Linked Annuity") == (
        "Registered Index Linked Annuity"
    )


def test_clean_asset_description_strips_leaked_footnote_reference():
    assert _clean_asset_description("200? F S: New DC Somnigroup International Inc.") == (
        "DC Somnigroup International Inc."
    )


def test_clean_asset_description_preserves_legitimate_comment_field():
    raw = (
        "5,000,000 F S: New D: Contribution of 7,704 shares held personally to "
        "Donor-Advised Fund. SP Amazon.com, Inc. - Common Stock"
    )
    assert _clean_asset_description(raw) == (
        "D: Contribution of 7,704 shares held personally to Donor-Advised Fund. "
        "SP Amazon.com, Inc. - Common Stock"
    )


# A third variant found live: sometimes the "Filing Status: New" half is dropped
# entirely and only the "Sub-Holding Of:" half survives as bare plain text "S O:".
def test_clean_asset_description_strips_bare_sub_holding_label():
    raw = "S O: 150 Main Street Trust > Bank of America D: Ticker 8306 JP Netflix, Inc. - Common Stock"
    assert _clean_asset_description(raw) == (
        "150 Main Street Trust > Bank of America D: Ticker 8306 JP Netflix, Inc. - Common Stock"
    )


def test_clean_asset_description_strips_leaked_footnote_ref_and_bare_sub_holding_together():
    raw = "200? S O: 150 Main Street Trust > Bank of America D: Ticker SAN SM Biogen Inc. - Common Stock"
    assert _clean_asset_description(raw) == (
        "150 Main Street Trust > Bank of America D: Ticker SAN SM Biogen Inc. - Common Stock"
    )


def test_clean_asset_description_strips_leaked_footnote_ref_alone():
    assert _clean_asset_description("200? SP Abbott Laboratories Common Stock") == (
        "SP Abbott Laboratories Common Stock"
    )
    assert _clean_asset_description("200?") == ""


# A fourth variant found live: the extraction window sometimes truncates the
# boilerplate label itself, chopping arbitrary leading characters off
# "F S: New S O:" rather than (or in addition to) what precedes it.
def test_clean_asset_description_strips_truncated_boilerplate_label_variants():
    assert _clean_asset_description(
        "S: New S O: Hern Family Foundation D: Exxon Mobile began trading as "
        "Exxon Mobile Holdings JT Honeywell Aerospace Inc. - Common"
    ) == (
        "Hern Family Foundation D: Exxon Mobile began trading as "
        "Exxon Mobile Holdings JT Honeywell Aerospace Inc. - Common"
    )
    assert _clean_asset_description(
        ": New S O: Richard R Larsen IRA D: Part of monthly portfolio rebalancing "
        "that account manager conducts Essex Property Trust, Inc. Common"
    ) == (
        "Richard R Larsen IRA D: Part of monthly portfolio rebalancing "
        "that account manager conducts Essex Property Trust, Inc. Common"
    )
    assert _clean_asset_description(
        "New S O: Richard R Larsen IRA D: Part of monthly portfolio rebalancing "
        "that account manager conducts Verisk Analytics, Inc. - Common Stock"
    ) == (
        "Richard R Larsen IRA D: Part of monthly portfolio rebalancing "
        "that account manager conducts Verisk Analytics, Inc. - Common Stock"
    )
    assert _clean_asset_description(
        "ew S O: Richard R Larsen IRA D: Part of monthly portfolio rebalancing "
        "that account manager conducts Mondelez International, Inc. - Class A"
    ) == (
        "Richard R Larsen IRA D: Part of monthly portfolio rebalancing "
        "that account manager conducts Mondelez International, Inc. - Class A"
    )


# House PTR forms use single-letter transaction-type codes; Senate rows (a separate
# source, senate_trades.py) use full words ("Purchase"/"Sale"/"Exchange") in the same
# transaction_type column. Without normalizing House's codes, a user sees "P" on one
# row and "Purchase" on the next for the identical concept.
def test_transaction_type_labels_cover_every_fields_re_alternative():
    # Every alternative in FIELDS_RE's transaction-type group must have a label,
    # or a real parsed row would silently fall back to the raw single-letter code.
    assert TRANSACTION_TYPE_LABELS["P"] == "Purchase"
    assert TRANSACTION_TYPE_LABELS["S"] == "Sale"
    assert TRANSACTION_TYPE_LABELS["S (partial)"] == "Sale (Partial)"
    assert TRANSACTION_TYPE_LABELS["S (full)"] == "Sale (Full)"
    assert TRANSACTION_TYPE_LABELS["E"] == "Exchange"


def test_parse_ptr_pdf_normalizes_house_transaction_type_to_full_word():
    text = "Jane Smith TX5 Apple Inc. - Common Stock (AAPL) P 01/15/2026 01/20/2026 $1,001 - $15,000"
    with patch("pdfplumber.open", lambda _bytes: _fake_pdf(text)):
        rows = _parse_ptr_pdf(b"fake-pdf-bytes")
    assert len(rows) == 1
    assert rows[0]["ticker"] == "AAPL"
    assert rows[0]["transaction_type"] == "Purchase"


def test_parse_ptr_pdf_normalizes_partial_sale_transaction_type():
    text = "Jane Smith TX5 Apple Inc. - Common Stock (AAPL) S (partial) 01/15/2026 01/20/2026 $1,001 - $15,000"
    with patch("pdfplumber.open", lambda _bytes: _fake_pdf(text)):
        rows = _parse_ptr_pdf(b"fake-pdf-bytes")
    assert len(rows) == 1
    assert rows[0]["transaction_type"] == "Sale (Partial)"


def test_is_valid_date_accepts_real_dates():
    assert _is_valid_date("12/31/2025") is True
    assert _is_valid_date("01/01/2026") is True


def test_is_valid_date_rejects_garbage():
    assert _is_valid_date("13/45/2026") is False
    assert _is_valid_date("not a date") is False
    assert _is_valid_date("") is False
