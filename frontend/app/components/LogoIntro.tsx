"use client";

import { motion } from "framer-motion";
import { ReactNode, useMemo } from "react";
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
// Fallback used only before page.tsx's runtime viewport measurement resolves (SSR/first
// paint) — in practice replaced by a real measurement before the flight ever plays, the
// same guarantee titleTargetScreenY relies on elsewhere in this sequence.
const FALLBACK_FLIGHT_ORIGIN = { x: -260, y: 240 };

// Where the rocket's resting box (#hero-rocket-rest, sized ROCKET_BOX below) needs to sit so
// the FIGURE'S HEAD — not the box — lands just past the trail's last, smallest circle. The
// head isn't near the box's center: PeloSiMark.tsx draws it (face/hair/sunglasses) at raw
// local coordinates centered around (50, 12), inside a viewBox="-15 -10 130 120" that gets
// rotated 28° (REST_ROTATION) about its own center (50, 50) before rendering. Rotating that
// point moves it to roughly (67.8, 16.5) — well toward the upper-right of the artwork, not
// the middle — so a box positioned by eye (as the previous pass did) puts the visible head
// somewhere else entirely. This resolves the actual head pixel offset within the box, then
// TitleBubble's trail-circle coordinates below resolve the target point, and ROCKET_BOX's
// left/top are solved backward from both so the head itself lands on target.
const ROCKET_BOX = 200;
const HEAD_ROTATED = (() => {
  const rad = (REST_ROTATION * Math.PI) / 180;
  const dy = 12 - 50; // raw head center (50, 12) relative to the rotation pivot (50, 50)
  return { x: 50 - dy * Math.sin(rad), y: 50 + dy * Math.cos(rad) };
})();
// PeloSiMark's viewBox is 130×120 (non-square), scaled uniformly to ROCKET_BOX on both axes.
const HEAD_PX = {
  x: (HEAD_ROTATED.x + 15) * (ROCKET_BOX / 130),
  y: (HEAD_ROTATED.y + 10) * (ROCKET_BOX / 120),
};
// One step past the trail's last circle (the three cascading dots drawn in TitleBubble below,
// local coords {7.5,95}/{-7.5,110}/{-20,122.5} inside a viewBox starting at x=-25 — i.e.
// composite-box pixels (32.5,95)/(17.5,110)/(5,122.5)), continuing its own cascade: circles
// 2→3 step by (-12.5, +12.5), so this is one more step past 3, toward where the head lands.
const HEAD_TARGET = { x: -5, y: 133 };
const ROCKET_REST = { left: HEAD_TARGET.x - HEAD_PX.x, top: HEAD_TARGET.y - HEAD_PX.y };

function cubicBezierPoint(p0: number, p1: number, p2: number, p3: number, t: number): number {
  const mt = 1 - t;
  return mt * mt * mt * p0 + 3 * mt * mt * t * p1 + 3 * mt * t * t * p2 + t * t * t * p3;
}

const FLIGHT_SAMPLES = 11;
const SAMPLE_T = Array.from({ length: FLIGHT_SAMPLES }, (_, i) => i / (FLIGHT_SAMPLES - 1));

// Trailing smoke puffs sampled along the flight path (every other point, skipping the final
// resting frame) — bigger, more opaque, and each its own grey shade so the trail reads as
// visibly billowy rather than one flat repeated dot.
const SMOKE_INDICES = [0, 2, 4, 6, 8];
const SMOKE_COLORS = ["#c9c9c4", "#9a9a95", "#dcdcd6", "#b0b0ab", "#c9c9c4"];

interface LogoIntroProps {
  mounted: boolean;
  shouldAnimate: boolean;
  /** The rocket's flight-in start point (x/y offset from its resting position) that lands
   * it just outside the browser viewport's actual bottom-left corner — measured at runtime
   * by page.tsx against #hero-rocket-rest so it starts from the real screen edge at any
   * viewport size. Null until that measurement resolves (falls back to a fixed constant). */
  flightOrigin: { x: number; y: number } | null;
  /** The rest of the left column (description, status pill, Trades card) — rendered
   * immediately, never gated behind this animation. */
  children: ReactNode;
}

export default function LogoIntro({ mounted, shouldAnimate, flightOrigin, children }: LogoIntroProps) {
  // A true single S-curve (one bend right, one bend left, then settle) from off-screen
  // bottom-left to the rocket's resting spot, sampled densely from a cubic bezier so Framer
  // Motion's between-point interpolation reads as one continuous flowing motion. Control
  // points are fixed ratios of the origin vector (derived from the original hand-tuned
  // {-260,240}/{-30,150}/{-190,55} constants), so the same S-curve shape holds at any
  // magnitude — the flight now starts from wherever page.tsx measures the real viewport
  // corner to be, rather than a point hardcoded for one layout.
  const { flightX, flightY, flightRotate, flightTimes, smokePuffs } = useMemo(() => {
    const origin = flightOrigin ?? FALLBACK_FLIGHT_ORIGIN;
    const control1 = { x: origin.x * 0.11538, y: origin.y * 0.625 };
    const control2 = { x: origin.x * 0.73077, y: origin.y * 0.22917 };
    const end = { x: 0, y: 0 };

    const points = SAMPLE_T.map((t) => ({
      x: cubicBezierPoint(origin.x, control1.x, control2.x, end.x, t),
      y: cubicBezierPoint(origin.y, control1.y, control2.y, end.y, t),
    }));

    // Rotation follows the curve's own tangent direction (derived from consecutive sampled
    // points) so it naturally banks into each bend of the S, rather than a hand-picked array
    // of angles that don't correspond to the actual path — only the final frame is a manual
    // override, settling on the artwork's resting tilt once the rocket has actually arrived.
    const rotate = points.map((p, i) => {
      if (i === points.length - 1) return REST_ROTATION;
      const next = points[i + 1];
      return (Math.atan2(next.y - p.y, next.x - p.x) * 180) / Math.PI + 90;
    });

    // Arc-length-proportional times (not uniform-t) paired with a single linear ease below —
    // this reproduces the bezier's own natural non-uniform speed as one continuous sweep.
    // Uniform times + a per-segment easeInOut instead re-accelerates/decelerates at every one
    // of the 10 segments between keyframes, which reads as stutter rather than one flowing arc.
    const segmentLengths = points.slice(1).map((p, i) => Math.hypot(p.x - points[i].x, p.y - points[i].y));
    const cumulative = segmentLengths.reduce((acc, len) => [...acc, acc[acc.length - 1] + len], [0]);
    const total = cumulative[cumulative.length - 1] || 1;
    const times = cumulative.map((d) => d / total);

    const puffs = SMOKE_INDICES.map((idx, i) => ({
      x: points[idx].x,
      y: points[idx].y,
      color: SMOKE_COLORS[i],
      delay: times[idx] * FLIGHT_DURATION,
    }));

    return {
      flightX: points.map((p) => p.x),
      flightY: points.map((p) => p.y),
      flightRotate: rotate,
      flightTimes: times,
      smokePuffs: puffs,
    };
  }, [flightOrigin]);

  return (
    <>
      {/* Shared composite box for the title bubble and the rocket, so the rocket can rest at
          the bottom-left of the bubble's three-circle "thought trail" instead of being an
          independent flex sibling with a hand-picked offset — the rocket now continues the
          cascade rather than sitting disconnected from it. Height reserved in advance
          (bubble ~138px plus the 200px rocket box, minus overlap) so `children` below never
          shifts when the rocket/bubble mount. */}
      <div className="relative w-fit min-h-[330px] shrink-0 self-start">
        {mounted && <TitleBubble shouldAnimate={shouldAnimate} startDelay={shouldAnimate ? FLIGHT_DURATION : 0} />}

        {/* The rocket's static resting wrapper — deliberately NOT the element Framer Motion
            transforms (that's the motion.div below), so page.tsx's getBoundingClientRect()
            reads the true resting layout box, never an already-animated position. */}
        <div
          id="hero-rocket-rest"
          className="absolute"
          style={{ left: ROCKET_REST.left, top: ROCKET_REST.top, width: ROCKET_BOX, height: ROCKET_BOX }}
        >
          {mounted &&
            shouldAnimate &&
            smokePuffs.map((puff, i) => (
              <motion.div
                key={i}
                className="absolute rounded-full"
                style={{ width: 25, height: 25, top: 87, left: 87, background: puff.color }}
                initial={{ x: puff.x, y: puff.y, opacity: 0, scale: 0.6 }}
                animate={{ opacity: [0, 0.9, 0], scale: [0.6, 1.4, 1.9], x: puff.x + 27, y: puff.y - 22 }}
                transition={{ duration: 0.75, delay: puff.delay, ease: "easeOut" }}
              />
            ))}

          {mounted && (
            <motion.div
              initial={shouldAnimate ? { x: flightX[0], y: flightY[0], rotate: flightRotate[0] } : false}
              animate={
                shouldAnimate
                  ? { x: flightX, y: flightY, rotate: flightRotate }
                  : { x: 0, y: 0, rotate: REST_ROTATION }
              }
              transition={
                shouldAnimate ? { duration: FLIGHT_DURATION, times: flightTimes, ease: "linear" } : { duration: 0 }
              }
            >
              <PeloSiMark size={ROCKET_BOX} />
            </motion.div>
          )}
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-8">{children}</div>
    </>
  );
}

function TitleBubble({ shouldAnimate, startDelay }: { shouldAnimate: boolean; startDelay: number }) {
  return (
    <svg width={325} height={138} viewBox="-25 0 325 137.5" role="img" aria-label="ToTheMoon!">
      <motion.rect
        x={17.5}
        y={10}
        width={265}
        height={72.5}
        rx={22.5}
        fill={BUBBLE_FILL}
        stroke="none"
        initial={shouldAnimate ? { opacity: 0 } : false}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.15, delay: startDelay + BUBBLE_DRAW_DURATION * 0.7 }}
      />

      {/* Classic comic "thought trail" — three circles of decreasing size cascading down
          and to the left from the bubble's bottom-left corner, continuing into the rocket's
          resting position (see the composite box above), per the reference image. */}
      {[
        { cx: 7.5, cy: 95, r: 8.75 },
        { cx: -7.5, cy: 110, r: 6.25 },
        { cx: -20, cy: 122.5, r: 3.75 },
      ].map((dot, i) => (
        <motion.circle
          key={i}
          cx={dot.cx}
          cy={dot.cy}
          r={dot.r}
          fill={BUBBLE_FILL}
          stroke={BUBBLE_STROKE}
          strokeWidth={2.5}
          initial={shouldAnimate ? { opacity: 0, scale: 0.5 } : false}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.15, delay: startDelay + BUBBLE_DRAW_DURATION * 0.85 + i * 0.06 }}
        />
      ))}

      <motion.rect
        x={17.5}
        y={10}
        width={265}
        height={72.5}
        rx={22.5}
        fill="none"
        stroke={BUBBLE_STROKE}
        strokeWidth={3}
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
        x={150}
        y={50}
        textAnchor="middle"
        dominantBaseline="middle"
        fontSize={33}
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
