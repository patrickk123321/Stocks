import { API_BASE, apiFetch, BackendUnreachableError, throwForStatus } from "./api";

export interface BotConfig {
  id: number;
  enabled: boolean;
  max_trade_dollars: number;
  max_trades_per_day: number;
  cash_buffer_pct: number;
  updated_at: string | null;
}

export interface BotConfigInput {
  enabled: boolean;
  max_trade_dollars: number;
  max_trades_per_day: number;
  cash_buffer_pct: number;
}

export interface AlpacaAccount {
  cash: number;
  buying_power: number;
  equity: number;
  portfolio_value: number;
}

export interface Position {
  ticker: string;
  shares: number;
  value: number;
}

export interface BotAccountInfo {
  account: AlpacaAccount;
  positions: Position[];
  market_open: boolean;
}

export interface BotTrade {
  id: number;
  run_date: string;
  ticker: string;
  side: string;
  notional: number;
  asset_class: string;
  rationale: string;
  status: string;
  alpaca_order_id: string | null;
  error_message: string | null;
  placed_at: string;
  filled_at: string | null;
  filled_avg_price: number | null;
}

export interface BotRunResult {
  skipped?: string;
  inserted?: number;
  errors?: number;
  trades: BotTrade[];
}

export class AlpacaNotConfiguredError extends Error {
  constructor(detail: string) {
    super(detail);
    this.name = "AlpacaNotConfiguredError";
  }
}

async function readDetail(res: Response, fallback: string): Promise<string> {
  try {
    const body = await res.json();
    return typeof body.detail === "string" ? body.detail : fallback;
  } catch {
    return fallback;
  }
}

// SQLite stores `enabled` as 0/1, and it comes back through JSON as a number,
// not a boolean — coerced here so BotConfig.enabled is always a real boolean
// for every caller (a raw 0 fed into aria-checked renders the invalid ARIA
// string "0" instead of "false").
function normalizeBotConfig(data: BotConfig): BotConfig {
  return { ...data, enabled: Boolean(data.enabled) };
}

export async function getBotConfig(): Promise<BotConfig> {
  const res = await apiFetch("/api/bot/config");
  if (!res.ok) throw new Error(`Failed to load bot config: ${res.status}`);
  return normalizeBotConfig(await res.json());
}

export async function saveBotConfig(input: BotConfigInput): Promise<BotConfig> {
  const res = await apiFetch("/api/bot/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(`Failed to save bot config: ${res.status}`);
  return normalizeBotConfig(await res.json());
}

// Unlike the other GET endpoints here, this one makes 3 sequential real calls
// to Alpaca's API rather than a local SQLite query — a cold outbound
// connection (e.g. right after a backend restart) can take several seconds,
// so the default 15s list-endpoint timeout is too tight for it.
const ACCOUNT_TIMEOUT_MS = 30_000;

export async function getBotAccount(): Promise<BotAccountInfo> {
  const res = await apiFetch("/api/bot/account", {}, ACCOUNT_TIMEOUT_MS);
  if (res.status === 503) {
    throw new AlpacaNotConfiguredError(await readDetail(res, "Auto-trading isn't configured yet."));
  }
  if (!res.ok) throw new Error(`Failed to load account info: ${res.status}`);
  return res.json();
}

export async function getBotTrades(limit = 50, offset = 0): Promise<{ rows: BotTrade[]; total: number }> {
  const res = await apiFetch(`/api/bot/trades?limit=${limit}&offset=${offset}`);
  if (!res.ok) throw new Error(`Failed to load trade history: ${res.status}`);
  return res.json();
}

export async function runBotNow(): Promise<BotRunResult> {
  const res = await apiFetch("/api/bot/run", { method: "POST" }, 30_000);
  if (res.status === 503) {
    throw new AlpacaNotConfiguredError(await readDetail(res, "Auto-trading isn't configured yet."));
  }
  if (!res.ok) {
    await throwForStatus(res, `Failed to run the bot: ${res.status}`);
  }
  return res.json();
}

export function isBackendUnreachable(err: unknown): boolean {
  return err instanceof BackendUnreachableError;
}

export { API_BASE };
