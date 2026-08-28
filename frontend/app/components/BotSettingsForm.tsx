"use client";

import { useState } from "react";
import { BotConfig, saveBotConfig } from "../lib/botApi";

const FOCUS_RING = "focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/50";

interface BotSettingsFormProps {
  config: BotConfig;
  onSaved: () => void;
}

export default function BotSettingsForm({ config, onSaved }: BotSettingsFormProps) {
  const [enabled, setEnabled] = useState(config.enabled);
  const [maxTradesPerDay, setMaxTradesPerDay] = useState(config.max_trades_per_day);
  const [cashBufferPct, setCashBufferPct] = useState(config.cash_buffer_pct);
  const [standardTradePct, setStandardTradePct] = useState(config.standard_trade_pct);
  const [highConvictionTradePct, setHighConvictionTradePct] = useState(config.high_conviction_trade_pct);
  const [positionCapPct, setPositionCapPct] = useState(config.position_cap_pct);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      await saveBotConfig({
        enabled,
        max_trades_per_day: maxTradesPerDay,
        cash_buffer_pct: cashBufferPct,
        standard_trade_pct: standardTradePct,
        high_conviction_trade_pct: highConvictionTradePct,
        position_cap_pct: positionCapPct,
      });
      onSaved();
    } catch {
      setError("Couldn't save these settings — try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col gap-4 rounded-xl border border-border bg-card p-6">
      <div className="flex items-center justify-between">
        <div className="flex flex-col gap-1">
          <h2 className="text-lg font-semibold text-card-foreground">Bot settings</h2>
          <p className="text-sm text-muted-foreground">
            Buys underweight targets and strong insider/congress signals; sells to enforce the position cap, exit a
            broken thesis, or trim an overweight allocation. Off by default.
          </p>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={enabled}
          onClick={() => setEnabled((e) => !e)}
          className={`relative h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors ${FOCUS_RING} ${
            enabled ? "bg-positive" : "bg-muted"
          }`}
        >
          <span
            className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${
              enabled ? "translate-x-5" : "translate-x-0.5"
            }`}
          />
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium text-card-foreground">Standard trade size (%)</span>
          <input
            type="number"
            min="1"
            max="100"
            step="1"
            value={standardTradePct}
            onChange={(e) => setStandardTradePct(Number(e.target.value))}
            className={`rounded-lg border border-border bg-card px-3 py-2 font-mono text-sm text-card-foreground outline-none focus:border-accent ${FOCUS_RING}`}
          />
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium text-card-foreground">High-conviction trade size (%)</span>
          <input
            type="number"
            min="1"
            max="100"
            step="1"
            value={highConvictionTradePct}
            onChange={(e) => setHighConvictionTradePct(Number(e.target.value))}
            className={`rounded-lg border border-border bg-card px-3 py-2 font-mono text-sm text-card-foreground outline-none focus:border-accent ${FOCUS_RING}`}
          />
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium text-card-foreground">Position cap (%)</span>
          <input
            type="number"
            min="1"
            max="100"
            step="1"
            value={positionCapPct}
            onChange={(e) => setPositionCapPct(Number(e.target.value))}
            className={`rounded-lg border border-border bg-card px-3 py-2 font-mono text-sm text-card-foreground outline-none focus:border-accent ${FOCUS_RING}`}
          />
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium text-card-foreground">Max trades / day</span>
          <input
            type="number"
            min="1"
            max="20"
            step="1"
            value={maxTradesPerDay}
            onChange={(e) => setMaxTradesPerDay(Number(e.target.value))}
            className={`rounded-lg border border-border bg-card px-3 py-2 font-mono text-sm text-card-foreground outline-none focus:border-accent ${FOCUS_RING}`}
          />
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium text-card-foreground">Cash buffer (%)</span>
          <input
            type="number"
            min="0"
            max="100"
            step="1"
            value={cashBufferPct}
            onChange={(e) => setCashBufferPct(Number(e.target.value))}
            className={`rounded-lg border border-border bg-card px-3 py-2 font-mono text-sm text-card-foreground outline-none focus:border-accent ${FOCUS_RING}`}
          />
        </label>
      </div>
      <p className="text-xs text-muted-foreground">
        Standard/high-conviction trade size is a % of buying power (high-conviction applies to a stock with 5+
        distinct insiders/congress members buying). Position cap is the max % of the portfolio any one stock can
        reach before the bot trims it. Cash buffer is never invested — a floor the bot won&apos;t spend past.
      </p>

      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}

      <button
        onClick={handleSave}
        disabled={saving}
        className={`self-start cursor-pointer rounded-lg bg-accent px-5 py-2.5 text-sm font-medium text-on-accent transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50 ${FOCUS_RING}`}
      >
        {saving ? "Saving…" : "Save settings"}
      </button>
    </div>
  );
}
