const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export type Category = "insiders" | "institutions" | "congress";

export class BackendUnreachableError extends Error {
  constructor() {
    super(`Can't reach the backend at ${API_BASE} — make sure it's running.`);
    this.name = "BackendUnreachableError";
  }
}

async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(`${API_BASE}${path}`, init);
  } catch {
    // A native fetch() network error (connection refused, DNS failure, CORS
    // block) throws a generic "Failed to fetch" TypeError with no useful
    // detail — surface something actionable instead.
    throw new BackendUnreachableError();
  }
}

export async function fetchTrades(category: Category, q: string): Promise<Record<string, unknown>[]> {
  const params = new URLSearchParams();
  if (q) params.set("q", q);

  const res = await apiFetch(`/api/${category}?${params.toString()}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch ${category}: ${res.status}`);
  }
  return res.json();
}

export async function refreshTrades(category: Category): Promise<{ inserted: number }> {
  const extra = category === "congress" ? `?year=${new Date().getFullYear()}` : "";
  const res = await apiFetch(`/api/${category}/refresh${extra}`, { method: "POST" });
  if (!res.ok) {
    throw new Error(`Failed to refresh ${category}: ${res.status}`);
  }
  return res.json();
}
