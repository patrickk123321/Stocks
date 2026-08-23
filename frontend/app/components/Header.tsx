"use client";

import { ChartLineUp, Robot, Wallet } from "@phosphor-icons/react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { key: "trade-tracker", href: "/trade-tracker", label: "Trade Tracker", icon: ChartLineUp },
  { key: "recommendations", href: "/recommendations", label: "Recommendations", icon: Wallet },
  { key: "auto-trader", href: "/auto-trader", label: "Auto-Trading Bot", icon: Robot },
] as const;

export default function Header() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-3">
        <Link
          href="/"
          className="flex items-center gap-2 rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/50"
        >
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent/15 text-accent">
            <ChartLineUp size={16} weight="bold" aria-hidden="true" />
          </span>
          <span className="text-sm font-semibold tracking-tight text-foreground">Stocks</span>
        </Link>

        <nav className="flex items-center gap-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);

            return (
              <Link
                key={item.key}
                href={item.href}
                className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 ${
                  active ? "bg-accent/15 text-accent" : "text-muted-foreground hover:bg-muted hover:text-foreground"
                }`}
              >
                <Icon size={16} weight={active ? "fill" : "regular"} aria-hidden="true" />
                <span className="hidden sm:inline">{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
