import { ReactNode } from "react";

export type BadgeTone = "positive" | "negative" | "neutral";

const BUY_CODES = new Set(["P", "A", "M"]);
const SELL_CODES = new Set(["S", "D", "F"]);

// SEC Form 4 transaction codes (17 CFR 249.104) — plain-English expansions for
// the single-letter values in transaction_code/transaction_type, surfaced as a
// hover tooltip since the badge itself only has room for the raw code.
const TRANSACTION_CODE_EXPLANATIONS: Record<string, string> = {
  P: "Open market or private purchase",
  S: "Open market or private sale",
  A: "Grant, award, or other acquisition",
  D: "Sale or disposition to the issuer",
  M: "Exercise or conversion of a derivative security",
  F: "Payment of exercise price or tax liability by delivering or withholding shares",
  G: "Bona fide gift",
  C: "Conversion of a derivative security",
  E: "Expiration of a short derivative position",
  H: "Expiration of a long derivative position",
  I: "Discretionary transaction",
  J: "Other acquisition or disposition",
  K: "Equity swap or similar transaction",
  L: "Small acquisition",
  O: "Exercise of an out-of-the-money derivative",
  U: "Disposition pursuant to a tender of shares",
  X: "Exercise of an in-the-money or at-the-money derivative",
  Z: "Deposit into or withdrawal from a voting trust",
};

export function badgeTitle(key: string, value: string): string | undefined {
  if (key === "acquired_disposed") {
    return value === "A" ? "Shares acquired by the insider" : value === "D" ? "Shares disposed by the insider" : undefined;
  }
  if (key === "transaction_code" || key === "transaction_type") {
    return TRANSACTION_CODE_EXPLANATIONS[value.toUpperCase()];
  }
  return undefined;
}

export function badge(label: string, tone: BadgeTone, title?: string) {
  const cls = tone === "positive" ? "text-positive" : tone === "negative" ? "text-destructive" : "text-muted-foreground";
  return (
    <span className={`font-mono text-xs font-semibold uppercase tracking-wide ${cls}`} title={title}>
      [{label}]
    </span>
  );
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
  if (!str) return <span className="text-muted-foreground/85">—</span>;
  if (key === "acquired_disposed" || key === "transaction_code" || key === "transaction_type") {
    return badge(badgeLabel(key, str), badgeTone(key, str), badgeTitle(key, str));
  }
  if (key === "chamber") return str.charAt(0).toUpperCase() + str.slice(1);
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

// Abbreviated form of formatMeta (137935 -> "137.9K") for the mobile row width,
// where the full formatted number doesn't fit next to the badge/name. Falls
// back to the plain value for non-numeric metas (e.g. congress's "amount_range",
// which is already a compact textual range like "$1,001 - $15,000").
export function formatMetaCompact(value: unknown, format?: "currency"): string {
  if (value === null || value === undefined || value === "") return "—";
  const num = Number(value);
  if (Number.isNaN(num)) return typeof value === "number" ? value.toLocaleString() : String(value);
  const abs = Math.abs(num);
  const compact =
    abs >= 1_000_000_000
      ? `${(num / 1_000_000_000).toFixed(1)}B`
      : abs >= 1_000_000
        ? `${(num / 1_000_000).toFixed(1)}M`
        : abs >= 1_000
          ? `${(num / 1_000).toFixed(1)}K`
          : num.toLocaleString();
  return format === "currency" ? `$${compact}` : compact;
}

const RELATIVE_TIME = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["year", 31536000], ["month", 2592000], ["day", 86400], ["hour", 3600], ["minute", 60],
];

export function formatRelativeTime(isoString: string): string {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return isoString;
  const seconds = (date.getTime() - Date.now()) / 1000;
  for (const [unit, secondsInUnit] of UNITS) {
    if (Math.abs(seconds) >= secondsInUnit) {
      return RELATIVE_TIME.format(Math.round(seconds / secondsInUnit), unit);
    }
  }
  return "just now";
}
