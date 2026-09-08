import { ChartLineUp } from "@phosphor-icons/react/ssr";
import Link from "next/link";
import CandlestickHero from "./components/CandlestickHero";
import LogoIntro from "./components/LogoIntro";

export default function Home() {
  return (
    <div className="flex flex-1 flex-col overflow-x-clip">
      <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-6 py-6 sm:py-8">
        <section className="grid flex-1 grid-cols-1 items-stretch gap-8 sm:grid-cols-[2fr_3fr] sm:gap-10">
          <div className="relative -left-6 flex flex-1 items-stretch gap-4 pt-2 animate-fade-up">
            <LogoIntro>
              <p className="mx-auto max-w-md text-center text-base leading-relaxed text-muted-foreground">
                A personal investing platform: track corporate insiders, institutional investors, and Congress in
                one place.
              </p>

              <div className="flex flex-1 flex-col items-center justify-center gap-8 py-4">
                <div className="flex w-fit items-center gap-2 rounded-md border border-border bg-card py-1.5 pl-2.5 pr-3 text-xs font-medium text-muted-foreground">
                  <span className="relative flex h-2 w-2">
                    <span className="absolute inline-flex h-full w-full animate-pulse-dot rounded-full bg-positive" />
                  </span>
                  Insider trades refresh twice daily at 9:00 AM and 9:00 PM Eastern
                </div>

                <Link
                  href="/trade-tracker"
                  className="w-full max-w-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                >
                  <div className="flex h-full cursor-pointer flex-col items-center gap-4 rounded-xl border border-border bg-card p-7 text-center shadow-sm transition-[border-color,box-shadow] duration-150 ease-out hover:border-accent hover:shadow-md">
                    <div className="flex h-11 w-11 items-center justify-center rounded-md border border-border-strong text-accent">
                      <ChartLineUp size={22} weight="regular" aria-hidden="true" />
                    </div>
                    <div className="flex flex-col gap-1.5">
                      <h2 className="font-semibold text-card-foreground">Trades</h2>
                      <p className="text-sm leading-relaxed text-muted-foreground">
                        Corporate insider trades, institutional 13F filings, and congressional trades in one place.
                      </p>
                    </div>
                  </div>
                </Link>
              </div>
            </LogoIntro>
          </div>

          <div className="relative min-h-[320px] w-full">
            <CandlestickHero />
          </div>
        </section>
      </main>
    </div>
  );
}
