"""Regression tests for the House PTR PDF text cleanup — this is the most fragile,
best-effort part of the codebase (see congress_trades.py's module docstring) and
the one place a real data-corruption bug was already found and fixed this project:
the PDF template's field labels ("Filing Status:", "Sub-Holding Of:") extract as
literal NUL bytes because pdfplumber can't map that font's glyphs to Unicode.
"""

from app.sources.congress_trades import _clean_asset_description, _is_valid_date


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


def test_is_valid_date_accepts_real_dates():
    assert _is_valid_date("12/31/2025") is True
    assert _is_valid_date("01/01/2026") is True


def test_is_valid_date_rejects_garbage():
    assert _is_valid_date("13/45/2026") is False
    assert _is_valid_date("not a date") is False
    assert _is_valid_date("") is False
