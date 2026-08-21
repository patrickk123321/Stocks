"use client";

import { ArrowsClockwise, CaretDown, CaretUp, CaretUpDown, Database, MagnifyingGlass, WarningCircle } from "@phosphor-icons/react";
import { ReactNode, useEffect, useState } from "react";
import { BackendUnreachableError, Category, fetchTrades, refreshTrades, SortOrder } from "../lib/api";

interface Column {
  key: string;
  label: string;
}

interface TradeTableProps {
  category: Category;
  searchPlaceholder: string;
  columns: Column[];
}

const PAGE_SIZE = 50;
const SKELETON_ROWS = 8;

const BUY_CODES = new Set(["P", "A", "M"]);
const SELL_CODES = new Set(["S", "D", "F"]);

function badge(label: string, tone: "positive" | "negative" | "neutral") {
  const cls =
    tone === "positive"
      ? "bg-positive/15 text-positive"
      : tone === "negative"
        ? "bg-destructive/15 text-destructive"
        : "bg-muted text-muted-foreground";
  return <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${cls}`}>{label}</span>;
}

function renderCell(key: string, value: unknown): ReactNode {
  const str = value === null || value === undefined || value === "" ? "" : String(value);
  if (!str) return <span className="text-muted-foreground/50">—</span>;

  if (key === "acquired_disposed") {
    if (str === "A") return badge("Acquired", "positive");
    if (str === "D") return badge("Disposed", "negative");
    return badge(str, "neutral");
  }

  if (key === "transaction_code") {
    if (BUY_CODES.has(str)) return badge(str, "positive");
    if (SELL_CODES.has(str)) return badge(str, "negative");
    return badge(str, "neutral");
  }

  if (key === "transaction_type") {
    const upper = str.toUpperCase();
    if (upper.startsWith("P")) return badge(str, "positive");
    if (upper.startsWith("S")) return badge(str, "negative");
    return badge(str, "neutral");
  }

  return str;
}

export default function TradeTable({ category, searchPlaceholder, columns }: TradeTableProps) {
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [total, setTotal] = useState(0);
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState<string | undefined>(undefined);
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async (q: string, sort: string | undefined, order: SortOrder) => {
    setLoading(true);
    setError(null);
    try {
      const page = await fetchTrades(category, q, { sort, order, limit: PAGE_SIZE, offset: 0 });
      setRows(page.rows);
      setTotal(page.total);
    } catch (err) {
      setError(err instanceof BackendUnreachableError ? err.message : "Something went wrong loading this data.");
    } finally {
      setLoading(false);
    }
  };

  const loadMore = async () => {
    setLoadingMore(true);
    setError(null);
    try {
      const page = await fetchTrades(category, query, { sort: sortKey, order: sortOrder, limit: PAGE_SIZE, offset: rows.length });
      setRows((prev) => [...prev, ...page.rows]);
      setTotal(page.total);
    } catch (err) {
      setError(err instanceof BackendUnreachableError ? err.message : "Couldn't load more rows — try again.");
    } finally {
      setLoadingMore(false);
    }
  };

  useEffect(() => {
    setQuery("");
    setSortKey(undefined);
    setSortOrder("desc");
    load("", undefined, "desc");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [category]);

  const handleSort = (key: string) => {
    const nextOrder: SortOrder = sortKey === key && sortOrder === "desc" ? "asc" : "desc";
    setSortKey(key);
    setSortOrder(nextOrder);
    load(query, key, nextOrder);
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    setError(null);
    try {
      await refreshTrades(category);
      await load(query, sortKey, sortOrder);
    } catch (err) {
      setError(err instanceof BackendUnreachableError ? err.message : "Refresh failed — try again in a moment.");
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
        <div className="relative flex-1 sm:min-w-[240px]">
          <MagnifyingGlass
            size={18}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && load(query, sortKey, sortOrder)}
            placeholder={searchPlaceholder}
            className="w-full rounded-lg border border-border bg-card py-2.5 pl-10 pr-3 text-base text-card-foreground placeholder:text-muted-foreground outline-none transition-colors focus:border-accent focus:ring-2 focus:ring-accent/40 sm:text-sm"
          />
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => load(query, sortKey, sortOrder)}
            disabled={loading}
            className="flex-1 cursor-pointer rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-on-accent transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50 sm:flex-none"
          >
            {loading ? "Searching…" : "Search"}
          </button>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex flex-1 cursor-pointer items-center justify-center gap-2 rounded-lg border border-border px-4 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50 sm:flex-none"
          >
            <ArrowsClockwise size={16} className={refreshing ? "animate-spin" : ""} aria-hidden="true" />
            {refreshing ? "Refreshing…" : "Refresh now"}
          </button>
        </div>
      </div>

      {!loading && !error && total > 0 && (
        <p className="text-xs font-medium text-muted-foreground">{total.toLocaleString()} result{total === 1 ? "" : "s"}</p>
      )}

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          <WarningCircle size={18} aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}

      <div className="overflow-x-auto rounded-lg border border-border bg-card">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-muted">
            <tr>
              {columns.map((col) => {
                const active = sortKey === col.key;
                return (
                  <th key={col.key} className="whitespace-nowrap px-4 py-3 font-sans font-semibold text-muted-foreground">
                    <button
                      onClick={() => handleSort(col.key)}
                      aria-sort={active ? (sortOrder === "asc" ? "ascending" : "descending") : "none"}
                      className={`flex cursor-pointer items-center gap-1 text-xs font-semibold tracking-wide uppercase transition-colors hover:text-foreground ${
                        active ? "text-foreground" : ""
                      }`}
                    >
                      {col.label}
                      {active ? (
                        sortOrder === "asc" ? (
                          <CaretUp size={12} weight="bold" className="text-accent" aria-hidden="true" />
                        ) : (
                          <CaretDown size={12} weight="bold" className="text-accent" aria-hidden="true" />
                        )
                      ) : (
                        <CaretUpDown size={12} className="opacity-40" aria-hidden="true" />
                      )}
                    </button>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {loading && rows.length === 0
              ? Array.from({ length: SKELETON_ROWS }).map((_, i) => (
                  <tr key={i} className="border-t border-border">
                    {columns.map((col) => (
                      <td key={col.key} className="px-4 py-3.5">
                        <div className="h-4 w-full max-w-24 animate-pulse rounded bg-muted" />
                      </td>
                    ))}
                  </tr>
                ))
              : rows.map((row, i) => (
                  <tr key={i} className="border-t border-border transition-colors hover:bg-muted/50">
                    {columns.map((col) => (
                      <td key={col.key} className="whitespace-nowrap px-4 py-3.5 font-mono text-[0.9rem] text-card-foreground">
                        {renderCell(col.key, row[col.key])}
                      </td>
                    ))}
                  </tr>
                ))}
            {rows.length === 0 && !loading && !error && (
              <tr>
                <td colSpan={columns.length} className="px-4 py-16">
                  <div className="flex flex-col items-center gap-3 text-center">
                    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
                      <Database size={22} aria-hidden="true" />
                    </div>
                    <p className="max-w-sm font-sans text-sm leading-relaxed text-muted-foreground">
                      No results yet. The daily scrape runs at 9am — or click &quot;Refresh now&quot; to fetch the latest filings.
                    </p>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {rows.length > 0 && rows.length < total && (
        <button
          onClick={loadMore}
          disabled={loadingMore}
          className="cursor-pointer self-center rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loadingMore ? "Loading…" : `Load more (${rows.length} of ${total.toLocaleString()})`}
        </button>
      )}
    </div>
  );
}
