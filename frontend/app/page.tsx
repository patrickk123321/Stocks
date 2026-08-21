import { ChartLineUp, Lock, Robot, Wallet } from "@phosphor-icons/react/ssr";
import Link from "next/link";

const PRODUCTS = [
  {
    key: "trade-tracker",
    href: "/trade-tracker",
    icon: ChartLineUp,
    title: "Trade Tracker",
    description: "Corporate insider trades, institutional 13F filings, and congressional trades in one place.",
    status: "live" as const,
  },
  {
    key: "recommendations",
    href: null,
    icon: Wallet,
    title: "Portfolio Recommendations",
    description: "Stock and ETF suggestions with target allocations, based on your risk profile and current holdings.",
    status: "coming-soon" as const,
  },
  {
    key: "auto-trader",
    href: null,
    icon: Robot,
    title: "Auto-Trading Bot",
    description: "Paper-trades automatically via Alpaca, informed by the tracker and your portfolio preferences.",
    status: "coming-soon" as const,
  },
];

export default function Home() {
  return (
    <div className="flex flex-1 flex-col">
      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col items-center justify-center gap-12 px-6 py-16">
        <div className="flex flex-col items-center gap-3 text-center">
          <h1 className="text-3xl font-semibold text-foreground sm:text-4xl">Stocks</h1>
          <p className="max-w-md text-muted-foreground">
            A personal investing platform: track the market&apos;s biggest players, get portfolio guidance, and
            paper-trade automatically.
          </p>
        </div>

        <div className="grid w-full grid-cols-1 gap-5 sm:grid-cols-3">
          {PRODUCTS.map((product) => {
            const Icon = product.icon;
            const isLive = product.status === "live";

            const card = (
              <div
                className={`group flex h-full flex-col gap-4 rounded-xl border border-border bg-card p-6 transition-colors ${
                  isLive ? "cursor-pointer hover:border-accent" : "opacity-70"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-muted text-accent">
                    <Icon size={22} weight="regular" aria-hidden="true" />
                  </div>
                  {!isLive && (
                    <span className="flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1 text-xs font-medium text-muted-foreground">
                      <Lock size={12} aria-hidden="true" />
                      Coming soon
                    </span>
                  )}
                </div>
                <div className="flex flex-col gap-1.5">
                  <h2 className="font-medium text-card-foreground">{product.title}</h2>
                  <p className="text-sm leading-relaxed text-muted-foreground">{product.description}</p>
                </div>
              </div>
            );

            return product.href ? (
              <Link key={product.key} href={product.href} className="focus:outline-none focus-visible:ring-2 focus-visible:ring-accent rounded-xl">
                {card}
              </Link>
            ) : (
              <div key={product.key} aria-disabled="true">
                {card}
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
}
