"use client";

import { ArrowLeft, Bank, Buildings, UserCircle } from "@phosphor-icons/react";
import Link from "next/link";
import { useState } from "react";
import TradeTable from "../components/TradeTable";
import { Category } from "../lib/api";

const TABS: { key: Category; label: string; icon: typeof UserCircle }[] = [
  { key: "insiders", label: "Corporate Insiders", icon: UserCircle },
  { key: "institutions", label: "Institutions (13F)", icon: Buildings },
  { key: "congress", label: "Congress", icon: Bank },
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
    { key: "member_name", label: "Member" },
    { key: "state_district", label: "District" },
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

export default function TradeTrackerPage() {
  const [activeTab, setActiveTab] = useState<Category>("insiders");

  return (
    <div className="flex flex-1 flex-col">
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-6 py-10">
        <div className="flex flex-col gap-1">
          <Link
            href="/"
            className="flex w-fit items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeft size={16} aria-hidden="true" />
            Stocks
          </Link>
          <h1 className="text-2xl font-semibold text-foreground">Trade Tracker</h1>
          <p className="text-sm text-muted-foreground">
            Corporate insider trades, institutional 13F holdings, and congressional trades — refreshed daily at 9am.
          </p>
        </div>

        <div className="flex gap-1 border-b border-border">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex cursor-pointer items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
                  active
                    ? "border-accent text-foreground"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                }`}
              >
                <Icon size={16} weight={active ? "fill" : "regular"} aria-hidden="true" />
                {tab.label}
              </button>
            );
          })}
        </div>

        <TradeTable
          category={activeTab}
          searchPlaceholder={SEARCH_PLACEHOLDERS[activeTab]}
          columns={COLUMNS[activeTab]}
        />
      </main>
    </div>
  );
}
