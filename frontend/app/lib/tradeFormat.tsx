import { ReactNode } from "react";

export type BadgeTone = "positive" | "negative" | "neutral";

const BUY_CODES = new Set(["P", "A", "M"]);
const SELL_CODES = new Set(["S", "D", "F"]);

export function badge(label: string, tone: BadgeTone) {
  const cls =
    tone === "positive"
      ? "bg-positive/15 text-positive"
      : tone === "negative"
        ? "bg-destructive/15 text-destructive"
        : "bg-muted text-muted-foreground";
  return <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${cls}`}>{label}</span>;
}

export function badgeTone(key: string, value: string): BadgeTone {
  if (key === "acquired_disposed") return value === "A" ? "positive" : value === "D" ? "negative" : "neutral";
  if (key === "transaction_code") return BUY_CODES.has(value) ? "positive" : SELL_CODES.has(value) ? "negative" : "neutral";
  if (key === "transaction_type") {
    const upper = value.toUpperCase();
    return upper.startsWith("P") ? "positive" : upper.startsWith("S") ? "negative" : "neutral";
  }
  return "neutral";
}

export function badgeLabel(key: string, value: string): string {
  if (key === "acquired_disposed") return value === "A" ? "Acquired" : value === "D" ? "Disposed" : value;
  return value;
}

export function renderCell(key: string, value: unknown): ReactNode {
  const str = value === null || value === undefined || value === "" ? "" : String(value);
  if (!str) return <span className="text-muted-foreground/50">—</span>;
  if (key === "acquired_disposed" || key === "transaction_code" || key === "transaction_type") {
    return badge(badgeLabel(key, str), badgeTone(key, str));
  }
  return str;
}

export function formatMeta(value: unknown, format?: "currency"): string {
  if (value === null || value === undefined || value === "") return "—";
  if (format === "currency") {
    const num = Number(value);
    if (!Number.isNaN(num)) return `$${num.toLocaleString()}`;
  }
  return typeof value === "number" ? value.toLocaleString() : String(value);
}
