"use client";

import { SignInButton, useAuth } from "@clerk/nextjs";
import { Bell, Star, WarningCircle } from "@phosphor-icons/react";
import Link from "next/link";
import { useEffect, useState } from "react";
import WatchlistButton from "../components/WatchlistButton";
import { badge, badgeLabel, badgeTitle, badgeTone } from "../lib/tradeFormat";
import { fetchWatchlist, fetchWatchlistAlerts, markAlertsSeen, WatchlistAlert } from "../lib/api";

export default function WatchlistPage() {
  const { isSignedIn, isLoaded, getToken } = useAuth();
  const [tickers, setTickers] = useState<string[]>([]);
  const [alerts, setAlerts] = useState<WatchlistAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isSignedIn) {
      setLoading(false);
      return;
    }
    setLoading(true);
    Promise.all([fetchWatchlist(getToken), fetchWatchlistAlerts(getToken)])
      .then(([tickerList, alertList]) => {
        setTickers(tickerList);
        setAlerts(alertList);
        markAlertsSeen(getToken)
          .then(() => window.dispatchEvent(new Event("watchlist-alerts-seen")))
          .catch(() => {});
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false));
  }, [isSignedIn, getToken]);

  if (isLoaded && !isSignedIn) {
    return (
      <div className="flex flex-1 flex-col">
        <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col items-center justify-center gap-4 px-6 py-16 text-center">
          <span className="flex h-12 w-12 items-center justify-center rounded-lg bg-muted text-muted-foreground">
            <Star size={22} aria-hidden="true" />
          </span>
          <h1 className="font-display text-2xl font-semibold text-foreground">Sign in to build a watchlist</h1>
          <p className="max-w-sm text-sm leading-relaxed text-muted-foreground">
            Favorite tickers from the trade tracker and get emailed the moment a politician buys one.
          </p>
          <SignInButton>
            <button
              type="button"
              className="cursor-pointer rounded-md bg-accent px-4 py-2 text-sm font-medium text-on-accent transition-[opacity,transform] duration-150 ease-out hover:opacity-90 active:scale-[0.97] focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/70"
            >
              Sign in
            </button>
          </SignInButton>
        </main>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col">
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-6 py-10">
        <div className="flex flex-col gap-1">
          <h1 className="font-display text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">Watchlist</h1>
          <p className="text-sm leading-relaxed text-muted-foreground">
            Favorited tickers, and every alert you&apos;ve been sent when a politician bought one.
          </p>
        </div>

        {error && (
          <div role="alert" className="flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-4 text-sm text-destructive">
            <WarningCircle size={16} aria-hidden="true" />
            {error}
          </div>
        )}

        <section className="flex flex-col gap-3">
          <h2 className="font-semibold text-foreground">Favorited tickers</h2>
          <div className="overflow-hidden rounded-lg border border-border bg-card shadow-sm">
            {loading ? (
              Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className={`flex items-center justify-between gap-4 px-5 py-4 ${i > 0 ? "border-t border-border" : ""}`}>
                  <div className="h-4 w-24 animate-pulse rounded bg-muted" />
                </div>
              ))
            ) : tickers.length === 0 ? (
              <p className="px-5 py-6 text-sm text-muted-foreground">
                No favorites yet — star a ticker from the{" "}
                <Link href="/trade-tracker" className="font-medium text-accent hover:underline">
                  trade tracker
                </Link>{" "}
                to add it here.
              </p>
            ) : (
              tickers.map((ticker, i) => (
                <div key={ticker} className={`flex items-center justify-between gap-4 px-5 py-4 ${i > 0 ? "border-t border-border" : ""}`}>
                  <Link href={`/ticker/${encodeURIComponent(ticker)}`} className="font-mono text-sm font-semibold text-foreground hover:underline">
                    {ticker}
                  </Link>
                  <WatchlistButton ticker={ticker} />
                </div>
              ))
            )}
          </div>
        </section>

        <section className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <Bell size={16} className="text-muted-foreground" aria-hidden="true" />
            <h2 className="font-semibold text-foreground">Recent alerts</h2>
          </div>
          <div className="overflow-hidden rounded-lg border border-border bg-card shadow-sm">
            {loading ? (
              Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className={`flex items-center justify-between gap-4 px-5 py-4 ${i > 0 ? "border-t border-border" : ""}`}>
                  <div className="h-4 w-40 animate-pulse rounded bg-muted" />
                  <div className="h-4 w-24 animate-pulse rounded bg-muted" />
                </div>
              ))
            ) : alerts.length === 0 ? (
              <p className="px-5 py-6 text-sm text-muted-foreground">
                No alerts yet — you&apos;ll be emailed here as soon as a politician buys a favorited ticker.
              </p>
            ) : (
              alerts.map((alert, i) => (
                <div key={i} className={`flex items-center justify-between gap-4 px-5 py-4 ${i > 0 ? "border-t border-border" : ""}`}>
                  <div className="flex min-w-0 items-center gap-3.5">
                    {badge(badgeLabel("transaction_type", "Purchase"), badgeTone("transaction_type", "Purchase"), badgeTitle("transaction_type", "Purchase"))}
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-card-foreground">{alert.member_name}</p>
                      <p className="truncate font-mono text-xs text-muted-foreground">
                        <span className="font-semibold text-foreground">{alert.ticker}</span> · {alert.chamber}
                      </p>
                    </div>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="font-mono text-xs text-card-foreground">{alert.amount_range}</p>
                    <p className="text-xs text-muted-foreground">{alert.transaction_date}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
