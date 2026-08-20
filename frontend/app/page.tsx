"use client";

import { useState } from "react";
import TradeTable from "./components/TradeTable";
import { Category } from "./lib/api";

const TABS: { key: Category; label: string }[] = [
  { key: "insiders", label: "Corporate Insiders" },
  { key: "institutions", label: "Institutions (13F)" },
  { key: "congress", label: "Congress" },
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

const NAME_LABELS: Record<Category, string> = {
  insiders: "Insider name",
  institutions: "Filer name",
  congress: "Member name",
};

const TICKER_LABELS: Record<Category, string> = {
  insiders: "Ticker",
  institutions: "Company",
  congress: "Ticker",
};

export default function Home() {
  const [activeTab, setActiveTab] = useState<Category>("insiders");

  return (
    <div className="flex flex-1 flex-col bg-zinc-50 dark:bg-black">
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-6 py-10">
        <h1 className="text-2xl font-semibold text-black dark:text-zinc-50">Trade Tracker</h1>

        <div className="flex gap-2 border-b border-zinc-200 dark:border-zinc-800">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 text-sm font-medium ${
                activeTab === tab.key
                  ? "border-b-2 border-black text-black dark:border-white dark:text-white"
                  : "text-zinc-500 hover:text-black dark:hover:text-white"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <TradeTable
          category={activeTab}
          nameLabel={NAME_LABELS[activeTab]}
          tickerLabel={TICKER_LABELS[activeTab]}
          columns={COLUMNS[activeTab]}
        />
      </main>
    </div>
  );
}
