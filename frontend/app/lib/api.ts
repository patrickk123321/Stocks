export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export type Category = "insiders" | "institutions" | "congress";

export class BackendUnreachableError extends Error {
  constructor() {
    super(`Can't reach the backend at ${API_BASE} — make sure it's running.`);
    this.name = "BackendUnreachableError";
  }
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

export async function refreshTrades(category: Category): Promise<{ inserted: number; errors: number }> {
  const extra = category === "congress" ? `?year=${new Date().getFullYear()}` : "";
  const res = await apiFetch(`/api/${category}/refresh${extra}`, { method: "POST" }, REFRESH_TIMEOUT_MS);
  if (!res.ok) {
    throw new Error(`Failed to refresh ${category}: ${res.status}`);
  }
  return res.json();
}

export interface ScrapeStatus {
  ran_at: string;
  inserted: number;
  error_count: number;
}

export async function fetchStatus(): Promise<Record<Category, ScrapeStatus | null>> {
  const res = await apiFetch("/api/status");
  if (!res.ok) {
    throw new Error(`Failed to fetch status: ${res.status}`);
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
