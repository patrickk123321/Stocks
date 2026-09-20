"use client";

import { useAuth } from "@clerk/nextjs";
import { Star } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { addToWatchlist, fetchWatchlist, GetToken, removeFromWatchlist } from "../lib/api";

// Module-level cache so every star on a page (many rows can share a ticker
// across a paginated trade list) reflects the same watchlist state without
// each button independently re-fetching the full list.
let cachedTickers: Set<string> | null = null;
let cacheLoad: Promise<Set<string>> | null = null;

function loadTickers(getToken: GetToken): Promise<Set<string>> {
  if (cachedTickers) return Promise.resolve(cachedTickers);
  if (!cacheLoad) {
    cacheLoad = fetchWatchlist(getToken).then((tickers) => {
      cachedTickers = new Set(tickers);
      return cachedTickers;
    });
  }
  return cacheLoad;
}

export default function WatchlistButton({ ticker, size = 16 }: { ticker: string; size?: number }) {
  const { isSignedIn, getToken } = useAuth();
  const [watching, setWatching] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!isSignedIn) return;
    let cancelled = false;
    loadTickers(getToken).then((tickers) => {
      if (!cancelled) setWatching(tickers.has(ticker));
    });
    return () => {
      cancelled = true;
    };
  }, [isSignedIn, ticker, getToken]);

  if (!isSignedIn) return null;

  const toggle = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (busy) return;
    setBusy(true);
    try {
      if (watching) {
        await removeFromWatchlist(ticker, getToken);
        cachedTickers?.delete(ticker);
      } else {
        await addToWatchlist(ticker, getToken);
        cachedTickers?.add(ticker);
      }
      setWatching((prev) => !prev);
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      type="button"
      onClick={toggle}
      disabled={busy}
      aria-pressed={watching}
      aria-label={watching ? `Remove ${ticker} from watchlist` : `Add ${ticker} to watchlist`}
      title={watching ? `Remove ${ticker} from watchlist` : `Add ${ticker} to watchlist`}
      className="-m-1.5 flex h-7 w-7 shrink-0 items-center justify-center text-muted-foreground transition-[color,transform] duration-150 ease-out hover:text-accent active:scale-[0.97] disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/70"
    >
      <Star size={size} weight={watching ? "fill" : "regular"} className={watching ? "text-accent" : ""} aria-hidden="true" />
    </button>
  );
}
