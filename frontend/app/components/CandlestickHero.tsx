"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useEffect, useRef, useState } from "react";

// "Shoot-up" candlestick hero — plays once per browser tab, then renders
// settled. See DESIGN.md's "one glow exception" note for why the breakout
// candle's flash is allowed here and nowhere else in the app.
const SESSION_KEY = "pelosi_hero_played";
const VIEW_W = 500;
const VIEW_H = 300;
const BASELINE = 280;
const STEP = 0.08;
const CANDLE_WIDTH = 14;

interface CandleData {
  x: number;
  o: number;
  c: number;
  h: number;
  l: number;
}

// Real per-candle up/down direction (green/red), alternating-but-trending,
// ending in one dramatically larger green breakout — not a straight staircase.
// x positions spread across nearly the full viewBox width (30 to 470 of 500, even
// 44px steps) so the chart fills its box edge-to-edge rather than leaving unused
// margin on the right, and better matches a container wider than the old 400-wide
// viewBox (which was letterboxing inside its wider column via preserveAspectRatio).
const CANDLES: CandleData[] = [
  { x: 30, o: 220, c: 200, h: 190, l: 230 }, // up
  { x: 74, o: 205, c: 225, h: 225, l: 235 }, // down (small pullback)
  { x: 118, o: 222, c: 190, h: 180, l: 228 }, // up
  { x: 162, o: 192, c: 165, h: 155, l: 198 }, // up
  { x: 206, o: 168, c: 185, h: 185, l: 192 }, // down (small pullback)
  { x: 250, o: 182, c: 150, h: 140, l: 188 }, // up
  { x: 294, o: 152, c: 170, h: 170, l: 178 }, // down (small pullback)
  { x: 338, o: 168, c: 130, h: 120, l: 174 }, // up
  { x: 382, o: 132, c: 150, h: 150, l: 158 }, // down (small pullback)
  { x: 426, o: 148, c: 100, h: 90, l: 154 }, // up
  { x: 470, o: 102, c: 12, h: 6, l: 108 }, // breakout — reaches almost to the top edge (y=0)
];
const BREAKOUT_INDEX = CANDLES.length - 1;

// Literal hex, matching --color-positive/--color-destructive in globals.css/DESIGN.md.
// Framer Motion doesn't need to interpolate these (colors are static per candle, not
// animated between states), but literals are used anyway for consistency with the rest
// of this file's animated numeric props.
const POSITIVE_HEX = "#0f5c3c";
const DESTRUCTIVE_HEX = "#a32424";

// A trend-line overlay, brought back from the very first version of this chart. Dark
// brown is a deliberate, scoped exception to Ledger tokens (same treatment as the logo
// and the glow — see DESIGN.md) — distinct from both candle colors and the logo's palette.
const TREND_LINE_HEX = "#4a2c17";
const TREND_GRADIENT_ID = "pelosi-trend-fill";
// Starts once the breakout candle's spring has had time to settle, as a calm finishing
// touch after the main sequence rather than drawing on progressively with the candles.
const TREND_LINE_DELAY = BREAKOUT_INDEX * STEP + 0.5;

const isUp = (c: CandleData) => c.c < c.o;
const bodyTop = (c: CandleData) => Math.min(c.o, c.c);
const bodyHeight = (c: CandleData) => Math.max(Math.abs(c.o - c.c), 2);

// Smooth curve through each candle's close price, using the midpoint-quadratic
// technique: each interior point is a control point pulling the curve toward it, with
// the curve itself passing through the midpoint between consecutive points, then a
// final smooth-quadratic segment (T) into the last real point.
function buildTrendPath(points: { x: number; y: number }[]): string {
  if (points.length === 0) return "";
  if (points.length === 1) return `M${points[0].x},${points[0].y}`;
  let d = `M${points[0].x},${points[0].y}`;
  for (let i = 1; i < points.length - 1; i++) {
    const midX = (points[i].x + points[i + 1].x) / 2;
    const midY = (points[i].y + points[i + 1].y) / 2;
    d += ` Q${points[i].x},${points[i].y} ${midX},${midY}`;
  }
  const last = points[points.length - 1];
  d += ` T${last.x},${last.y}`;
  return d;
}

export default function CandlestickHero() {
  const prefersReducedMotion = useReducedMotion();
  const [mounted, setMounted] = useState(false);
  const [shouldAnimate, setShouldAnimate] = useState(false);
  // React (Next.js App Router) runs Strict Mode in dev, which double-invokes effects.
  // Without this guard, the second invocation reads back the sessionStorage write the
  // first invocation just made, concludes "already played," and the animation never
  // gets a chance to run — this ref makes the second invocation a no-op.
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
      // Storage unavailable (e.g. private browsing) — fail open and play the animation.
      playedAlready = false;
    }
    setShouldAnimate(!playedAlready && !prefersReducedMotion);
    setMounted(true);
  }, [prefersReducedMotion]);

  const closePoints = CANDLES.map((c) => ({ x: c.x, y: c.c }));
  const trendLinePath = buildTrendPath(closePoints);
  const trendFillPath = `${trendLinePath} L${closePoints[closePoints.length - 1].x},${BASELINE} L${closePoints[0].x},${BASELINE} Z`;

  return (
    <svg
      viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
      role="img"
      aria-label="Stylized candlestick chart trending upward"
      className="h-full w-full"
      preserveAspectRatio="xMidYMid meet"
    >
      <defs>
        <radialGradient id="pelosi-breakout-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="var(--color-positive)" stopOpacity="0.5" />
          <stop offset="100%" stopColor="var(--color-positive)" stopOpacity="0" />
        </radialGradient>
        <linearGradient id={TREND_GRADIENT_ID} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={TREND_LINE_HEX} stopOpacity="0.3" />
          <stop offset="100%" stopColor={TREND_LINE_HEX} stopOpacity="0" />
        </linearGradient>
      </defs>

      {[60, 120, 180, 240].map((y) => (
        <line key={y} x1="0" y1={y} x2={VIEW_W} y2={y} stroke="var(--color-border)" strokeWidth="1" opacity="0.5" />
      ))}

      {mounted &&
        CANDLES.map((candle, i) => {
          const isBreakout = i === BREAKOUT_INDEX;
          const delay = i * STEP;
          const top = bodyTop(candle);
          const height = bodyHeight(candle);
          const color = isUp(candle) ? POSITIVE_HEX : DESTRUCTIVE_HEX;
          const transition = isBreakout
            ? { type: "spring" as const, stiffness: 400, damping: 10, delay }
            : { duration: 0.3, ease: "easeOut" as const, delay };

          return (
            <g key={candle.x}>
              {isBreakout && shouldAnimate && (
                <motion.circle
                  cx={candle.x}
                  cy={top + height / 2}
                  fill="url(#pelosi-breakout-glow)"
                  initial={{ opacity: 0, r: 8 }}
                  animate={{ opacity: [0, 0.6, 0], r: 40 }}
                  transition={{ duration: 0.4, delay: delay + 0.05, ease: "easeOut" }}
                />
              )}
              <motion.line
                x1={candle.x}
                x2={candle.x}
                stroke={color}
                strokeWidth="2"
                initial={shouldAnimate ? { y1: BASELINE, y2: BASELINE } : false}
                animate={{ y1: candle.h, y2: candle.l }}
                transition={transition}
              />
              <motion.rect
                x={candle.x - CANDLE_WIDTH / 2}
                width={CANDLE_WIDTH}
                fill={color}
                initial={shouldAnimate ? { y: BASELINE, height: 0 } : false}
                animate={{ y: top, height }}
                transition={transition}
              />
            </g>
          );
        })}

      {mounted && (
        <motion.g
          initial={shouldAnimate ? { opacity: 0 } : false}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4, delay: TREND_LINE_DELAY, ease: "easeOut" }}
        >
          <path d={trendFillPath} fill={`url(#${TREND_GRADIENT_ID})`} stroke="none" />
          <path d={trendLinePath} fill="none" stroke={TREND_LINE_HEX} strokeWidth="3" strokeLinecap="round" />
        </motion.g>
      )}
    </svg>
  );
}
