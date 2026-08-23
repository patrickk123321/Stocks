from app.csv_export import export_headers, rows_to_csv


def test_rows_to_csv_uses_given_column_order_and_ignores_extras():
    rows = [
        {"ticker": "AAPL", "owner_name": "Alice", "internal_id": 999},
        {"ticker": "MSFT", "owner_name": "Bob", "internal_id": 1000},
    ]
    csv_text = rows_to_csv(rows, ["ticker", "owner_name"])
    lines = csv_text.strip().splitlines()
    assert lines[0] == "ticker,owner_name"
    assert lines[1] == "AAPL,Alice"
    assert lines[2] == "MSFT,Bob"
    assert "internal_id" not in csv_text


def test_rows_to_csv_handles_missing_keys_as_blank():
    rows = [{"ticker": "AAPL"}]
    csv_text = rows_to_csv(rows, ["ticker", "owner_name"])
    lines = csv_text.strip().splitlines()
    assert lines[1] == "AAPL,"


def test_rows_to_csv_empty_rows_still_has_header():
    csv_text = rows_to_csv([], ["ticker", "owner_name"])
    assert csv_text.strip() == "ticker,owner_name"


def test_export_headers_not_truncated_when_row_count_matches_total():
    headers = export_headers("insider_trades.csv", 150, 150)
    assert headers["X-Total-Matched"] == "150"
    assert headers["X-Export-Row-Count"] == "150"
    assert headers["X-Export-Truncated"] == "false"
    assert headers["Content-Disposition"] == "attachment; filename=insider_trades.csv"


def test_export_headers_flags_truncation_when_row_count_below_total():
    headers = export_headers("congress_trades.csv", 20_000, 34_112)
    assert headers["X-Total-Matched"] == "34112"
    assert headers["X-Export-Row-Count"] == "20000"
    assert headers["X-Export-Truncated"] == "true"
