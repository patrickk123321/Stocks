"use client";

import { ChartLineUp } from "@phosphor-icons/react";
import { useReducedMotion } from "framer-motion";
import Link from "next/link";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import CandlestickHero from "./components/CandlestickHero";
import LogoIntro, { FLIGHT_DURATION } from "./components/LogoIntro";

// The breakpoint below which the grid stacks to one column (Tailwind's `sm:`) — below
// this, the header and hero already share the page's own left padding directly, so no
// extra alignment offset is needed or wanted.
const ALIGN_BREAKPOINT = 640;

// Single shared session key/mount-gate for the whole hero sequence (rocket, then chart) —
// one sequenced experience now, not two independently-gated animations.
const SESSION_KEY = "tothemoon_hero_played";

export default function Home() {
  const prefersReducedMotion = useReducedMotion();
  const [mounted, setMounted] = useState(false);
  const [shouldAnimate, setShouldAnimate] = useState(false);
  // Guards against React Strict Mode's dev-only double-invocation of effects — without
  // this, the second invocation reads back the sessionStorage write the first invocation
  // just made, concludes "already played," and the animation never gets a chance to run.
  const hasCheckedRef = useRef(false);

  useEffect(() => {
    if (hasCheckedRef.current) return;
    hasCheckedRef.current = true;

    let playedAlready = false;
    try {
      if (typeof window !== "undefined" && window.sessionStorage) {
        playedAlready = window.sessionStorage.getItem(SESSION_KEY) === "1";
        if (!playedAlready) window.sessionStorage.setItem(SESSION_KEY, "1");
      }
    } catch {
      playedAlready = false;
    }
    setShouldAnimate(!playedAlready && !prefersReducedMotion);
    setMounted(true);
  }, [prefersReducedMotion]);

  // The candlestick entrance waits for the rocket's flight to fully settle (hard cut, no
  // overlap) — expressed as a fixed delay on top of its own stagger rather than a second
  // piece of React state, so it can't drift out of sync with LogoIntro's own timing.
  const entranceDelay = shouldAnimate ? FLIGHT_DURATION : 0;

  // Aligns the whole hero (logo, title, description, pill, Trades card, and the
  // candlestick chart together, via one transform on their shared grid) so the "A" of the
  // description paragraph lines up with the "e" of the header's "Home" label. Computed by
  // measuring both elements' real rendered positions rather than a guessed pixel offset —
  // font metrics/kerning make a hand-picked constant unreliable, and this stays correct
  // across viewport widths and font-loading timing without needing to be re-tuned by eye.
  const [heroOffsetX, setHeroOffsetX] = useState(0);
  const heroOffsetXRef = useRef(0);
  const firstLetterRef = useRef<HTMLSpanElement>(null);
  // Same idea, vertically: the on-screen Y of the hero title's text, so CandlestickHero can
  // size its breakout candle to actually reach it (see that component's own conversion of
  // this screen coordinate into its viewBox space).
  const [titleTargetScreenY, setTitleTargetScreenY] = useState<number | null>(null);

  useLayoutEffect(() => {
    function measure() {
      if (window.innerWidth < ALIGN_BREAKPOINT) {
        heroOffsetXRef.current = 0;
        setHeroOffsetX(0);
      } else {
        const homeLabel = document.getElementById("header-home-label");
        const letter = firstLetterRef.current;
        if (homeLabel && letter) {
          const homeRight = homeLabel.getBoundingClientRect().right;
          // Back out any offset already applied so repeated measurements (e.g. on resize)
          // compute a fresh delta from the element's natural, untransformed position.
          const naturalLetterLeft = letter.getBoundingClientRect().left - heroOffsetXRef.current;
          const delta = homeRight - naturalLetterLeft;
          heroOffsetXRef.current = delta;
          setHeroOffsetX(delta);
        }
      }

      const titleText = document.getElementById("hero-title-text");
      if (titleText) {
        const rect = titleText.getBoundingClientRect();
        setTitleTargetScreenY(rect.top + rect.height / 2);
      }
    }

    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
    // Re-run once the title actually exists in the DOM (it's gated behind `mounted`,
    // which flips true after this component's first paint).
  }, [mounted]);

  return (
    <div className="flex flex-1 flex-col overflow-x-clip">
      <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-6 py-6 sm:py-8">
        <section
          className="grid flex-1 grid-cols-1 items-stretch gap-8 sm:grid-cols-[1fr_2fr] sm:gap-10"
          style={{ transform: `translateX(${heroOffsetX}px)` }}
        >
          <div className="relative flex flex-1 flex-col pt-2 animate-fade-up">
            <LogoIntro mounted={mounted} shouldAnimate={shouldAnimate}>
              <p className="mx-auto max-w-md text-center text-base leading-relaxed text-muted-foreground">
                <span ref={firstLetterRef}>A</span> personal investing platform: track corporate insiders,
                institutional investors, and Congress in one place.
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
            <CandlestickHero
              mounted={mounted}
              shouldAnimate={shouldAnimate}
              entranceDelay={entranceDelay}
              titleTargetScreenY={titleTargetScreenY}
            />
          </div>
        </section>
      </main>
    </div>
  );
}
