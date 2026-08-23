"use client";

import {
  ArrowsClockwise,
  Bank,
  ClockCounterClockwise,
  Info,
  WarningCircle,
} from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { fetchTrades } from "../lib/api";
import { AlpacaNotConfiguredError, BotAccountInfo, BotConfig, BotTrade, getBotTrades, runBotNow } from "../lib/botApi";
import BotSettingsForm from "./BotSettingsForm";

const FOCUS_RING = "focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/50";

function money(n: number): string {
  return `$${n.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

const STATUS_TONE: Record<string, string> = {
  submitted: "bg-warning/15 text-warning",
  filled: "bg-positive/15 text-positive",
  rejected: "bg-destructive/15 text-destructive",
  failed: "bg-destructive/15 text-destructive",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${STATUS_TONE[status] ?? "bg-muted text-muted-foreground"}`}>
      {status}
    </span>
  );
}

interface BotDashboardViewProps {
  config: BotConfig;
  account: BotAccountInfo | null;
  alpacaNotConfigured: string | null;
  onConfigSaved: () => void;
}

export default function BotDashboardView({ config, account, alpacaNotConfigured, onConfigSaved }: BotDashboardViewProps) {
  const [trades, setTrades] = useState<BotTrade[]>([]);
  const [tradesLoading, setTradesLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [runNotice, setRunNotice] = useState<string | null>(null);

  const loadTrades = async () => {
    setTradesLoading(true);
    try {
      const page = await getBotTrades();
      setTrades(page.rows);
    } catch {
      // Non-critical — the dashboard still works without trade history.
    } finally {
      setTradesLoading(false);
    }
  };

  useEffect(() => {
    loadTrades();
  }, []);

  const handleRunNow = async () => {
    setRunning(true);
    setRunError(null);
    setRunNotice(null);
    try {
      const result = await runBotNow();
      if (result.skipped) {
        setRunNotice("Already ran today — the bot runs at most once per calendar day.");
      } else {
        setRunNotice(`Placed ${result.inserted ?? 0} trade(s)${result.errors ? `, ${result.errors} failed` : ""}.`);
      }
      await loadTrades();
    } catch (err) {
      setRunError(
        err instanceof AlpacaNotConfiguredError ? err.message : err instanceof Error ? err.message : "Run failed — try again.",
      );
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start gap-2 rounded-lg border border-border bg-muted/50 px-4 py-3 text-xs leading-relaxed text-muted-foreground">
        <WarningCircle size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
        <span>Paper trading only — no real money is ever placed by this bot. Not investment advice.</span>
      </div>

      {alpacaNotConfigured && (
        <div role="status" className="flex items-start gap-2 rounded-lg border border-warning/40 bg-warning/10 px-4 py-3 text-sm text-warning">
          <WarningCircle size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
          <span>{alpacaNotConfigured}</span>
        </div>
      )}

      {account && (
        <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-6">
          <div className="flex items-center gap-2">
            <Bank size={18} className="text-accent" aria-hidden="true" />
            <h2 className="font-semibold text-card-foreground">Alpaca paper account</h2>
            <span
              className={`ml-auto flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
                account.market_open ? "bg-positive/15 text-positive" : "bg-muted text-muted-foreground"
              }`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${account.market_open ? "bg-positive" : "bg-muted-foreground"}`} aria-hidden="true" />
              {account.market_open ? "Market open" : "Market closed"}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div>
              <p className="text-xs text-muted-foreground">Equity</p>
              <p className="font-mono text-sm text-card-foreground">{money(account.account.equity)}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Cash</p>
              <p className="font-mono text-sm text-card-foreground">{money(account.account.cash)}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Buying power</p>
              <p className="font-mono text-sm text-card-foreground">{money(account.account.buying_power)}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Bot status</p>
              <p className={`text-sm font-medium ${config.enabled ? "text-positive" : "text-muted-foreground"}`}>
                {config.enabled ? "Enabled" : "Disabled"}
              </p>
            </div>
          </div>

          {account.positions.length > 0 && (
            <div className="overflow-x-auto rounded-lg border border-border">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-muted">
                  <tr>
                    <th className="px-3 py-2 font-medium text-muted-foreground">Ticker</th>
                    <th className="px-3 py-2 font-medium text-muted-foreground">Shares</th>
                    <th className="px-3 py-2 font-medium text-muted-foreground">Value</th>
                  </tr>
                </thead>
                <tbody>
                  {account.positions.map((p) => (
                    <tr key={p.ticker} className="border-t border-border">
                      <td className="px-3 py-2 font-semibold text-card-foreground">{p.ticker}</td>
                      <td className="px-3 py-2 font-mono text-card-foreground">{p.shares}</td>
                      <td className="px-3 py-2 font-mono text-card-foreground">{money(p.value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      <BotSettingsForm config={config} onSaved={onConfigSaved} />

      <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-6">
        <div className="flex items-center gap-2">
          <ClockCounterClockwise size={18} className="text-accent" aria-hidden="true" />
          <h2 className="font-semibold text-card-foreground">Trade history</h2>
          <button
            onClick={handleRunNow}
            disabled={running || !!alpacaNotConfigured}
            title={alpacaNotConfigured ?? undefined}
            className={`ml-auto flex cursor-pointer items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50 ${FOCUS_RING}`}
          >
            <ArrowsClockwise size={13} className={running ? "animate-spin" : ""} aria-hidden="true" />
            {running ? "Running…" : "Run now"}
          </button>
        </div>

        {runNotice && (
          <p role="status" className="text-sm text-muted-foreground">
            {runNotice}
          </p>
        )}
        {runError && (
          <p role="alert" className="text-sm text-destructive">
            {runError}
          </p>
        )}

        {tradesLoading ? (
          <div className="h-16 animate-pulse rounded-lg bg-muted" />
        ) : trades.length === 0 ? (
          <p className="text-sm text-muted-foreground">No trades yet.</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-muted">
                <tr>
                  <th className="px-3 py-2 font-medium text-muted-foreground">Date</th>
                  <th className="px-3 py-2 font-medium text-muted-foreground">Ticker</th>
                  <th className="px-3 py-2 font-medium text-muted-foreground">Amount</th>
                  <th className="px-3 py-2 font-medium text-muted-foreground">Status</th>
                  <th className="px-3 py-2 font-medium text-muted-foreground">Rationale</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((t) => (
                  <tr key={t.id} className="border-t border-border">
                    <td className="px-3 py-2 text-xs text-muted-foreground">{t.run_date}</td>
                    <td className="px-3 py-2 font-semibold text-card-foreground">{t.ticker}</td>
                    <td className="px-3 py-2 font-mono text-card-foreground">{money(t.notional)}</td>
                    <td className="px-3 py-2">
                      <StatusBadge status={t.status} />
                    </td>
                    <td className="px-3 py-2 text-xs text-muted-foreground">{t.rationale}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <BotNotableActivity />
    </div>
  );
}

function BotNotableActivity() {
  const [congressRows, setCongressRows] = useState<Record<string, unknown>[]>([]);
  const [insiderRows, setInsiderRows] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const dateFrom = new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    Promise.all([
      fetchTrades("congress", "", { limit: 5, dateFrom }).catch(() => ({ rows: [], total: 0 })),
      fetchTrades("insiders", "", { limit: 5, dateFrom }).catch(() => ({ rows: [], total: 0 })),
    ])
      .then(([congress, insiders]) => {
        setCongressRows(congress.rows);
        setInsiderRows(insiders.rows);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading || (congressRows.length === 0 && insiderRows.length === 0)) return null;

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-6">
      <div className="flex items-center gap-2">
        <Info size={18} className="text-muted-foreground" aria-hidden="true" />
        <h2 className="font-semibold text-card-foreground">Notable recent activity</h2>
      </div>
      <p className="text-xs text-muted-foreground">
        For your information only — does not affect the bot&apos;s trades. From the Trade Tracker, last 14 days.
      </p>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Congress</p>
          {congressRows.length === 0 ? (
            <p className="text-xs text-muted-foreground/70">Nothing recent.</p>
          ) : (
            congressRows.map((r, i) => (
              <p key={i} className="truncate text-xs text-card-foreground">
                {String(r.member_name)} · {String(r.ticker ?? "—")}
              </p>
            ))
          )}
        </div>
        <div className="flex flex-col gap-1.5">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Insiders</p>
          {insiderRows.length === 0 ? (
            <p className="text-xs text-muted-foreground/70">Nothing recent.</p>
          ) : (
            insiderRows.map((r, i) => (
              <p key={i} className="truncate text-xs text-card-foreground">
                {String(r.owner_name)} · {String(r.issuer_ticker ?? "—")}
              </p>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
