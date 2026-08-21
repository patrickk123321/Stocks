"use client";

import { Bank, Buildings, UserCircle } from "@phosphor-icons/react";
import { useState } from "react";
import PositionChanges from "../components/PositionChanges";
import TradeTable, { SummaryConfig } from "../components/TradeTable";
import { Category } from "../lib/api";

const TABS: { key: Category; label: string; icon: typeof UserCircle; active: string; inactive: string }[] = [
  {
    key: "insiders",
    label: "Corporate Insiders",
    icon: UserCircle,
    active: "bg-accent/15 text-accent",
    inactive: "text-muted-foreground hover:bg-muted hover:text-foreground",
  },
  {
    key: "institutions",
    label: "Institutions (13F)",
    icon: Buildings,
    active: "bg-warning/15 text-warning",
    inactive: "text-muted-foreground hover:bg-muted hover:text-foreground",
  },
  {
    key: "congress",
    label: "Congress",
    icon: Bank,
    active: "bg-positive/15 text-positive",
    inactive: "text-muted-foreground hover:bg-muted hover:text-foreground",
  },
];

const COLUMNS: Record<Category, { key: string; label: string }[]> = {
  insiders: [
    { key: "issuer_ticker", label: "Ticker" },
    { key: "issuer_name", label: "Company" },
    { key: "owner_name", label: "Insider" },
    { key: "officer_title", label: "Title" },
    { key: "transaction_code", label: "Code" },
    { key: "acquired_disposed", label: "A/D" },
    { key: "shares", label: "Shares" },
    { key: "price_per_share", label: "Price" },
    { key: "transaction_date", label: "Date" },
  ],
  institutions: [
    { key: "issuer_name", label: "Company" },
    { key: "cusip", label: "CUSIP" },
    { key: "filer_name", label: "Filer" },
    { key: "value", label: "Value ($)" },
    { key: "shares", label: "Shares" },
    { key: "investment_discretion", label: "Discretion" },
    { key: "period_of_report", label: "Period" },
  ],
  congress: [
    { key: "chamber", label: "Chamber" },
    { key: "member_name", label: "Member" },
    { key: "state_district", label: "State/District" },
    { key: "ticker", label: "Ticker" },
    { key: "asset_description", label: "Asset" },
    { key: "transaction_type", label: "Type" },
    { key: "amount_range", label: "Amount" },
    { key: "transaction_date", label: "Date" },
  ],
};

const SEARCH_PLACEHOLDERS: Record<Category, string> = {
  insiders: "Search by ticker, insider, or company",
  institutions: "Search by company, filer, or CUSIP",
  congress: "Search by ticker, member, or asset",
};

const SUMMARY: Record<Category, SummaryConfig> = {
  insiders: {
    actorLabel: "Insider",
    actorKey: "owner_name",
    targetTickerKey: "issuer_ticker",
    targetNameKey: "issuer_name",
    badgeKey: "acquired_disposed",
    dateKey: "transaction_date",
    metaKey: "shares",
    metaLabel: "Shares",
    sourceLabel: "SEC EDGAR — Form 4 filing",
    sourceNote:
      "Read directly from the SEC's structured EDGAR filing feed (not a PDF or text extraction) — the most reliable source in this app.",
    sourceVerified: true,
  },
  institutions: {
    actorLabel: "Institution",
    actorKey: "filer_name",
    targetTickerKey: "cusip",
    targetNameKey: "issuer_name",
    dateKey: "period_of_report",
    metaKey: "value",
    metaLabel: "Value",
    metaFormat: "currency",
    sourceLabel: "SEC EDGAR — Form 13F-HR filing",
    sourceNote:
      "Read directly from the SEC's structured EDGAR filing feed (not a PDF or text extraction) — the most reliable source in this app.",
    sourceVerified: true,
  },
  congress: {
    actorLabel: "Member of Congress",
    actorKey: "member_name",
    targetTickerKey: "ticker",
    targetNameKey: "asset_description",
    badgeKey: "transaction_type",
    dateKey: "transaction_date",
    metaKey: "amount_range",
    metaLabel: "Amount",
    // House and Senate rows come from genuinely different sources with different
    // reliability — sourceFor gives each row its own accurate label instead of
    // papering over the difference with one generic category-level claim.
    sourceLabel: "House Clerk PDF + Senate via Financial Modeling Prep",
    sourceNote:
      "House rows are auto-extracted from House Clerk PDFs; Senate rows come via a third-party API (efdsearch.senate.gov blocks direct automated access). Expand a row for its specific source.",
    sourceVerified: false,
    sourceFor: (row) =>
      row.chamber === "senate"
        ? {
            label: "Financial Modeling Prep — Senate disclosure",
            note:
              "efdsearch.senate.gov blocks direct automated access, so this is read via a third-party API rather than the primary source directly — but the link below points to the actual Senate filing page for verification.",
            verified: false,
          }
        : {
            label: "House Clerk PDF — auto-extracted",
            note:
              "The House Clerk only publishes these as PDFs, so fields are extracted with a best-effort parser rather than read from structured data. Use \"View original filing\" to confirm any row against the source PDF.",
            verified: false,
          },
  },
};

type InstitutionsView = "holdings" | "changes";

export default function TradeTrackerPage() {
  const [activeTab, setActiveTab] = useState<Category>("insiders");
  const [institutionsView, setInstitutionsView] = useState<InstitutionsView>("holdings");

  return (
    <div className="flex flex-1 flex-col">
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-6 py-10">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">Trade Tracker</h1>
          <p className="text-sm leading-relaxed text-muted-foreground">
            Corporate insider trades, institutional 13F holdings, and congressional trades — refreshed daily at 9am.
          </p>
        </div>

        <div className="flex flex-wrap gap-1.5 rounded-xl border border-border bg-card p-1.5">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex cursor-pointer items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 ${
                  active ? tab.active : tab.inactive
                }`}
              >
                <Icon size={16} weight={active ? "fill" : "regular"} aria-hidden="true" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {activeTab === "institutions" && (
          <div className="flex gap-1.5 border-b border-border">
            {(["holdings", "changes"] as const).map((view) => (
              <button
                key={view}
                onClick={() => setInstitutionsView(view)}
                className={`cursor-pointer border-b-2 px-3 py-2 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 ${
                  institutionsView === view
                    ? "border-warning text-warning"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                }`}
              >
                {view === "holdings" ? "All Holdings" : "Position Changes"}
              </button>
            ))}
          </div>
        )}

        {activeTab === "institutions" && institutionsView === "changes" ? (
          <PositionChanges />
        ) : (
          <TradeTable
            category={activeTab}
            searchPlaceholder={SEARCH_PLACEHOLDERS[activeTab]}
            columns={COLUMNS[activeTab]}
            summary={SUMMARY[activeTab]}
            emptyIcon={TABS.find((tab) => tab.key === activeTab)!.icon}
          />
        )}
      </main>
    </div>
  );
}
