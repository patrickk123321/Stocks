from app.csv_export import rows_to_csv


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
