"use client";

import { motion } from "framer-motion";
import { ReactNode } from "react";
import PeloSiMark from "./PeloSiMark";

// Homepage-only rocket-flies-in intro, wrapping the plain/static PeloSiMark (which stays
// untouched for its unrelated Header.tsx usage). Session-gating/reduced-motion/mount state
// lives in page.tsx (shared with CandlestickHero.tsx so the two animations run as one
// sequence: rocket first, chart entrance only once this settles) and is passed down as
// props. FLIGHT_DURATION is exported so page.tsx can delay the chart's entrance by exactly
// this amount, rather than guessing a second constant that could drift out of sync.
export const FLIGHT_DURATION = 1.4;
const BUBBLE_DRAW_DURATION = 0.45;
const BUBBLE_STROKE = "#1c2b45";
const BUBBLE_FILL = "var(--color-card)";
const TITLE_COLOR = "var(--color-foreground)";
// The artwork's own baked-in tilt (PeloSiMark.tsx's <g transform="rotate(28 50 50)">,
// untouched). The outer flight animation's rotate ends on this same value at rest — both
// the animated case's final keyframe and the "already played" static case use it, matching
// what's already live.
const REST_ROTATION = 28;

function cubicBezierPoint(p0: number, p1: number, p2: number, p3: number, t: number): number {
  const mt = 1 - t;
  return mt * mt * mt * p0 + 3 * mt * mt * t * p1 + 3 * mt * t * t * p2 + t * t * t * p3;
}

// A true single S-curve (one bend right, one bend left, then settle) from off-screen
// bottom-left to the rocket's resting spot, sampled densely from a cubic bezier so Framer
// Motion's between-point interpolation reads as one continuous flowing motion rather than
// a handful of disconnected keyframes snapping between sharp direction reversals.
const FLIGHT_START = { x: -260, y: 240 };
const FLIGHT_CONTROL_1 = { x: -30, y: 150 };
const FLIGHT_CONTROL_2 = { x: -190, y: 55 };
const FLIGHT_END = { x: 0, y: 0 };
const FLIGHT_SAMPLES = 11;

const FLIGHT_TIMES = Array.from({ length: FLIGHT_SAMPLES }, (_, i) => i / (FLIGHT_SAMPLES - 1));
const FLIGHT_POINTS = FLIGHT_TIMES.map((t) => ({
  x: cubicBezierPoint(FLIGHT_START.x, FLIGHT_CONTROL_1.x, FLIGHT_CONTROL_2.x, FLIGHT_END.x, t),
  y: cubicBezierPoint(FLIGHT_START.y, FLIGHT_CONTROL_1.y, FLIGHT_CONTROL_2.y, FLIGHT_END.y, t),
}));
const FLIGHT_X = FLIGHT_POINTS.map((p) => p.x);
const FLIGHT_Y = FLIGHT_POINTS.map((p) => p.y);
// Rotation follows the curve's own tangent direction (derived from consecutive sampled
// points) so it naturally banks into each bend of the S, rather than a hand-picked array
// of angles that don't correspond to the actual path — only the final frame is a manual
// override, settling on the artwork's resting tilt once the rocket has actually arrived.
const FLIGHT_ROTATE = FLIGHT_POINTS.map((p, i) => {
  if (i === FLIGHT_POINTS.length - 1) return REST_ROTATION;
  const next = FLIGHT_POINTS[i + 1];
  return (Math.atan2(next.y - p.y, next.x - p.x) * 180) / Math.PI + 90;
});

// Trailing smoke puffs sampled along the same flight path (every other point, skipping the
// final resting frame) — bigger, more opaque, and each its own grey shade so the trail
// reads as visibly billowy rather than one flat repeated dot.
const SMOKE_INDICES = [0, 2, 4, 6, 8];
const SMOKE_COLORS = ["#c9c9c4", "#9a9a95", "#dcdcd6", "#b0b0ab", "#c9c9c4"];
const SMOKE_PUFFS = SMOKE_INDICES.map((idx, i) => ({
  x: FLIGHT_POINTS[idx].x,
  y: FLIGHT_POINTS[idx].y,
  color: SMOKE_COLORS[i],
  delay: FLIGHT_TIMES[idx] * FLIGHT_DURATION,
}));

interface LogoIntroProps {
  mounted: boolean;
  shouldAnimate: boolean;
  /** The rest of the left column (description, status pill, Trades card) — rendered
   * immediately, never gated behind this animation. */
  children: ReactNode;
}

export default function LogoIntro({ mounted, shouldAnimate, children }: LogoIntroProps) {
  return (
    <>
      {/* Normal flex-flow sibling of the title (matching the live/shipped layout) — the
          horizontal alignment of the whole hero against Header's "Home" is handled by
          page.tsx measuring real rendered positions and shifting the entire row, so this
          doesn't need to be pulled out of flow to avoid pushing the title rightward. */}
      <div className="relative -ml-2 shrink-0 self-start" style={{ width: 160, height: 160 }}>
        {mounted &&
          shouldAnimate &&
          SMOKE_PUFFS.map((puff, i) => (
            <motion.div
              key={i}
              className="absolute rounded-full"
              style={{ width: 20, height: 20, top: 70, left: 70, background: puff.color }}
              initial={{ x: puff.x, y: puff.y, opacity: 0, scale: 0.6 }}
              animate={{ opacity: [0, 0.9, 0], scale: [0.6, 1.4, 1.9], x: puff.x + 22, y: puff.y - 18 }}
              transition={{ duration: 0.75, delay: puff.delay, ease: "easeOut" }}
            />
          ))}

        {mounted && (
          <motion.div
            initial={shouldAnimate ? { x: FLIGHT_X[0], y: FLIGHT_Y[0], rotate: FLIGHT_ROTATE[0] } : false}
            animate={
              shouldAnimate
                ? { x: FLIGHT_X, y: FLIGHT_Y, rotate: FLIGHT_ROTATE }
                : { x: 0, y: 0, rotate: REST_ROTATION }
            }
            transition={
              shouldAnimate
                ? { duration: FLIGHT_DURATION, times: FLIGHT_TIMES, ease: "easeInOut" }
                : { duration: 0 }
            }
          >
            <PeloSiMark size={160} />
          </motion.div>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-6">
        <div className="flex h-28 items-center justify-center sm:justify-start">
          {mounted && <TitleBubble shouldAnimate={shouldAnimate} startDelay={shouldAnimate ? FLIGHT_DURATION : 0} />}
        </div>
        {children}
      </div>
    </>
  );
}

function TitleBubble({ shouldAnimate, startDelay }: { shouldAnimate: boolean; startDelay: number }) {
  return (
    <svg width={260} height={110} viewBox="-20 0 260 110" role="img" aria-label="ToTheMoon!">
      <motion.rect
        x={14}
        y={8}
        width={212}
        height={58}
        rx={18}
        fill={BUBBLE_FILL}
        stroke="none"
        initial={shouldAnimate ? { opacity: 0 } : false}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.15, delay: startDelay + BUBBLE_DRAW_DURATION * 0.7 }}
      />

      {/* Classic comic "thought trail" — three circles of decreasing size cascading down
          and to the left from the bubble's bottom-left corner, per the reference image. */}
      {[
        { cx: 6, cy: 76, r: 7 },
        { cx: -6, cy: 88, r: 5 },
        { cx: -16, cy: 98, r: 3 },
      ].map((dot, i) => (
        <motion.circle
          key={i}
          cx={dot.cx}
          cy={dot.cy}
          r={dot.r}
          fill={BUBBLE_FILL}
          stroke={BUBBLE_STROKE}
          strokeWidth={2}
          initial={shouldAnimate ? { opacity: 0, scale: 0.5 } : false}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.15, delay: startDelay + BUBBLE_DRAW_DURATION * 0.85 + i * 0.06 }}
        />
      ))}

      <motion.rect
        x={14}
        y={8}
        width={212}
        height={58}
        rx={18}
        fill="none"
        stroke={BUBBLE_STROKE}
        strokeWidth={2.5}
        pathLength={1}
        strokeDasharray={1}
        initial={shouldAnimate ? { strokeDashoffset: 1 } : false}
        animate={{ strokeDashoffset: 0 }}
        transition={{ duration: BUBBLE_DRAW_DURATION, delay: startDelay, ease: "easeInOut" }}
      />

      {/* Body font (no font-display), matching the description/pill/card text below. `id`
          lets page.tsx measure its real on-screen position for the breakout candle's
          height target — see CandlestickHero.tsx. */}
      <motion.text
        id="hero-title-text"
        x={120}
        y={40}
        textAnchor="middle"
        dominantBaseline="middle"
        fontSize={26}
        fontWeight={600}
        fill={TITLE_COLOR}
        initial={shouldAnimate ? { opacity: 0, scale: 0.9 } : false}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.25, delay: startDelay + BUBBLE_DRAW_DURATION * 0.8 }}
      >
        ToTheMoon!
      </motion.text>
    </svg>
  );
}
