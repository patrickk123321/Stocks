// Strips any trailing slash(es) — every call site below appends a path that
// starts with "/", so a trailing slash here would produce a "//" that 404s.
export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/+$/, "");

export type Category = "insiders" | "institutions" | "congress";

export class BackendUnreachableError extends Error {
  constructor() {
    super(`Can't reach the backend at ${API_BASE} — it may be down, or this site's origin may not be in the backend's CORS_ALLOWED_ORIGINS.`);
    this.name = "BackendUnreachableError";
  }
}

// Thrown when the backend's per-endpoint cooldown guard (app/rate_limit.py)
// rejects a call — a guard against an accidental double-click or client-side
// loop, not real rate-limiting. Carries the backend's own "wait Ns" message.
export class RateLimitedError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "RateLimitedError";
  }
}

export async function throwForStatus(res: Response, fallbackMessage: string): Promise<never> {
  if (res.status === 429) {
    const body = await res.json().catch(() => null);
    throw new RateLimitedError(body?.detail || "Please wait a moment before trying again.");
  }
  throw new Error(fallbackMessage);
}

const LIST_TIMEOUT_MS = 15_000;
// A real refresh triggers live scraping of SEC/House Clerk filings and can
// legitimately take well over a minute — a short timeout here would cancel
// a healthy in-progress scrape, not just catch a stalled connection.
const REFRESH_TIMEOUT_MS = 120_000;

export async function apiFetch(path: string, init: RequestInit = {}, timeoutMs = LIST_TIMEOUT_MS): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(`${API_BASE}${path}`, { ...init, signal: controller.signal });
  } catch {
    // A native fetch() error — network failure (connection refused, DNS
    // failure, CORS block) or our own abort on timeout — throws a generic
    // TypeError/AbortError with no useful detail; surface something actionable.
    throw new BackendUnreachableError();
  } finally {
    clearTimeout(timeout);
  }
}

export type SortOrder = "asc" | "desc";

export interface TradesPage {
  rows: Record<string, unknown>[];
  total: number;
}

export interface FetchTradesOptions {
  sort?: string;
  order?: SortOrder;
  limit?: number;
  offset?: number;
  dateFrom?: string;
  dateTo?: string;
  actor?: string;
  ticker?: string;
}

function buildTradesParams(q: string, options: FetchTradesOptions): URLSearchParams {
  const { sort, order, dateFrom, dateTo, actor, ticker } = options;
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (sort) params.set("sort", sort);
  if (order) params.set("order", order);
  if (dateFrom) params.set("date_from", dateFrom);
  if (dateTo) params.set("date_to", dateTo);
  if (actor) params.set("actor", actor);
  if (ticker) params.set("ticker", ticker);
  return params;
}

export async function fetchTrades(category: Category, q: string, options: FetchTradesOptions = {}): Promise<TradesPage> {
  const { limit = 50, offset = 0 } = options;
  const params = buildTradesParams(q, options);
  params.set("limit", String(limit));
  params.set("offset", String(offset));

  const res = await apiFetch(`/api/${category}?${params.toString()}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch ${category}: ${res.status}`);
  }
  return res.json();
}

export function buildExportUrl(category: Category, q: string, options: FetchTradesOptions = {}): string {
  const params = buildTradesParams(q, options);
  return `${API_BASE}/api/${category}/export?${params.toString()}`;
}

export interface ExportResult {
  blob: Blob;
  totalMatched: number;
  rowCount: number;
  truncated: boolean;
}

// Fetches the export via JS (rather than a plain <a href> navigation) so the
// truncation-signal response headers can be inspected before the download —
// see backend/app/csv_export.py's export_headers.
export async function fetchExportCsv(category: Category, q: string, options: FetchTradesOptions = {}): Promise<ExportResult> {
  const params = buildTradesParams(q, options);
  const res = await apiFetch(`/api/${category}/export?${params.toString()}`, {}, REFRESH_TIMEOUT_MS);
  if (!res.ok) {
    throw new Error(`Failed to export ${category}: ${res.status}`);
  }
  const totalMatched = Number(res.headers.get("X-Total-Matched") ?? "0");
  const rowCount = Number(res.headers.get("X-Export-Row-Count") ?? "0");
  const truncated = res.headers.get("X-Export-Truncated") === "true";
  const blob = await res.blob();
  return { blob, totalMatched, rowCount, truncated };
}

export interface ScrapeStatus {
  ran_at: string;
  inserted: number;
  error_count: number;
}

export async function fetchStatus(): Promise<Record<Category, ScrapeStatus | null>> {
  const res = await apiFetch("/api/status");
  if (!res.ok) {
    await throwForStatus(res, `Failed to fetch status: ${res.status}`);
  }
  return res.json();
}

export type PositionChangeType = "NEW" | "EXITED" | "CHANGED";

export async function fetchPositionChanges(
  changeType: PositionChangeType | undefined,
  limit: number,
  offset: number,
): Promise<TradesPage> {
  const params = new URLSearchParams();
  if (changeType) params.set("change_type", changeType);
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  const res = await apiFetch(`/api/institutions/changes?${params.toString()}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch position changes: ${res.status}`);
  }
  return res.json();
}

// Watchlist calls are the only ones that need the caller's identity, so only
// these attach a Clerk bearer token — everything above stays unauthenticated.
export type GetToken = () => Promise<string | null>;

// Throws a message carrying the actual backend response (status + body) or
// parse failure, rather than a generic "Failed to..." — surfaced directly in
// the watchlist page's error banner so the real cause is visible without
// needing DevTools.
async function authedJson<T>(path: string, getToken: GetToken, init: RequestInit = {}): Promise<T> {
  const token = await getToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await apiFetch(path, { ...init, headers });
  const text = await res.text();
  if (!res.ok) {
    throw new Error(`${path} -> ${res.status}: ${text || "(empty body)"} (token attached: ${Boolean(token)})`);
  }
  try {
    return text ? (JSON.parse(text) as T) : (undefined as T);
  } catch {
    throw new Error(`${path} -> ${res.status}: response wasn't valid JSON: ${text.slice(0, 200)}`);
  }
}

export interface WatchlistAlert {
  sent_at: string;
  ticker: string;
  member_name: string;
  chamber: string;
  transaction_date: string;
  amount_range: string;
  [key: string]: unknown;
}

export async function fetchWatchlist(getToken: GetToken): Promise<string[]> {
  const data = await authedJson<{ tickers: string[] }>("/api/watchlist", getToken);
  return data.tickers;
}

export async function addToWatchlist(ticker: string, getToken: GetToken): Promise<string[]> {
  const data = await authedJson<{ tickers: string[] }>("/api/watchlist", getToken, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticker }),
  });
  return data.tickers;
}

export async function removeFromWatchlist(ticker: string, getToken: GetToken): Promise<string[]> {
  const data = await authedJson<{ tickers: string[] }>(`/api/watchlist/${encodeURIComponent(ticker)}`, getToken, {
    method: "DELETE",
  });
  return data.tickers;
}

export async function fetchWatchlistAlerts(getToken: GetToken): Promise<WatchlistAlert[]> {
  const data = await authedJson<{ alerts: WatchlistAlert[] }>("/api/watchlist/alerts", getToken);
  return data.alerts;
}

export async function fetchUnreadAlertCount(getToken: GetToken): Promise<number> {
  const data = await authedJson<{ count: number }>("/api/watchlist/alerts/unread-count", getToken);
  return data.count;
}

export async function markAlertsSeen(getToken: GetToken): Promise<void> {
  await authedJson<{ count: number }>("/api/watchlist/alerts/seen", getToken, { method: "POST" });
}
