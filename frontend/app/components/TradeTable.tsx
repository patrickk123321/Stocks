"use client";

import {
  ArrowSquareOut,
  ArrowsClockwise,
  CaretDown,
  CaretUp,
  Database,
  DownloadSimple,
  MagnifyingGlass,
  ShieldCheck,
  WarningCircle,
  X,
} from "@phosphor-icons/react";
import Link from "next/link";
import { useEffect, useState } from "react";
import {
  BackendUnreachableError,
  Category,
  ScrapeStatus,
  buildExportUrl,
  fetchStatus,
  fetchTrades,
  refreshTrades,
  SortOrder,
} from "../lib/api";
import { badge, badgeLabel, badgeTone, formatMeta, formatRelativeTime, renderCell } from "../lib/tradeFormat";
import StatTiles from "./StatTiles";

interface Column {
  key: string;
  label: string;
}

export interface RowSource {
  label: string;
  note: string;
  verified: boolean;
}

export interface SummaryConfig {
  actorLabel: string;
  actorKey: string;
  targetTickerKey?: string;
  targetNameKey: string;
  badgeKey?: string;
  dateKey: string;
  metaKey?: string;
  metaLabel?: string;
  metaFormat?: "currency";
  sourceLabel: string;
  sourceNote: string;
  sourceVerified: boolean;
  /** Overrides sourceLabel/sourceNote/sourceVerified per row when a category mixes
   * sources of differing reliability (e.g. congress: House PDF vs. Senate via FMP). */
  sourceFor?: (row: Record<string, unknown>) => RowSource;
}

interface TradeTableProps {
  category: Category;
  searchPlaceholder: string;
  columns: Column[];
  summary: SummaryConfig;
  emptyIcon?: typeof Database;
}

interface Filters {
  q: string;
  sort: string | undefined;
  order: SortOrder;
  dateFrom: string;
  dateTo: string;
  actor: string | null;
}

const PAGE_SIZE = 50;
const SKELETON_ROWS = 8;
const FOCUS_RING = "focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/50";
const DEFAULT_FILTERS: Filters = { q: "", sort: undefined, order: "desc", dateFrom: "", dateTo: "", actor: null };

export default function TradeTable({ category, searchPlaceholder, columns, summary, emptyIcon: EmptyIcon = Database }: TradeTableProps) {
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [total, setTotal] = useState(0);
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [loadToken, setLoadToken] = useState(0);
  const [lastRun, setLastRun] = useState<ScrapeStatus | null>(null);

  const refreshStatus = async () => {
    try {
      const status = await fetchStatus();
      setLastRun(status[category] ?? null);
    } catch {
      // Non-critical — the page still works without a last-run indicator.
    }
  };

  const load = async (next: Filters) => {
    setLoading(true);
    setError(null);
    setExpanded(null);
    setFilters(next);
    try {
      const page = await fetchTrades(category, next.q, {
        sort: next.sort,
        order: next.order,
        limit: PAGE_SIZE,
        offset: 0,
        dateFrom: next.dateFrom || undefined,
        dateTo: next.dateTo || undefined,
        actor: next.actor || undefined,
      });
      setRows(page.rows);
      setTotal(page.total);
      setLoadToken((t) => t + 1);
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
      const page = await fetchTrades(category, filters.q, {
        sort: filters.sort,
        order: filters.order,
        limit: PAGE_SIZE,
        offset: rows.length,
        dateFrom: filters.dateFrom || undefined,
        dateTo: filters.dateTo || undefined,
        actor: filters.actor || undefined,
      });
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
    load(DEFAULT_FILTERS);
    refreshStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [category]);

  const handleActorClick = (actor: string) => {
    setQuery("");
    load({ ...filters, q: "", actor });
  };

  const handleClearActor = () => load({ ...filters, actor: null });

  const handleRefresh = async () => {
    setRefreshing(true);
    setError(null);
    try {
      await refreshTrades(category);
      await load(filters);
      await refreshStatus();
    } catch (err) {
      setError(err instanceof BackendUnreachableError ? err.message : "Refresh failed — try again in a moment.");
    } finally {
      setRefreshing(false);
    }
  };

  const exportUrl = buildExportUrl(category, filters.q, {
    sort: filters.sort,
    order: filters.order,
    dateFrom: filters.dateFrom || undefined,
    dateTo: filters.dateTo || undefined,
    actor: filters.actor || undefined,
  });

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
            onKeyDown={(e) => e.key === "Enter" && load({ ...filters, q: query })}
            placeholder={searchPlaceholder}
            className="w-full rounded-lg border border-border bg-card py-2.5 pl-10 pr-3 text-base text-card-foreground placeholder:text-muted-foreground outline-none transition-colors focus:border-accent focus:ring-2 focus:ring-accent/40 sm:text-sm"
          />
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => load({ ...filters, q: query })}
            disabled={loading}
            className={`flex-1 cursor-pointer rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-on-accent transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50 sm:flex-none ${FOCUS_RING}`}
          >
            {loading ? "Searching…" : "Search"}
          </button>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className={`flex flex-1 cursor-pointer items-center justify-center gap-2 rounded-lg border border-border px-4 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50 sm:flex-none ${FOCUS_RING}`}
          >
            <ArrowsClockwise size={16} className={refreshing ? "animate-spin" : ""} aria-hidden="true" />
            {refreshing ? "Refreshing…" : "Refresh now"}
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1.5 text-xs">
          <label htmlFor={`date-from-${category}`} className="text-muted-foreground">
            From
          </label>
          <input
            id={`date-from-${category}`}
            type="date"
            value={filters.dateFrom}
            onChange={(e) => load({ ...filters, dateFrom: e.target.value })}
            className={`cursor-pointer rounded-md border border-border bg-card px-2 py-1.5 text-xs text-card-foreground outline-none focus:border-accent ${FOCUS_RING}`}
          />
        </div>
        <div className="flex items-center gap-1.5 text-xs">
          <label htmlFor={`date-to-${category}`} className="text-muted-foreground">
            To
          </label>
          <input
            id={`date-to-${category}`}
            type="date"
            value={filters.dateTo}
            onChange={(e) => load({ ...filters, dateTo: e.target.value })}
            className={`cursor-pointer rounded-md border border-border bg-card px-2 py-1.5 text-xs text-card-foreground outline-none focus:border-accent ${FOCUS_RING}`}
          />
        </div>

        {filters.actor && (
          <span className="flex items-center gap-1.5 rounded-full bg-accent/15 py-1 pl-3 pr-1.5 text-xs font-medium text-accent">
            {summary.actorLabel}: {filters.actor}
            <button
              onClick={handleClearActor}
              aria-label={`Clear filter for ${filters.actor}`}
              className={`flex h-4 w-4 cursor-pointer items-center justify-center rounded-full hover:bg-accent/20 ${FOCUS_RING}`}
            >
              <X size={10} weight="bold" aria-hidden="true" />
            </button>
          </span>
        )}

        <a
          href={exportUrl}
          className={`ml-auto flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-muted ${FOCUS_RING}`}
        >
          <DownloadSimple size={13} aria-hidden="true" />
          Export CSV
        </a>
      </div>

      {!loading && !error && rows.length > 0 && <StatTiles total={total} rows={rows} summary={summary} />}

      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1.5">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <span
            className={`flex items-center gap-1 text-xs ${summary.sourceVerified ? "text-positive" : "text-warning"}`}
            title={summary.sourceNote}
          >
            {summary.sourceVerified && <ShieldCheck size={13} weight="fill" aria-hidden="true" />}
            {summary.sourceLabel}
          </span>
          {lastRun && (
            <span
              className={`flex items-center gap-1 text-xs ${lastRun.error_count !== 0 ? "text-warning" : "text-muted-foreground"}`}
              title={lastRun.error_count > 0 ? `${lastRun.error_count} filing(s) failed to fetch/parse on the last scrape` : lastRun.error_count < 0 ? "The last scrape failed entirely — check the backend logs" : undefined}
            >
              {lastRun.error_count !== 0 && <WarningCircle size={13} weight="fill" aria-hidden="true" />}
              Last scrape {formatRelativeTime(lastRun.ran_at)}
              {lastRun.error_count > 0 ? ` · ${lastRun.error_count} failed` : lastRun.error_count < 0 ? " · scrape failed" : ""}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 text-xs">
          <label htmlFor={`sort-${category}`} className="text-muted-foreground">
            Sort by
          </label>
          <select
            id={`sort-${category}`}
            value={filters.sort ?? ""}
            onChange={(e) => load({ ...filters, sort: e.target.value || undefined })}
            className={`cursor-pointer rounded-md border border-border bg-card px-2 py-1.5 text-xs text-card-foreground outline-none focus:border-accent ${FOCUS_RING}`}
          >
            <option value="">Most recent</option>
            {columns.map((col) => (
              <option key={col.key} value={col.key}>
                {col.label}
              </option>
            ))}
          </select>
          <button
            onClick={() => load({ ...filters, order: filters.order === "desc" ? "asc" : "desc" })}
            aria-label={filters.order === "asc" ? "Sort descending" : "Sort ascending"}
            className={`flex h-7 w-7 cursor-pointer items-center justify-center rounded-md border border-border text-muted-foreground transition-colors hover:bg-muted hover:text-foreground ${FOCUS_RING}`}
          >
            {filters.order === "asc" ? <CaretUp size={13} aria-hidden="true" /> : <CaretDown size={13} aria-hidden="true" />}
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          <WarningCircle size={18} aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}

      <div className="overflow-hidden rounded-lg border border-border bg-card" role={rows.length > 0 ? "list" : undefined}>
        {loading && rows.length === 0 ? (
          Array.from({ length: SKELETON_ROWS }).map((_, i) => (
            <div key={i} className={`flex items-center justify-between gap-4 px-4 py-3.5 ${i > 0 ? "border-t border-border" : ""}`}>
              <div className="h-4 w-40 animate-pulse rounded bg-muted" />
              <div className="h-4 w-24 animate-pulse rounded bg-muted" />
            </div>
          ))
        ) : rows.length === 0 && !error ? (
          <div className="flex flex-col items-center gap-3 px-4 py-16 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
              <EmptyIcon size={22} aria-hidden="true" />
            </div>
            <p className="max-w-sm text-sm leading-relaxed text-muted-foreground">
              {filters.actor || filters.dateFrom || filters.dateTo
                ? "No results match these filters."
                : 'No results yet. The daily scrape runs at 9am — or click "Refresh now" to fetch the latest filings.'}
            </p>
          </div>
        ) : (
          rows.map((row, i) => {
            const isOpen = expanded === i;
            const actor = String(row[summary.actorKey] ?? "Unknown");
            const ticker = summary.targetTickerKey ? String(row[summary.targetTickerKey] ?? "") : "";
            // Institutions' "ticker" slot is actually a CUSIP (13F filings don't report
            // ticker symbols) — only link to the cross-category ticker page for real tickers.
            const tickerLinks = summary.targetTickerKey !== "cusip";
            const targetName = String(row[summary.targetNameKey] ?? "");
            const badgeValue = summary.badgeKey ? String(row[summary.badgeKey] ?? "") : "";
            const sourceUrl = row.source_url ? String(row.source_url) : null;
            const tone = summary.badgeKey && badgeValue ? badgeTone(summary.badgeKey, badgeValue) : null;
            const barClass = tone === "positive" ? "bg-positive" : tone === "negative" ? "bg-destructive" : tone === "neutral" ? "bg-border" : "bg-accent";
            // Keying on loadToken (bumped once per fresh load/search/sort/category-switch, not on
            // loadMore or expand/collapse) makes the entrance animation replay on a fresh result set
            // without replaying every time a row is merely toggled open or closed.
            const rowKey = `${loadToken}-${i}`;
            const panelId = `trade-row-panel-${category}-${rowKey}`;
            const chamber = typeof row.chamber === "string" ? row.chamber : null;
            const rowSource = summary.sourceFor?.(row) ?? {
              label: summary.sourceLabel,
              note: summary.sourceNote,
              verified: summary.sourceVerified,
            };

            const toggleExpand = () => setExpanded(isOpen ? null : i);

            return (
              <div key={rowKey} role="listitem">
                <div
                  role="button"
                  tabIndex={0}
                  onClick={toggleExpand}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      toggleExpand();
                    }
                  }}
                  aria-expanded={isOpen}
                  aria-controls={panelId}
                  className={`group relative flex w-full cursor-pointer items-center justify-between gap-4 px-4 py-3.5 text-left transition-colors hover:bg-muted/50 animate-fade-up ${FOCUS_RING} ${
                    i > 0 ? "border-t border-border" : ""
                  } ${isOpen ? "bg-muted/40" : ""}`}
                  style={{ animationDelay: `${Math.min(i, 10) * 30}ms` }}
                >
                  <span
                    aria-hidden="true"
                    className={`absolute inset-y-0 left-0 w-0.5 ${barClass} transition-opacity ${
                      isOpen ? "opacity-100" : "opacity-0 group-hover:opacity-60"
                    }`}
                  />
                  <div className="flex min-w-0 items-center gap-3">
                    {badgeValue && badge(badgeLabel(summary.badgeKey!, badgeValue), badgeTone(summary.badgeKey!, badgeValue))}
                    <div className="min-w-0">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleActorClick(actor);
                        }}
                        title={`Show only ${actor}'s ${summary.actorLabel.toLowerCase()} activity`}
                        className={`truncate text-left text-sm font-medium text-card-foreground hover:text-accent hover:underline ${FOCUS_RING} rounded`}
                      >
                        {actor}
                      </button>
                      <p className="truncate font-mono text-xs text-muted-foreground">
                        {ticker &&
                          (tickerLinks ? (
                            <Link
                              href={`/ticker/${encodeURIComponent(ticker)}`}
                              onClick={(e) => e.stopPropagation()}
                              title={`See everything tracked for ${ticker}`}
                              className={`font-semibold text-foreground hover:text-accent hover:underline ${FOCUS_RING} rounded`}
                            >
                              {ticker}
                            </Link>
                          ) : (
                            <span className="font-semibold text-foreground">{ticker}</span>
                          ))}
                        {ticker && targetName ? " · " : ""}
                        {targetName}
                      </p>
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-4">
                    {chamber && (
                      <span className="hidden rounded-full bg-muted px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-muted-foreground sm:inline">
                        {chamber}
                      </span>
                    )}
                    <div className="hidden text-right sm:block">
                      {summary.metaKey && (
                        <p className="font-mono text-xs text-card-foreground">
                          {formatMeta(row[summary.metaKey], summary.metaFormat)}
                        </p>
                      )}
                      <p className="text-xs text-muted-foreground">{String(row[summary.dateKey] ?? "—")}</p>
                    </div>
                    <CaretDown
                      size={16}
                      className={`text-muted-foreground transition-transform ${isOpen ? "rotate-180" : ""}`}
                      aria-hidden="true"
                    />
                  </div>
                </div>

                {isOpen && (
                  <div id={panelId} role="region" className="border-t border-border bg-background/40 px-4 py-4">
                    <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3">
                      {columns.map((col) => (
                        <div key={col.key} className="min-w-0">
                          <dt className="text-[0.65rem] font-semibold uppercase tracking-wide text-muted-foreground">{col.label}</dt>
                          <dd className="mt-0.5 truncate font-mono text-sm text-card-foreground">{renderCell(col.key, row[col.key])}</dd>
                        </div>
                      ))}
                    </dl>
                    <div className="mt-4 flex flex-col gap-2 border-t border-border pt-3 sm:flex-row sm:items-center sm:justify-between">
                      <div className="flex max-w-md flex-col gap-1">
                        <span
                          className={`flex items-center gap-1 text-xs font-medium ${rowSource.verified ? "text-positive" : "text-warning"}`}
                        >
                          {rowSource.verified && <ShieldCheck size={12} weight="fill" aria-hidden="true" />}
                          {rowSource.label}
                        </span>
                        <p className="text-xs text-muted-foreground">{rowSource.note}</p>
                      </div>
                      {sourceUrl ? (
                        <a
                          href={sourceUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className={`flex w-fit items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-muted ${FOCUS_RING}`}
                        >
                          View original filing
                          <ArrowSquareOut size={13} aria-hidden="true" />
                        </a>
                      ) : (
                        <p className="text-xs text-muted-foreground/70">
                          Source link unavailable for this row — Refresh now to fetch it with a live link.
                        </p>
                      )}
                    </div>
                  </div>
                )}
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
