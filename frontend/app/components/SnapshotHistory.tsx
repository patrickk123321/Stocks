"use client";

import { ClockCounterClockwise } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { listSnapshots, SnapshotSummary } from "../lib/portfolioApi";

// Read-only — recommendations are always computed from the single latest
// snapshot (see backend/app/routers/portfolio.py). This just makes the
// previously-invisible upload history visible, not interactive switching.
export default function SnapshotHistory() {
  const [snapshots, setSnapshots] = useState<SnapshotSummary[] | null>(null);

  useEffect(() => {
    listSnapshots()
      .then(setSnapshots)
      .catch(() => setSnapshots([]));
  }, []);

  if (!snapshots || snapshots.length < 2) return null;

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-border bg-card p-4">
      <div className="flex items-center gap-2">
        <ClockCounterClockwise size={16} className="text-muted-foreground" aria-hidden="true" />
        <h2 className="text-sm font-semibold text-card-foreground">Past uploads</h2>
      </div>
      <ul className="flex flex-col gap-1.5">
        {snapshots.map((s, i) => (
          <li key={s.id} className="flex items-center justify-between text-xs">
            <span className={i === 0 ? "font-medium text-card-foreground" : "text-muted-foreground"}>
              {new Date(s.uploaded_at).toLocaleString()}
              {i === 0 ? " (current)" : ""}
            </span>
            <span className="font-mono text-muted-foreground">
              ${s.total_value.toLocaleString()} · {s.holding_count} holding{s.holding_count === 1 ? "" : "s"}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
