"use client";

import { WarningCircle } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import BotDashboardView from "../components/BotDashboardView";
import { AlpacaNotConfiguredError, BotAccountInfo, BotConfig, getBotAccount, getBotConfig, isBackendUnreachable } from "../lib/botApi";

type LoadState = "loading" | "ready" | "error";

export default function AutoTraderPage() {
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [config, setConfig] = useState<BotConfig | null>(null);
  const [account, setAccount] = useState<BotAccountInfo | null>(null);
  const [alpacaNotConfigured, setAlpacaNotConfigured] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadEverything = async () => {
    setLoadState("loading");
    setError(null);
    setAlpacaNotConfigured(null);
    try {
      const configResult = await getBotConfig();
      setConfig(configResult);
      try {
        const accountResult = await getBotAccount();
        setAccount(accountResult);
      } catch (err) {
        if (err instanceof AlpacaNotConfiguredError) {
          setAlpacaNotConfigured(err.message);
          setAccount(null);
        } else {
          throw err;
        }
      }
      setLoadState("ready");
    } catch (err) {
      setError(isBackendUnreachable(err) ? (err as Error).message : "Something went wrong loading the trading bot.");
      setLoadState("error");
    }
  };

  useEffect(() => {
    loadEverything();
  }, []);

  return (
    <div className="flex flex-1 flex-col">
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-6 py-10">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">Auto-Trading Bot</h1>
          <p className="text-sm leading-relaxed text-muted-foreground">
            Paper-trades toward your target allocation via Alpaca — buy-only, guardrailed, off by default.
          </p>
        </div>

        {loadState === "loading" && (
          <div className="flex flex-col gap-3">
            <div className="h-32 animate-pulse rounded-xl bg-muted" />
            <div className="h-32 animate-pulse rounded-xl bg-muted" />
          </div>
        )}

        {loadState === "error" && (
          <div className="flex items-center gap-2 rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            <WarningCircle size={18} aria-hidden="true" />
            <span>{error}</span>
          </div>
        )}

        {loadState === "ready" && config && (
          <BotDashboardView config={config} account={account} alpacaNotConfigured={alpacaNotConfigured} onConfigSaved={loadEverything} />
        )}
      </main>
    </div>
  );
}
