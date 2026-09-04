"use client";

import { ArrowSquareOut, ChartLineDown, ChartLineUp, Sparkle, WarningCircle } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { BackendUnreachableError, PositionChangeType, fetchPositionChanges } from "../lib/api";
import { formatMeta } from "../lib/tradeFormat";

const FILTERS: { key: PositionChangeType | "ALL"; label: string }[] = [
  { key: "ALL", label: "All changes" },
  { key: "NEW", label: "New positions" },
  { key: "EXITED", label: "Exited positions" },
  { key: "CHANGED", label: "Changed" },
];

const PAGE_SIZE = 50;
const FOCUS_RING = "focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/50";

function changeBadge(type: string, pctChange: number | null) {
  if (type === "NEW") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-positive/15 px-2 py-0.5 text-xs font-semibold text-positive">
        <Sparkle size={11} weight="fill" aria-hidden="true" />
        New
      </span>
    );
  }
  if (type === "EXITED") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-destructive/15 px-2 py-0.5 text-xs font-semibold text-destructive">
        Exited
      </span>
    );
  }
  const up = (pctChange ?? 0) > 0;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${
        up ? "bg-positive/15 text-positive" : "bg-destructive/15 text-destructive"
      }`}
    >
      {up ? <ChartLineUp size={11} weight="bold" aria-hidden="true" /> : <ChartLineDown size={11} weight="bold" aria-hidden="true" />}
      {up ? "+" : ""}
      {pctChange}%
    </span>
  );
}

export default function PositionChanges() {
  const [filter, setFilter] = useState<PositionChangeType | "ALL">("ALL");
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async (type: PositionChangeType | "ALL") => {
    setLoading(true);
    setError(null);
    try {
      const page = await fetchPositionChanges(type === "ALL" ? undefined : type, PAGE_SIZE, 0);
      setRows(page.rows);
      setTotal(page.total);
    } catch (err) {
      setError(err instanceof BackendUnreachableError ? err.message : "Couldn't load position changes.");
    } finally {
      setLoading(false);
    }
  };

  const loadMore = async () => {
    setLoadingMore(true);
    try {
      const page = await fetchPositionChanges(filter === "ALL" ? undefined : filter, PAGE_SIZE, rows.length);
      setRows((prev) => [...prev, ...page.rows]);
      setTotal(page.total);
    } catch {
      setError("Couldn't load more — try again.");
    } finally {
      setLoadingMore(false);
    }
  };

  useEffect(() => {
    load(filter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  return (
    <div className="flex flex-col gap-3">
      <p className="text-xs leading-relaxed text-muted-foreground">
        Diffs each institution&apos;s two most recent 13F filing periods to surface new positions, exited positions, and meaningful
        share-count changes — derived entirely from filings already tracked, not a new data source. A filer needs at least two
        reporting periods on file before it can show up here.
      </p>

      <div className="flex flex-wrap gap-1.5 rounded-xl border border-border bg-card p-1.5">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`cursor-pointer rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${FOCUS_RING} ${
              filter === f.key ? "bg-accent/15 text-accent-text" : "text-muted-foreground hover:bg-muted hover:text-foreground"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {!loading && !error && rows.length > 0 && (
        <p className="text-xs font-medium text-muted-foreground">{total.toLocaleString()} change{total === 1 ? "" : "s"}</p>
      )}

      {error && (
        <div
          role="alert"
          className="flex items-center gap-2 rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive"
        >
          <WarningCircle size={18} aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}

      <div className="overflow-hidden rounded-lg border border-border bg-card" role={rows.length > 0 ? "list" : undefined}>
        {loading ? (
          Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className={`flex items-center justify-between gap-4 px-4 py-3.5 ${i > 0 ? "border-t border-border" : ""}`}>
              <div className="h-4 w-48 animate-pulse rounded bg-muted" />
              <div className="h-4 w-20 animate-pulse rounded bg-muted" />
            </div>
          ))
        ) : rows.length === 0 && !error ? (
          <p className="px-4 py-16 text-center text-sm leading-relaxed text-muted-foreground">
            No position changes detected yet. This needs at least two 13F filing periods on file for the same institution — check
            back after the next quarterly filing cycle, or once more historical data has been backfilled.
          </p>
        ) : (
          rows.map((row, i) => {
            const sourceUrl = row.source_url ? String(row.source_url) : null;
            return (
              <div
                key={i}
                role="listitem"
                className={`flex items-center justify-between gap-4 px-4 py-3.5 ${i > 0 ? "border-t border-border" : ""}`}
              >
                <div className="flex min-w-0 items-center gap-3">
                  {changeBadge(String(row.change_type), row.pct_change as number | null)}
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-card-foreground">{String(row.filer_name ?? "Unknown")}</p>
                    <p className="truncate font-mono text-xs text-muted-foreground">
                      {String(row.issuer_name ?? "")} · {String(row.cusip ?? "")}
                    </p>
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <div className="text-right">
                    <p className="font-mono text-xs text-card-foreground">
                      {row.change_type === "EXITED" ? formatMeta(row.prior_shares) : formatMeta(row.shares)} sh
                    </p>
                    <p className="text-xs text-muted-foreground">{String(row.period_of_report ?? "")}</p>
                  </div>
                  {sourceUrl && (
                    <a
                      href={sourceUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      title="View filing"
                      aria-label="View filing"
                      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground ${FOCUS_RING}`}
                    >
                      <ArrowSquareOut size={14} aria-hidden="true" />
                    </a>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {rows.length > 0 && rows.length < total && (
        <button
          onClick={loadMore}
          disabled={loadingMore}
          className={`cursor-pointer self-center rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50 ${FOCUS_RING}`}
        >
          {loadingMore ? "Loading…" : `Load more (${rows.length} of ${total.toLocaleString()})`}
        </button>
      )}
    </div>
  );
}
