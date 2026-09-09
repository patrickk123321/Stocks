"use client";

import { motion } from "framer-motion";
import { useLayoutEffect, useMemo, useRef, useState } from "react";

// "Shoot-up" candlestick hero. Session-gating/reduced-motion/mount state now lives in
// page.tsx (shared with LogoIntro.tsx so the two animations run as one sequence) and is
// passed down as props. See DESIGN.md's "one glow exception" note for why the breakout
// candle's flash is allowed here and nowhere else in the app.
const VIEW_H = 300;
const BASELINE = 280;
const STEP = 0.08;

// Default/fallback candle spacing and margin before the container has been measured (also
// what a failed measurement falls back to). The real spacing is derived at runtime from the
// container's actual aspect ratio — see the measurement effect below — so the chart's
// drawing genuinely fills its box instead of relying on a fixed guess.
const DEFAULT_STEP_X = 72;
const MARGIN_X = 48;
const CANDLE_TO_STEP_RATIO = 16 / 72;

// Bounds on how far the viewBox's aspect ratio is allowed to follow the container's real
// aspect ratio. Deriving the viewBox to exactly match the container eliminates
// `preserveAspectRatio` letterboxing by construction; the clamp only engages for genuinely
// extreme container shapes, trading a little letterboxing there for readable candle spacing
// instead of absurdly thin or fat candles.
const MIN_ASPECT = 1.3;
const MAX_ASPECT = 3.2;

interface CandleData {
  x: number;
  o: number;
  c: number;
  h: number;
  l: number;
}

// Real per-candle up/down direction (green/red), alternating-but-trending, ending in one
// dramatically larger green breakout candle. Its high/close default to a fixed near-top
// value (below) but are overridden at runtime — see titleTargetScreenY below — once
// page.tsx has measured exactly where the hero title's text actually sits on screen.
const RAW_CANDLES: Omit<CandleData, "x">[] = [
  { o: 220, c: 200, h: 190, l: 230 }, // up
  { o: 205, c: 225, h: 225, l: 235 }, // down (small pullback)
  { o: 222, c: 190, h: 180, l: 228 }, // up
  { o: 192, c: 165, h: 155, l: 198 }, // up
  { o: 168, c: 185, h: 185, l: 192 }, // down (small pullback)
  { o: 182, c: 150, h: 140, l: 188 }, // up
  { o: 152, c: 170, h: 170, l: 178 }, // down (small pullback)
  { o: 168, c: 130, h: 120, l: 174 }, // up
  { o: 132, c: 150, h: 150, l: 158 }, // down (small pullback)
  { o: 148, c: 100, h: 90, l: 154 }, // up
  { o: 102, c: 4, h: 2, l: 108 }, // breakout — reaches almost to y=0, the very top of the chart
];
const BREAKOUT_INDEX = RAW_CANDLES.length - 1;

// Literal hex, matching --color-positive/--color-destructive in globals.css/DESIGN.md.
const POSITIVE_HEX = "#0f5c3c";
const DESTRUCTIVE_HEX = "#a32424";

// A trend-line overlay. Dark brown is a deliberate, scoped exception to Ledger tokens
// (same treatment as the logo and the glow — see DESIGN.md) — distinct from both candle
// colors and the logo's palette.
const TREND_LINE_HEX = "#4a2c17";
const TREND_GRADIENT_ID = "pelosi-trend-fill";
// Starts once the breakout candle's spring has had time to settle, as a calm finishing
// touch after the main sequence rather than drawing on progressively with the candles.
const TREND_LINE_DELAY_OFFSET = BREAKOUT_INDEX * STEP + 0.5;

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

interface CandlestickHeroProps {
  /** Gates all rendering until page.tsx's client effect resolves session/reduced-motion
   * state, avoiding an SSR-hydration flash. */
  mounted: boolean;
  shouldAnimate: boolean;
  /** Seconds to add on top of every per-candle stagger delay — set by page.tsx to the
   * rocket flight's duration so the whole chart entrance waits for LogoIntro to land
   * (0 when shouldAnimate is false, since the skip case renders instantly regardless). */
  entranceDelay: number;
  /** Screen-space Y (from getBoundingClientRect) of the hero title text's vertical center,
   * measured by page.tsx. Converted below into this chart's own viewBox coordinate space
   * (accounting for preserveAspectRatio letterboxing) so the breakout candle's tip can
   * reach the title's actual on-screen height — the two live in independently-sized flex
   * columns with no other shared coordinate system. Null until measured (SSR, first paint)
   * — falls back to the fixed near-top RAW_CANDLES value in that case. */
  titleTargetScreenY: number | null;
}

export default function CandlestickHero({
  mounted,
  shouldAnimate,
  entranceDelay,
  titleTargetScreenY,
}: CandlestickHeroProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [breakoutTop, setBreakoutTop] = useState<number | null>(null);
  const [dims, setDims] = useState({ stepX: DEFAULT_STEP_X, candleWidth: DEFAULT_STEP_X * CANDLE_TO_STEP_RATIO });

  useLayoutEffect(() => {
    function measure() {
      if (!svgRef.current) return;
      const rect = svgRef.current.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) return;

      // Derive the viewBox's aspect ratio from the container's real rendered box (clamped
      // to a sane range) so `preserveAspectRatio="xMidYMid meet"` produces no letterboxing
      // in the common case — the drawing's own aspect ratio matches the box it's drawn into.
      const rawAspect = rect.width / rect.height;
      const clampedAspect = Math.min(Math.max(rawAspect, MIN_ASPECT), MAX_ASPECT);
      const viewW = VIEW_H * clampedAspect;
      const stepX = (viewW - MARGIN_X * 2) / (RAW_CANDLES.length - 1);
      setDims({ stepX, candleWidth: stepX * CANDLE_TO_STEP_RATIO });

      if (titleTargetScreenY == null) {
        setBreakoutTop(null);
        return;
      }
      const scale = Math.min(rect.width / viewW, rect.height / VIEW_H);
      const renderedHeight = VIEW_H * scale;
      const letterboxTop = rect.top + (rect.height - renderedHeight) / 2;
      const internalY = (titleTargetScreenY - letterboxTop) / scale;
      // Clamp to a sane range within the chart's own box so a measurement taken before
      // layout has settled can't produce a broken (negative or off-chart) candle.
      setBreakoutTop(Math.min(Math.max(internalY, 2), BASELINE - 20));
    }

    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [titleTargetScreenY]);

  const viewW = useMemo(() => MARGIN_X * 2 + dims.stepX * (RAW_CANDLES.length - 1), [dims.stepX]);

  const candlesBase = useMemo(
    () => RAW_CANDLES.map((c, i) => ({ ...c, x: MARGIN_X + i * dims.stepX })),
    [dims.stepX]
  );

  const candles = useMemo(() => {
    if (breakoutTop == null) return candlesBase;
    return candlesBase.map((c, i) =>
      i === BREAKOUT_INDEX ? { ...c, c: breakoutTop, h: Math.max(breakoutTop - 6, 0) } : c
    );
  }, [candlesBase, breakoutTop]);

  const closePoints = candles.map((c) => ({ x: c.x, y: c.c }));
  const trendLinePath = buildTrendPath(closePoints);
  const trendFillPath = `${trendLinePath} L${closePoints[closePoints.length - 1].x},${BASELINE} L${closePoints[0].x},${BASELINE} Z`;

  return (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${viewW} ${VIEW_H}`}
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
        <line key={y} x1="0" y1={y} x2={viewW} y2={y} stroke="var(--color-border)" strokeWidth="1" opacity="0.5" />
      ))}

      {mounted &&
        candles.map((candle, i) => {
          const isBreakout = i === BREAKOUT_INDEX;
          const delay = entranceDelay + i * STEP;
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
                x={candle.x - dims.candleWidth / 2}
                width={dims.candleWidth}
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
          transition={{ duration: 0.4, delay: entranceDelay + TREND_LINE_DELAY_OFFSET, ease: "easeOut" }}
        >
          <path d={trendFillPath} fill={`url(#${TREND_GRADIENT_ID})`} stroke="none" />
          <path d={trendLinePath} fill="none" stroke={TREND_LINE_HEX} strokeWidth="3" strokeLinecap="round" />
        </motion.g>
      )}
    </svg>
  );
}
