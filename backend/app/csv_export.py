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


def export_headers(filename: str, row_count: int, total_matched: int) -> dict[str, str]:
    """Response headers for a CSV export — beyond the download disposition,
    carries the truncation signal (query_all_rows caps at EXPORT_ROW_CAP) so a
    capped file doesn't silently look like the complete result set. Exposed to
    frontend JS via CORS's expose_headers in main.py."""
    return {
        "Content-Disposition": f"attachment; filename={filename}",
        "X-Total-Matched": str(total_matched),
        "X-Export-Row-Count": str(row_count),
        "X-Export-Truncated": "true" if row_count < total_matched else "false",
    }
