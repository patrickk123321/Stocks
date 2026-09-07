import { Bank, Buildings, ChartLineUp, UserCircle } from "@phosphor-icons/react/ssr";
import Link from "next/link";

const PRODUCTS = [
  {
    key: "trade-tracker",
    href: "/trade-tracker",
    icon: ChartLineUp,
    title: "Trade Tracker",
    description: "Corporate insider trades, institutional 13F filings, and congressional trades in one place.",
  },
];

const CATEGORIES = [
  {
    key: "insiders",
    icon: UserCircle,
    colorClass: "text-accent",
    title: "Corporate Insiders",
    description: "SEC Form 4 filings, read directly from EDGAR's structured feed.",
  },
  {
    key: "institutions",
    icon: Buildings,
    colorClass: "text-info",
    title: "Institutions (13F)",
    description: "Quarterly 13F-HR holdings for every tracked institutional filer.",
  },
  {
    key: "congress",
    icon: Bank,
    colorClass: "text-positive",
    title: "Congress",
    description: "House Clerk PDFs and Senate disclosures, House and Senate alike.",
  },
];

export default function Home() {
  return (
    <div className="flex flex-1 flex-col overflow-x-clip">
      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-16 px-6 py-16 sm:py-20">
        <section className="grid grid-cols-1 items-center gap-10 sm:grid-cols-[1.1fr_0.9fr] sm:gap-6">
          <div className="flex flex-col items-start gap-5 animate-fade-up">
            <div className="flex items-center gap-2 border border-border bg-card py-1.5 pl-2.5 pr-3 text-xs font-medium text-muted-foreground">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-pulse-dot rounded-full bg-positive" />
              </span>
              Insider trades refresh twice daily at 9:00 AM and 4:30 PM
            </div>
            <h1 className="text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">Stocks</h1>
            <p className="max-w-md text-base leading-relaxed text-muted-foreground">
              A personal investing platform: track corporate insiders, institutional investors, and Congress in one
              place.
            </p>
          </div>

          <div className="relative hidden sm:block animate-fade-up" style={{ animationDelay: "100ms" }}>
            <HeroChart />
          </div>
        </section>

        <section className="grid w-full grid-cols-1 gap-5 sm:max-w-sm">
          {PRODUCTS.map((product, i) => {
            const Icon = product.icon;

            return (
              <Link
                key={product.key}
                href={product.href}
                className="animate-fade-up focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                style={{ animationDelay: `${150 + i * 75}ms` }}
              >
                <div className="flex h-full cursor-pointer flex-col gap-5 border border-border bg-card p-6 transition-colors hover:border-accent">
                  <div className="flex h-11 w-11 items-center justify-center border border-border-strong text-accent">
                    <Icon size={22} weight="regular" aria-hidden="true" />
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <h2 className="font-semibold text-card-foreground">{product.title}</h2>
                    <p className="text-sm leading-relaxed text-muted-foreground">{product.description}</p>
                  </div>
                </div>
              </Link>
            );
          })}
        </section>

        <section className="flex flex-col gap-5 border-t border-border pt-12">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">What&apos;s tracked</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {CATEGORIES.map((category) => {
              const Icon = category.icon;
              return (
                <div key={category.key} className="flex flex-col gap-3 border border-border bg-card p-5">
                  <div className={`flex h-9 w-9 items-center justify-center border border-border-strong ${category.colorClass}`}>
                    <Icon size={16} weight="regular" aria-hidden="true" />
                  </div>
                  <div className="flex flex-col gap-1">
                    <h3 className="text-sm font-semibold text-card-foreground">{category.title}</h3>
                    <p className="text-xs leading-relaxed text-muted-foreground">{category.description}</p>
                  </div>
                </div>
              );
            })}
          </div>
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
      className="w-full"
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
