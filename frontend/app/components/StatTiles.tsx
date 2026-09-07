import { ReactNode } from "react";
import { badgeTone, formatMeta } from "../lib/tradeFormat";
import type { SummaryConfig } from "./TradeTable";

interface StatTilesProps {
  total: number;
  rows: Record<string, unknown>[];
  summary: SummaryConfig;
}

function Tile({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-card px-4 py-3 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label}</p>
      <div className="mt-0.5 font-mono text-sm text-card-foreground">{children}</div>
    </div>
  );
}

export default function StatTiles({ total, rows, summary }: StatTilesProps) {
  const tickerKey = summary.targetTickerKey;
  const distinctTickers = tickerKey
    ? new Set(rows.map((r) => r[tickerKey]).filter((v) => v !== null && v !== undefined && v !== "")).size
    : null;

  let thirdTile: ReactNode = null;
  if (summary.badgeKey) {
    const key = summary.badgeKey;
    let positive = 0;
    let negative = 0;
    for (const row of rows) {
      const value = row[key];
      if (value === null || value === undefined || value === "") continue;
      const tone = badgeTone(key, String(value));
      if (tone === "positive") positive++;
      else if (tone === "negative") negative++;
    }
    const counted = positive + negative;
    const positivePct = counted > 0 ? Math.round((positive / counted) * 100) : 0;
    thirdTile = (
      <Tile label="Buy / sell in view">
        {counted > 0 ? (
          <div className="flex flex-col gap-1">
            <div className="flex h-1.5 w-full overflow-hidden rounded-full bg-muted">
              <div className="bg-positive" style={{ width: `${positivePct}%` }} />
              <div className="bg-destructive" style={{ width: `${100 - positivePct}%` }} />
            </div>
            <p className="font-sans text-xs text-muted-foreground">
              {positive} bought · {negative} sold
            </p>
          </div>
        ) : (
          <span className="text-muted-foreground">—</span>
        )}
      </Tile>
    );
  } else if (summary.metaKey) {
    const metaKey = summary.metaKey;
    const sum = rows.reduce((acc, row) => {
      const num = Number(row[metaKey]);
      return Number.isFinite(num) ? acc + num : acc;
    }, 0);
    thirdTile = <Tile label={`${summary.metaLabel ?? "Total"} in view`}>{formatMeta(sum, summary.metaFormat)}</Tile>;
  }

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
      <Tile label="Total matches">{total.toLocaleString()}</Tile>
      {distinctTickers !== null && <Tile label="Tickers in view">{distinctTickers.toLocaleString()}</Tile>}
      {thirdTile}
    </div>
  );
}
