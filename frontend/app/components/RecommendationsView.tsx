"use client";

import { ArrowDown, ArrowUp, ChartPieSlice, Warning } from "@phosphor-icons/react";
import { Recommendations } from "../lib/portfolioApi";

const ASSET_CLASS_COLOR: Record<string, string> = {
  stock: "bg-accent",
  bond: "bg-warning",
  cash: "bg-positive",
  alternative: "bg-destructive",
  Unclassified: "bg-border",
};

const ASSET_CLASS_LABEL: Record<string, string> = {
  stock: "Stocks",
  bond: "Bonds",
  cash: "Cash",
  alternative: "Alternatives",
  Unclassified: "Unclassified",
};

function colorFor(key: string): string {
  return ASSET_CLASS_COLOR[key] ?? "bg-muted-foreground";
}

function labelFor(key: string): string {
  return ASSET_CLASS_LABEL[key] ?? key;
}

export default function RecommendationsView({ data }: { data: Recommendations }) {
  const { allocation, gaps, sector_flags } = data;
  const assetClasses = Object.entries(allocation.asset_class).sort((a, b) => b[1].pct - a[1].pct);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start gap-2 rounded-lg border border-border bg-muted/50 px-4 py-3 text-xs leading-relaxed text-muted-foreground">
        <Warning size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
        <span>
          For personal informational use only — not registered investment advice. This is a simple rules-based allocator, not a
          personalized recommendation from a financial professional.
        </span>
      </div>

      <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-6">
        <div className="flex items-center gap-2">
          <ChartPieSlice size={18} className="text-accent" aria-hidden="true" />
          <h2 className="font-semibold text-card-foreground">Current allocation</h2>
          <span className="ml-auto font-mono text-sm text-muted-foreground">
            ${allocation.total_value.toLocaleString()}
          </span>
        </div>

        <div className="flex h-3 w-full overflow-hidden rounded-full bg-muted">
          {assetClasses.map(([key, bucket]) => (
            <div key={key} className={colorFor(key)} style={{ width: `${bucket.pct}%` }} title={`${labelFor(key)}: ${bucket.pct}%`} />
          ))}
        </div>

        <div className="flex flex-wrap gap-x-5 gap-y-1.5">
          {assetClasses.map(([key, bucket]) => (
            <div key={key} className="flex items-center gap-1.5 text-xs">
              <span className={`h-2 w-2 rounded-full ${colorFor(key)}`} aria-hidden="true" />
              <span className="text-muted-foreground">{labelFor(key)}</span>
              <span className="font-mono font-medium text-card-foreground">{bucket.pct}%</span>
            </div>
          ))}
        </div>
      </div>

      {gaps.length > 0 && (
        <div className="flex flex-col gap-3">
          <h2 className="font-semibold text-foreground">Allocation gaps</h2>
          <div className="flex flex-col gap-2">
            {gaps.map((gap) => (
              <div key={gap.asset_class} className="flex flex-col gap-2 rounded-lg border border-border bg-card p-4">
                <div className="flex items-start gap-2">
                  {gap.direction === "overweight" ? (
                    <ArrowUp size={16} className="mt-0.5 shrink-0 text-warning" aria-hidden="true" />
                  ) : (
                    <ArrowDown size={16} className="mt-0.5 shrink-0 text-accent" aria-hidden="true" />
                  )}
                  <p className="text-sm text-card-foreground">{gap.message}</p>
                </div>
                {gap.suggested_funds.length > 0 && (
                  <ul className="ml-6 flex flex-col gap-0.5 text-xs text-muted-foreground">
                    {gap.suggested_funds.map((fund) => (
                      <li key={fund}>• {fund}</li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {sector_flags.length > 0 && (
        <div className="flex flex-col gap-3">
          <h2 className="font-semibold text-foreground">Sector concentration</h2>
          <div className="flex flex-col gap-2">
            {sector_flags.map((flag) => (
              <div key={flag.sector} className="rounded-lg border border-warning/40 bg-warning/10 px-4 py-3 text-sm text-warning">
                {flag.message}
              </div>
            ))}
          </div>
        </div>
      )}

      {gaps.length === 0 && sector_flags.length === 0 && (
        <p className="text-sm text-muted-foreground">
          Your current allocation is within range of your target, and no sector looks overly concentrated.
        </p>
      )}
    </div>
  );
}
