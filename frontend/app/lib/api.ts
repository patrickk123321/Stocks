const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export type Category = "insiders" | "institutions" | "congress";

export interface Filters {
  ticker?: string;
  name?: string;
  startDate?: string;
  endDate?: string;
}

export async function fetchTrades(category: Category, filters: Filters): Promise<Record<string, unknown>[]> {
  const params = new URLSearchParams();
  if (filters.ticker) params.set("ticker", filters.ticker);
  if (filters.name) params.set("name", filters.name);
  if (filters.startDate) params.set("start_date", filters.startDate);
  if (filters.endDate) params.set("end_date", filters.endDate);

  const res = await fetch(`${API_BASE}/api/${category}?${params.toString()}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch ${category}: ${res.status}`);
  }
  return res.json();
}

export async function refreshTrades(category: Category): Promise<{ inserted: number }> {
  const extra = category === "congress" ? `?year=${new Date().getFullYear()}` : "";
  const res = await fetch(`${API_BASE}/api/${category}/refresh${extra}`, { method: "POST" });
  if (!res.ok) {
    throw new Error(`Failed to refresh ${category}: ${res.status}`);
  }
  return res.json();
}
