"use client";

import { SignInButton, SignUpButton, Show, UserButton, useAuth } from "@clerk/nextjs";
import { ChartLineUp, Star } from "@phosphor-icons/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { fetchUnreadAlertCount } from "../lib/api";
import PeloSiMark from "./PeloSiMark";

const NAV_ITEMS = [
  { key: "trade-tracker", href: "/trade-tracker", label: "Trades", icon: ChartLineUp },
  { key: "watchlist", href: "/watchlist", label: "Watchlist", icon: Star },
] as const;

export default function Header() {
  const pathname = usePathname();
  const { isSignedIn, getToken } = useAuth();
  const [unreadAlerts, setUnreadAlerts] = useState(0);

  useEffect(() => {
    if (!isSignedIn) {
      setUnreadAlerts(0);
      return;
    }
    let cancelled = false;
    fetchUnreadAlertCount(getToken)
      .then((count) => {
        if (!cancelled) setUnreadAlerts(count);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
    // Re-fetch on every route change, since a new alert can arrive while the
    // user is browsing elsewhere on the site.
  }, [isSignedIn, getToken, pathname]);

  useEffect(() => {
    // The /watchlist page dispatches this right after marking alerts seen,
    // so the badge clears immediately instead of waiting for a route change.
    const onSeen = () => setUnreadAlerts(0);
    window.addEventListener("watchlist-alerts-seen", onSeen);
    return () => window.removeEventListener("watchlist-alerts-seen", onSeen);
  }, []);

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background">
      {/* pl-36/pr-6 matches page.tsx's homepage <main> exactly (not just its max-width) — the
          homepage's heroOffsetX measurement computes a transform from the gap between this
          "Home" label and the hero's own content, so if the two containers' padding ever
          diverges, that transform would shift the whole hero to compensate, undoing whatever
          padding change was made there. Keep these in sync. */}
      <div className="mx-auto flex w-full max-w-[96rem] items-center justify-between pl-36 pr-6 py-3">
        <Link
          href="/"
          className="flex items-center gap-2 transition-transform duration-150 ease-out active:scale-[0.97] focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/70"
        >
          <span className="flex h-7 w-7 items-center justify-center rounded-md border border-border-strong">
            <PeloSiMark size={16} />
          </span>
          <span id="header-home-label" className="text-sm font-semibold tracking-tight text-foreground">
            Home
          </span>
        </Link>

        <nav className="flex items-center gap-3">
          <div className="flex items-center gap-1">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href || pathname.startsWith(`${item.href}/`);

              return (
                <Link
                  key={item.key}
                  href={item.href}
                  className={`flex items-center gap-2 border-b-2 px-3 py-2 text-sm font-medium transition-[color,border-color,transform] duration-150 ease-out active:scale-[0.97] focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/70 ${
                    active ? "border-accent text-accent" : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <span className="relative flex items-center">
                    <Icon size={16} weight={active ? "fill" : "regular"} aria-hidden="true" />
                    {item.key === "watchlist" && unreadAlerts > 0 && (
                      <span
                        className="absolute -right-0.5 -top-0.5 h-1.5 w-1.5 rounded-full bg-accent"
                        aria-hidden="true"
                      />
                    )}
                  </span>
                  <span className="hidden sm:inline">
                    {item.label}
                    {item.key === "watchlist" && unreadAlerts > 0 && (
                      <span className="sr-only"> ({unreadAlerts} unread alert{unreadAlerts !== 1 ? "s" : ""})</span>
                    )}
                  </span>
                </Link>
              );
            })}
          </div>

          <div className="flex items-center gap-2 border-l border-border pl-3">
            <Show when="signed-out">
              <SignInButton>
                <button
                  type="button"
                  className={`cursor-pointer rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/70`}
                >
                  Sign in
                </button>
              </SignInButton>
              <SignUpButton>
                <button
                  type="button"
                  className={`cursor-pointer rounded-md bg-accent px-3 py-2 text-sm font-medium text-on-accent transition-[opacity,transform] duration-150 ease-out hover:opacity-90 active:scale-[0.97] focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/70`}
                >
                  Sign up
                </button>
              </SignUpButton>
            </Show>
            <Show when="signed-in">
              <UserButton appearance={{ elements: { avatarBox: "h-7 w-7" } }} />
            </Show>
          </div>
        </nav>
      </div>
    </header>
  );
}
