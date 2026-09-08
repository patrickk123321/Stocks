"use client";

import { motion, useReducedMotion } from "framer-motion";
import { ReactNode, useEffect, useRef, useState } from "react";
import PeloSiMark from "./PeloSiMark";

// Homepage-only rocket-flies-in intro, wrapping the plain/static PeloSiMark (which stays
// untouched for its unrelated Header.tsx usage). Independent session key/gating from
// CandlestickHero.tsx — these are two separate one-time animations. See DESIGN.md's
// "Homepage logo intro" note.
const SESSION_KEY = "tothemoon_logo_intro_played";
const FLIGHT_DURATION = 1.3;
const BUBBLE_DRAW_DURATION = 0.45;
const BUBBLE_STROKE = "#1c2b45";
const BUBBLE_FILL = "var(--color-card)";
const TITLE_COLOR = "var(--color-foreground)";

// Waypoints trailing the rocket's S-curve flight path (see the motion.div below) —
// approximate, not physically tracking the rotated engine nozzle; a decorative trail.
const SMOKE_PUFFS = [
  { x: -280, y: 220, delay: 0 },
  { x: -170, y: 150, delay: 0.25 },
  { x: -220, y: 95, delay: 0.5 },
  { x: -100, y: 50, delay: 0.75 },
  { x: -40, y: 15, delay: 0.95 },
];

interface LogoIntroProps {
  /** The rest of the left column (description, status pill, Trades card) — rendered
   * immediately, never gated behind this animation. */
  children: ReactNode;
}

export default function LogoIntro({ children }: LogoIntroProps) {
  const prefersReducedMotion = useReducedMotion();
  const [mounted, setMounted] = useState(false);
  const [shouldAnimate, setShouldAnimate] = useState(false);
  // Guards against React Strict Mode's dev-only double-invocation of effects — the same
  // bug that silently prevented CandlestickHero's animation from ever playing.
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

  return (
    <>
      <div className="relative -ml-2 shrink-0 self-start" style={{ width: 160, height: 160 }}>
        {mounted &&
          shouldAnimate &&
          SMOKE_PUFFS.map((puff, i) => (
            <motion.div
              key={i}
              className="absolute rounded-full"
              style={{ width: 14, height: 14, top: 70, left: 70, background: "rgba(200,200,195,0.65)" }}
              initial={{ x: puff.x, y: puff.y, opacity: 0, scale: 0.6 }}
              animate={{ opacity: [0, 0.7, 0], scale: [0.6, 1.3, 1.8], x: puff.x + 20, y: puff.y - 15 }}
              transition={{ duration: 0.7, delay: puff.delay, ease: "easeOut" }}
            />
          ))}

        {mounted && (
          <motion.div
            initial={shouldAnimate ? { x: -280, y: 220, rotate: 10 } : false}
            animate={
              shouldAnimate
                ? { x: [-280, -140, -200, -60, 0], y: [220, 140, 70, 20, 0], rotate: [10, -15, 12, -6, 28] }
                : { x: 0, y: 0, rotate: 28 }
            }
            transition={
              shouldAnimate
                ? { duration: FLIGHT_DURATION, times: [0, 0.3, 0.55, 0.8, 1], ease: "easeInOut" }
                : { duration: 0 }
            }
          >
            <PeloSiMark size={160} />
          </motion.div>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-6">
        <div className="flex h-24 items-center justify-center">
          {mounted && <TitleBubble shouldAnimate={shouldAnimate} startDelay={shouldAnimate ? FLIGHT_DURATION : 0} />}
        </div>
        {children}
      </div>
    </>
  );
}

function TitleBubble({ shouldAnimate, startDelay }: { shouldAnimate: boolean; startDelay: number }) {
  return (
    <svg width={240} height={90} viewBox="0 0 240 90" role="img" aria-label="ToTheMoon">
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
      <motion.polygon
        points="18,50 18,64 2,58"
        fill={BUBBLE_FILL}
        stroke={BUBBLE_STROKE}
        strokeWidth={2.5}
        initial={shouldAnimate ? { opacity: 0 } : false}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.1, delay: startDelay + BUBBLE_DRAW_DURATION * 0.85 }}
      />
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
      <motion.text
        x={120}
        y={40}
        textAnchor="middle"
        dominantBaseline="middle"
        className="font-display"
        fontSize={26}
        fontWeight={600}
        fill={TITLE_COLOR}
        initial={shouldAnimate ? { opacity: 0, scale: 0.9 } : false}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.25, delay: startDelay + BUBBLE_DRAW_DURATION * 0.8 }}
      >
        ToTheMoon
      </motion.text>
    </svg>
  );
}
