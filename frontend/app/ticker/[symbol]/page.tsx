"use client";

import { Bank, Buildings, UserCircle, WarningCircle } from "@phosphor-icons/react";
import { ArrowLeft } from "@phosphor-icons/react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";
import { fetchTrades } from "../../lib/api";
import { badge, badgeLabel, badgeTone, formatMeta } from "../../lib/tradeFormat";

type Row = Record<string, unknown>;

function EntitySection({
  icon: Icon,
  title,
  accentClass,
  loading,
  error,
  rows,
  renderRow,
  emptyMessage,
}: {
  icon: typeof UserCircle;
  title: string;
  accentClass: string;
  loading: boolean;
  error: string | null;
  rows: Row[];
  renderRow: (row: Row, i: number) => ReactNode;
  emptyMessage: string;
}) {
  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <span className={`flex h-8 w-8 items-center justify-center border border-border-strong ${accentClass}`}>
          <Icon size={16} aria-hidden="true" />
        </span>
        <h2 className="font-semibold text-foreground">{title}</h2>
      </div>
      <div className="overflow-hidden border border-border bg-card">
        {loading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className={`flex items-center justify-between gap-4 px-4 py-3.5 ${i > 0 ? "border-t border-border" : ""}`}>
              <div className="h-4 w-40 animate-pulse bg-muted" />
              <div className="h-4 w-24 animate-pulse bg-muted" />
            </div>
          ))
        ) : error ? (
          <div role="alert" className="flex items-center gap-2 px-4 py-4 text-sm text-destructive">
            <WarningCircle size={16} aria-hidden="true" />
            {error}
          </div>
        ) : rows.length === 0 ? (
          <p className="px-4 py-6 text-sm text-muted-foreground">{emptyMessage}</p>
        ) : (
          rows.map(renderRow)
        )}
      </div>
    </section>
  );
}

export default function TickerPage() {
  const params = useParams<{ symbol: string }>();
  const symbol = (params.symbol ?? "").toUpperCase();

  const [insiders, setInsiders] = useState<Row[]>([]);
  const [insidersLoading, setInsidersLoading] = useState(true);
  const [insidersError, setInsidersError] = useState<string | null>(null);

  const [congress, setCongress] = useState<Row[]>([]);
  const [congressLoading, setCongressLoading] = useState(true);
  const [congressError, setCongressError] = useState<string | null>(null);

  const [institutions, setInstitutions] = useState<Row[]>([]);
  const [institutionsLoading, setInstitutionsLoading] = useState(false);
  const [institutionsError, setInstitutionsError] = useState<string | null>(null);
  const [companyName, setCompanyName] = useState<string | null>(null);

  useEffect(() => {
    if (!symbol) return;

    setInsidersLoading(true);
    fetchTrades("insiders", "", { ticker: symbol, limit: 100 })
      .then((page) => {
        setInsiders(page.rows);
        const name = page.rows.find((r) => r.issuer_name)?.issuer_name;
        if (typeof name === "string") setCompanyName(name);
      })
      .catch(() => setInsidersError("Couldn't load insider trades for this ticker."))
      .finally(() => setInsidersLoading(false));

    setCongressLoading(true);
    fetchTrades("congress", "", { ticker: symbol, limit: 100 })
      .then((page) => setCongress(page.rows))
      .catch(() => setCongressError("Couldn't load congressional trades for this ticker."))
      .finally(() => setCongressLoading(false));
  }, [symbol]);

  useEffect(() => {
    if (!companyName) return;
    setInstitutionsLoading(true);
    fetchTrades("institutions", companyName, { limit: 100 })
      .then((page) => setInstitutions(page.rows))
      .catch(() => setInstitutionsError("Couldn't load institutional holdings for this ticker."))
      .finally(() => setInstitutionsLoading(false));
  }, [companyName]);

  return (
    <div className="flex flex-1 flex-col">
      <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-8 px-6 py-10">
        <div className="flex flex-col gap-1">
          <Link
            href="/trade-tracker"
            className="flex w-fit items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeft size={16} aria-hidden="true" />
            Trade Tracker
          </Link>
          <h1 className="text-3xl font-semibold tracking-tight text-foreground">{symbol}</h1>
          <p className="text-sm leading-relaxed text-muted-foreground">
            Every tracked insider and congressional trade in {symbol}, plus a best-effort match on institutional 13F holdings.
          </p>
        </div>

        <EntitySection
          icon={UserCircle}
          title="Corporate Insiders"
          accentClass="text-accent"
          loading={insidersLoading}
          error={insidersError}
          rows={insiders}
          emptyMessage={`No tracked insider trades in ${symbol}.`}
          renderRow={(row, i) => {
            const code = String(row.acquired_disposed ?? "");
            return (
              <div key={i} className={`flex items-center justify-between gap-4 px-4 py-3.5 ${i > 0 ? "border-t border-border" : ""}`}>
                <div className="flex min-w-0 items-center gap-3">
                  {code && badge(badgeLabel("acquired_disposed", code), badgeTone("acquired_disposed", code))}
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-card-foreground">{String(row.owner_name ?? "Unknown")}</p>
                    <p className="truncate text-xs text-muted-foreground">{String(row.officer_title ?? "")}</p>
                  </div>
                </div>
                <div className="shrink-0 text-right">
                  <p className="font-mono text-xs text-card-foreground">{formatMeta(row.shares)} sh</p>
                  <p className="text-xs text-muted-foreground">{String(row.transaction_date ?? "")}</p>
                </div>
              </div>
            );
          }}
        />

        <EntitySection
          icon={Bank}
          title="Congress"
          accentClass="text-positive"
          loading={congressLoading}
          error={congressError}
          rows={congress}
          emptyMessage={`No tracked congressional trades in ${symbol}.`}
          renderRow={(row, i) => {
            const type = String(row.transaction_type ?? "");
            return (
              <div key={i} className={`flex items-center justify-between gap-4 px-4 py-3.5 ${i > 0 ? "border-t border-border" : ""}`}>
                <div className="flex min-w-0 items-center gap-3">
                  {type && badge(badgeLabel("transaction_type", type), badgeTone("transaction_type", type))}
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-card-foreground">{String(row.member_name ?? "Unknown")}</p>
                    <p className="truncate text-xs text-muted-foreground">{String(row.state_district ?? "")}</p>
                  </div>
                </div>
                <div className="shrink-0 text-right">
                  <p className="font-mono text-xs text-card-foreground">{String(row.amount_range ?? "")}</p>
                  <p className="text-xs text-muted-foreground">{String(row.transaction_date ?? "")}</p>
                </div>
              </div>
            );
          }}
        />

        <EntitySection
          icon={Buildings}
          title="Institutions (13F)"
          accentClass="text-info"
          loading={institutionsLoading}
          error={institutionsError}
          rows={institutions}
          emptyMessage={
            companyName
              ? `No institutional 13F holdings matched by company name ("${companyName}") for ${symbol}.`
              : `13F filings only report CUSIP, not ticker — institutional matching needs a resolved company name from an insider filing, which isn't available for ${symbol} yet.`
          }
          renderRow={(row, i) => (
            <div key={i} className={`flex items-center justify-between gap-4 px-4 py-3.5 ${i > 0 ? "border-t border-border" : ""}`}>
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-card-foreground">{String(row.filer_name ?? "Unknown")}</p>
                <p className="truncate font-mono text-xs text-muted-foreground">{String(row.cusip ?? "")}</p>
              </div>
              <div className="shrink-0 text-right">
                <p className="font-mono text-xs text-card-foreground">{formatMeta(row.value, "currency")}</p>
                <p className="text-xs text-muted-foreground">{String(row.period_of_report ?? "")}</p>
              </div>
            </div>
          )}
        />

        {companyName && (
          <p className="text-xs text-muted-foreground/85">
            Institutional holdings above are matched by company name (&quot;{companyName}&quot;), not ticker — 13F filings don&apos;t report
            ticker symbols, only CUSIP, so this match is best-effort rather than exhaustive.
          </p>
        )}
      </main>
    </div>
  );
}
