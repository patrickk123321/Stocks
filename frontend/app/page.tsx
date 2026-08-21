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
    iconWrap: "bg-accent/15 text-accent",
    hoverBorder: "hover:border-accent/60",
    glow: "group-hover:shadow-[0_0_0_1px_rgba(124,58,237,0.4),0_16px_40px_-12px_rgba(124,58,237,0.35)]",
  },
  {
    key: "recommendations",
    href: "/recommendations",
    icon: Wallet,
    title: "Portfolio Recommendations",
    description: "Stock and ETF suggestions with target allocations, based on your risk profile and current holdings.",
    status: "live" as const,
    iconWrap: "bg-warning/15 text-warning",
    hoverBorder: "hover:border-warning/60",
    glow: "group-hover:shadow-[0_0_0_1px_rgba(251,191,36,0.35),0_16px_40px_-12px_rgba(251,191,36,0.3)]",
  },
  {
    key: "auto-trader",
    href: null,
    icon: Robot,
    title: "Auto-Trading Bot",
    description: "Paper-trades automatically via Alpaca, informed by the tracker and your portfolio preferences.",
    status: "coming-soon" as const,
    iconWrap: "bg-positive/15 text-positive",
    hoverBorder: "hover:border-positive/60",
    glow: "group-hover:shadow-[0_0_0_1px_rgba(52,211,153,0.35),0_16px_40px_-12px_rgba(52,211,153,0.3)]",
  },
];

export default function Home() {
  return (
    <div className="flex flex-1 flex-col overflow-x-clip">
      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-16 px-6 py-16 sm:py-20">
        <section className="relative grid grid-cols-1 items-center gap-10 sm:grid-cols-[1.1fr_0.9fr] sm:gap-6">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute -top-24 left-1/4 h-72 w-72 -translate-x-1/2 rounded-full bg-accent/25 blur-[100px]"
          />
          <div
            aria-hidden="true"
            className="pointer-events-none absolute -top-10 right-0 h-64 w-64 rounded-full bg-positive/15 blur-[100px]"
          />

          <div className="relative flex flex-col items-start gap-5 animate-fade-up">
            <div className="flex items-center gap-2 rounded-full border border-border bg-card/60 py-1.5 pl-2.5 pr-3 text-xs font-medium text-muted-foreground">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-pulse-dot rounded-full bg-positive" />
              </span>
              Trade Tracker refreshes daily at 9:00 AM
            </div>
            <h1 className="text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">Stocks</h1>
            <p className="max-w-md text-base leading-relaxed text-muted-foreground">
              A personal investing platform: track the market&apos;s biggest players, get portfolio guidance, and
              paper-trade automatically.
            </p>
          </div>

          <div className="relative hidden sm:block animate-fade-up" style={{ animationDelay: "100ms" }}>
            <HeroChart />
          </div>
        </section>

        <section className="grid w-full grid-cols-1 gap-5 sm:grid-cols-3">
          {PRODUCTS.map((product, i) => {
            const Icon = product.icon;
            const isLive = product.status === "live";

            const card = (
              <div
                className={`group relative flex h-full flex-col gap-5 overflow-hidden rounded-xl border border-border bg-card p-6 transition-all duration-300 ${
                  isLive ? `cursor-pointer ${product.hoverBorder} ${product.glow} hover:-translate-y-0.5` : "opacity-80"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className={`flex h-11 w-11 items-center justify-center rounded-lg ${product.iconWrap}`}>
                    <Icon size={22} weight="regular" aria-hidden="true" />
                  </div>
                  {isLive ? (
                    <span className="flex items-center gap-1.5 rounded-full bg-positive/15 px-2.5 py-1 text-xs font-medium text-positive">
                      <span className="h-1.5 w-1.5 rounded-full bg-positive" aria-hidden="true" />
                      Live
                    </span>
                  ) : (
                    <span className="flex items-center gap-1.5 rounded-full bg-warning/15 px-2.5 py-1 text-xs font-medium text-warning">
                      <Lock size={12} aria-hidden="true" />
                      Coming soon
                    </span>
                  )}
                </div>
                <div className="flex flex-col gap-1.5">
                  <h2 className="font-semibold text-card-foreground">{product.title}</h2>
                  <p className="text-sm leading-relaxed text-muted-foreground">{product.description}</p>
                </div>
              </div>
            );

            return product.href ? (
              <Link
                key={product.key}
                href={product.href}
                className="animate-fade-up rounded-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                style={{ animationDelay: `${150 + i * 75}ms` }}
              >
                {card}
              </Link>
            ) : (
              <div key={product.key} aria-disabled="true" className="animate-fade-up" style={{ animationDelay: `${150 + i * 75}ms` }}>
                {card}
              </div>
            );
          })}
        </section>
      </main>
    </div>
  );
}

function HeroChart() {
  return (
    <svg
      viewBox="0 0 360 220"
      role="img"
      aria-label="Stylized upward market chart"
      className="w-full text-accent"
    >
      <defs>
        <linearGradient id="hero-line" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="var(--color-accent)" />
          <stop offset="100%" stopColor="var(--color-positive)" />
        </linearGradient>
        <linearGradient id="hero-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--color-accent)" stopOpacity="0.28" />
          <stop offset="100%" stopColor="var(--color-accent)" stopOpacity="0" />
        </linearGradient>
      </defs>

      {[40, 80, 120, 160].map((y) => (
        <line key={y} x1="0" y1={y} x2="360" y2={y} stroke="var(--color-border)" strokeWidth="1" opacity="0.5" />
      ))}

      {[
        { x: 24, o: 150, c: 130, h: 118, l: 158, up: true },
        { x: 56, o: 132, c: 148, h: 148, l: 155, up: false },
        { x: 88, o: 146, c: 100, h: 92, l: 150, up: true },
        { x: 120, o: 102, c: 118, h: 118, l: 108, up: false },
        { x: 184, o: 96, c: 60, h: 52, l: 100, up: true },
        { x: 216, o: 62, c: 76, h: 76, l: 58, up: false },
        { x: 248, o: 78, c: 44, h: 38, l: 82, up: true },
        { x: 280, o: 46, c: 30, h: 24, l: 50, up: true },
      ].map((c, i) => (
        <g key={i}>
          <line x1={c.x} y1={c.h} x2={c.x} y2={c.l} stroke={c.up ? "var(--color-positive)" : "var(--color-destructive)"} strokeWidth="1.5" opacity="0.9" />
          <rect
            x={c.x - 5}
            y={Math.min(c.o, c.c)}
            width="10"
            height={Math.max(Math.abs(c.o - c.c), 2)}
            fill={c.up ? "var(--color-positive)" : "var(--color-destructive)"}
            opacity="0.85"
            rx="1.5"
          />
        </g>
      ))}

      <path
        d="M8,165 C60,150 90,158 130,110 C160,80 190,95 220,68 C250,45 280,50 352,15"
        fill="none"
        stroke="url(#hero-line)"
        strokeWidth="3"
        strokeLinecap="round"
      />
      <path
        d="M8,165 C60,150 90,158 130,110 C160,80 190,95 220,68 C250,45 280,50 352,15 L352,220 L8,220 Z"
        fill="url(#hero-fill)"
        stroke="none"
      />
    </svg>
  );
}
