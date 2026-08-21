import { API_BASE, apiFetch, BackendUnreachableError } from "./api";

const UPLOAD_TIMEOUT_MS = 60_000; // a vision call is slower than a plain list fetch

export interface Holding {
  ticker: string;
  shares: number | null;
  value: number | null;
}

export interface PortfolioSnapshot {
  id: number;
  uploaded_at: string;
  holdings: Holding[];
}

export type RiskTolerance = "conservative" | "moderate" | "aggressive";

export interface RiskProfile {
  id: number;
  time_horizon: string | null;
  risk_tolerance: RiskTolerance;
  primary_goal: string | null;
  target_stock_pct: number;
  target_bond_pct: number;
  target_cash_pct: number;
  updated_at: string;
}

export interface RiskProfileInput {
  time_horizon?: string;
  risk_tolerance: RiskTolerance;
  primary_goal?: string;
}

export interface AllocationBucket {
  value: number;
  pct: number;
}

export interface Allocation {
  total_value: number;
  asset_class: Record<string, AllocationBucket>;
  sector: Record<string, AllocationBucket>;
  equity_value: number;
}

export interface AllocationGap {
  asset_class: string;
  current_pct: number;
  target_pct: number;
  diff_pct: number;
  direction: "overweight" | "underweight";
  message: string;
  suggested_funds: string[];
}

export interface SectorFlag {
  sector: string;
  pct: number;
  message: string;
}

export interface Recommendations {
  allocation: Allocation;
  target: Record<string, number>;
  gaps: AllocationGap[];
  sector_flags: SectorFlag[];
}

class ApiDetailError extends Error {}

async function readDetail(res: Response, fallback: string): Promise<string> {
  try {
    const body = await res.json();
    return typeof body.detail === "string" ? body.detail : fallback;
  } catch {
    return fallback;
  }
}

export class VisionNotConfiguredError extends Error {
  constructor(detail: string) {
    super(detail);
    this.name = "VisionNotConfiguredError";
  }
}

export async function uploadScreenshot(file: File): Promise<Holding[]> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await apiFetch("/api/portfolio/upload", { method: "POST", body: formData }, UPLOAD_TIMEOUT_MS);
  if (res.status === 503) {
    throw new VisionNotConfiguredError(await readDetail(res, "Screenshot parsing isn't configured yet."));
  }
  if (!res.ok) {
    throw new ApiDetailError(await readDetail(res, `Failed to parse screenshot: ${res.status}`));
  }
  const data = await res.json();
  return data.holdings;
}

export async function saveSnapshot(holdings: Holding[]): Promise<{ id: number }> {
  const res = await apiFetch("/api/portfolio/snapshots", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(holdings),
  });
  if (!res.ok) throw new Error(`Failed to save snapshot: ${res.status}`);
  return res.json();
}

export async function getLatestSnapshot(): Promise<PortfolioSnapshot | null> {
  const res = await apiFetch("/api/portfolio/latest");
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Failed to load portfolio snapshot: ${res.status}`);
  return res.json();
}

export async function getRiskProfile(): Promise<RiskProfile | null> {
  const res = await apiFetch("/api/portfolio/risk-profile");
  if (!res.ok) throw new Error(`Failed to load risk profile: ${res.status}`);
  return res.json();
}

export async function saveRiskProfile(input: RiskProfileInput): Promise<RiskProfile> {
  const res = await apiFetch("/api/portfolio/risk-profile", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(`Failed to save risk profile: ${res.status}`);
  return res.json();
}

export async function getRecommendations(): Promise<Recommendations | null> {
  const res = await apiFetch("/api/portfolio/recommendations");
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Failed to load recommendations: ${res.status}`);
  return res.json();
}

export function isBackendUnreachable(err: unknown): boolean {
  return err instanceof BackendUnreachableError;
}

export { API_BASE };
