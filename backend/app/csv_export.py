import csv
import io


def rows_to_csv(rows: list[dict], columns: list[str]) -> str:
    """Renders `rows` as CSV text using exactly `columns`, in order — the caller
    picks the column list so export output stays stable even if a row dict
    happens to carry extra internal keys."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()
