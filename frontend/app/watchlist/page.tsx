"use client";

import { SignInButton, useAuth } from "@clerk/nextjs";
import { Bank, Bell, Buildings, MagnifyingGlass, Star, WarningCircle, X } from "@phosphor-icons/react";
import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ActorType,
  addToWatchlist,
  addWatchlistActor,
  fetchWatchlist,
  fetchWatchlistActors,
  fetchWatchlistAlerts,
  markAlertsSeen,
  removeFromWatchlist,
  removeWatchlistActor,
  searchActors,
  searchTickers,
  WatchlistActor,
  WatchlistAlert,
} from "../lib/api";
import { badge, badgeLabel, badgeTitle, badgeTone, formatMeta } from "../lib/tradeFormat";

type Tab = "stocks" | "people";

interface ActorSearchResult {
  actor_type: ActorType;
  actor_name: string;
}

const ACTOR_TYPE_LABEL: Record<ActorType, string> = {
  congress: "Congress",
  institution: "Institution",
};

// Debounces the raw input value so search-as-you-type doesn't fire a
// request per keystroke.
function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}

export default function WatchlistPage() {
  const { isSignedIn, isLoaded, getToken } = useAuth();
  const [tab, setTab] = useState<Tab>("stocks");
  const [tickers, setTickers] = useState<string[]>([]);
  const [actors, setActors] = useState<WatchlistActor[]>([]);
  const [alerts, setAlerts] = useState<WatchlistAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [tickerQuery, setTickerQuery] = useState("");
  const debouncedTickerQuery = useDebouncedValue(tickerQuery, 250);
  const [tickerResults, setTickerResults] = useState<string[]>([]);

  const [actorQuery, setActorQuery] = useState("");
  const debouncedActorQuery = useDebouncedValue(actorQuery, 250);
  const [actorResults, setActorResults] = useState<ActorSearchResult[]>([]);

  useEffect(() => {
    if (!isSignedIn) {
      setLoading(false);
      return;
    }
    setLoading(true);
    Promise.all([fetchWatchlist(getToken), fetchWatchlistActors(getToken), fetchWatchlistAlerts(getToken)])
      .then(([tickerList, actorList, alertList]) => {
        setTickers(tickerList);
        setActors(actorList);
        setAlerts(alertList);
        markAlertsSeen(getToken)
          .then(() => window.dispatchEvent(new Event("watchlist-alerts-seen")))
          .catch(() => {});
      })
      .catch(() => setError("Couldn't load your watchlist. Try reloading the page."))
      .finally(() => setLoading(false));
  }, [isSignedIn, getToken]);

  useEffect(() => {
    if (!debouncedTickerQuery.trim()) {
      setTickerResults([]);
      return;
    }
    let cancelled = false;
    searchTickers(debouncedTickerQuery)
      .then((results) => {
        if (!cancelled) setTickerResults(results);
      })
      .catch(() => {
        if (!cancelled) setTickerResults([]);
      });
    return () => {
      cancelled = true;
    };
  }, [debouncedTickerQuery]);

  useEffect(() => {
    if (!debouncedActorQuery.trim()) {
      setActorResults([]);
      return;
    }
    let cancelled = false;
    Promise.all([searchActors("congress", debouncedActorQuery), searchActors("institution", debouncedActorQuery)])
      .then(([congressNames, institutionNames]) => {
        if (cancelled) return;
        setActorResults([
          ...congressNames.map((name) => ({ actor_type: "congress" as const, actor_name: name })),
          ...institutionNames.map((name) => ({ actor_type: "institution" as const, actor_name: name })),
        ]);
      })
      .catch(() => {
        if (!cancelled) setActorResults([]);
      });
    return () => {
      cancelled = true;
    };
  }, [debouncedActorQuery]);

  const handleAddTicker = async (ticker: string) => {
    setTickerQuery("");
    setTickerResults([]);
    const updated = await addToWatchlist(ticker, getToken);
    setTickers(updated);
  };

  const handleRemoveTicker = async (ticker: string) => {
    const updated = await removeFromWatchlist(ticker, getToken);
    setTickers(updated);
  };

  const handleAddActor = async (result: ActorSearchResult) => {
    setActorQuery("");
    setActorResults([]);
    const updated = await addWatchlistActor(result.actor_type, result.actor_name, getToken);
    setActors(updated);
  };

  const handleRemoveActor = async (actor: WatchlistActor) => {
    const updated = await removeWatchlistActor(actor.actor_type, actor.actor_name, getToken);
    setActors(updated);
  };

  if (isLoaded && !isSignedIn) {
    return (
      <div className="flex flex-1 flex-col">
        <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col items-center justify-center gap-4 px-6 py-16 text-center">
          <span className="flex h-12 w-12 items-center justify-center rounded-lg bg-muted text-muted-foreground">
            <Star size={22} aria-hidden="true" />
          </span>
          <h1 className="font-display text-2xl font-semibold text-foreground">Sign in to build a watchlist</h1>
          <p className="max-w-sm text-sm leading-relaxed text-muted-foreground">
            Favorite stocks or follow congress members and institutions, and get notified here the moment they&apos;re active.
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
            Favorite stocks or follow congress members and institutions, and see every alert when they&apos;re active.
          </p>
        </div>

        {error && (
          <div role="alert" className="flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-4 text-sm text-destructive">
            <WarningCircle size={16} aria-hidden="true" />
            {error}
          </div>
        )}

        <div className="flex border-b border-border">
          {([
            { key: "stocks" as const, label: "Stocks" },
            { key: "people" as const, label: "People" },
          ]).map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`cursor-pointer border-b-2 px-4 py-2.5 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/70 ${
                tab === t.key ? "border-accent text-accent" : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {tab === "stocks" ? (
          <section className="flex flex-col gap-3">
            <div className="relative">
              <MagnifyingGlass
                size={16}
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                aria-hidden="true"
              />
              <input
                type="text"
                value={tickerQuery}
                onChange={(e) => setTickerQuery(e.target.value.toUpperCase())}
                placeholder="Search a ticker (e.g. AAPL)"
                className="w-full rounded-md border border-border-strong bg-card py-2.5 pl-10 pr-3 text-sm text-card-foreground placeholder:text-muted-foreground outline-none transition-colors focus:border-accent focus:ring-2 focus:ring-accent/40"
              />
              {tickerResults.length > 0 && (
                <div className="absolute z-10 mt-1 w-full overflow-hidden rounded-md border border-border bg-card shadow-md">
                  {tickerResults.map((ticker) => (
                    <button
                      key={ticker}
                      onClick={() => handleAddTicker(ticker)}
                      className="block w-full cursor-pointer px-3 py-2 text-left font-mono text-sm text-card-foreground hover:bg-muted"
                    >
                      {ticker}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="overflow-hidden rounded-lg border border-border bg-card shadow-sm">
              {loading ? (
                Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className={`flex items-center justify-between gap-4 px-5 py-4 ${i > 0 ? "border-t border-border" : ""}`}>
                    <div className="h-4 w-24 animate-pulse rounded bg-muted" />
                  </div>
                ))
              ) : tickers.length === 0 ? (
                <p className="px-5 py-6 text-sm text-muted-foreground">
                  No favorited stocks yet — search above, or star a ticker from the{" "}
                  <Link href="/trade-tracker" className="font-medium text-accent hover:underline">
                    trade tracker
                  </Link>
                  .
                </p>
              ) : (
                tickers.map((ticker, i) => (
                  <div key={ticker} className={`flex items-center justify-between gap-4 px-5 py-4 ${i > 0 ? "border-t border-border" : ""}`}>
                    <Link href={`/ticker/${encodeURIComponent(ticker)}`} className="font-mono text-sm font-semibold text-foreground hover:underline">
                      {ticker}
                    </Link>
                    <button
                      onClick={() => handleRemoveTicker(ticker)}
                      aria-label={`Remove ${ticker} from watchlist`}
                      title={`Remove ${ticker} from watchlist`}
                      className="-m-1.5 flex h-7 w-7 shrink-0 cursor-pointer items-center justify-center text-muted-foreground transition-colors hover:text-destructive focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/70"
                    >
                      <X size={14} weight="bold" aria-hidden="true" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </section>
        ) : (
          <section className="flex flex-col gap-3">
            <div className="relative">
              <MagnifyingGlass
                size={16}
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                aria-hidden="true"
              />
              <input
                type="text"
                value={actorQuery}
                onChange={(e) => setActorQuery(e.target.value)}
                placeholder="Search a congress member or institution"
                className="w-full rounded-md border border-border-strong bg-card py-2.5 pl-10 pr-3 text-sm text-card-foreground placeholder:text-muted-foreground outline-none transition-colors focus:border-accent focus:ring-2 focus:ring-accent/40"
              />
              {actorResults.length > 0 && (
                <div className="absolute z-10 mt-1 w-full overflow-hidden rounded-md border border-border bg-card shadow-md">
                  {actorResults.map((result) => (
                    <button
                      key={`${result.actor_type}:${result.actor_name}`}
                      onClick={() => handleAddActor(result)}
                      className="flex w-full cursor-pointer items-center justify-between gap-3 px-3 py-2 text-left text-sm text-card-foreground hover:bg-muted"
                    >
                      <span className="truncate">{result.actor_name}</span>
                      <span className="shrink-0 text-xs text-muted-foreground">{ACTOR_TYPE_LABEL[result.actor_type]}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="overflow-hidden rounded-lg border border-border bg-card shadow-sm">
              {loading ? (
                Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className={`flex items-center justify-between gap-4 px-5 py-4 ${i > 0 ? "border-t border-border" : ""}`}>
                    <div className="h-4 w-40 animate-pulse rounded bg-muted" />
                  </div>
                ))
              ) : actors.length === 0 ? (
                <p className="px-5 py-6 text-sm text-muted-foreground">
                  Not following anyone yet — search above, or follow a member/institution from the{" "}
                  <Link href="/trade-tracker" className="font-medium text-accent hover:underline">
                    trade tracker
                  </Link>
                  .
                </p>
              ) : (
                actors.map((actor, i) => (
                  <div
                    key={`${actor.actor_type}:${actor.actor_name}`}
                    className={`flex items-center justify-between gap-4 px-5 py-4 ${i > 0 ? "border-t border-border" : ""}`}
                  >
                    <div className="flex min-w-0 items-center gap-2.5">
                      {actor.actor_type === "congress" ? (
                        <Bank size={16} className="shrink-0 text-positive" aria-hidden="true" />
                      ) : (
                        <Buildings size={16} className="shrink-0 text-info" aria-hidden="true" />
                      )}
                      <span className="truncate text-sm font-semibold text-foreground">{actor.actor_name}</span>
                    </div>
                    <button
                      onClick={() => handleRemoveActor(actor)}
                      aria-label={`Stop following ${actor.actor_name}`}
                      title={`Stop following ${actor.actor_name}`}
                      className="-m-1.5 flex h-7 w-7 shrink-0 cursor-pointer items-center justify-center text-muted-foreground transition-colors hover:text-destructive focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/70"
                    >
                      <X size={14} weight="bold" aria-hidden="true" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </section>
        )}

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
                No alerts yet — they&apos;ll show up here as soon as a favorited stock, congress member, or institution is active.
              </p>
            ) : (
              alerts.map((alert, i) => (
                <div key={i} className={`flex items-center justify-between gap-4 px-5 py-4 ${i > 0 ? "border-t border-border" : ""}`}>
                  {alert.source === "congress" ? (
                    <>
                      <div className="flex min-w-0 items-center gap-3.5">
                        {alert.transaction_type &&
                          badge(
                            badgeLabel("transaction_type", alert.transaction_type),
                            badgeTone("transaction_type", alert.transaction_type),
                            badgeTitle("transaction_type", alert.transaction_type),
                          )}
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
                    </>
                  ) : (
                    <>
                      <div className="flex min-w-0 items-center gap-3.5">
                        <Buildings size={16} className="shrink-0 text-info" aria-hidden="true" />
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold text-card-foreground">{alert.filer_name}</p>
                          <p className="truncate font-mono text-xs text-muted-foreground">{alert.issuer_name ?? alert.cusip}</p>
                        </div>
                      </div>
                      <div className="shrink-0 text-right">
                        <p className="font-mono text-xs text-card-foreground">{formatMeta(alert.value, "currency")}</p>
                        <p className="text-xs text-muted-foreground">{alert.period_of_report}</p>
                      </div>
                    </>
                  )}
                </div>
              ))
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
