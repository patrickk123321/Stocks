"use client";

import { useEffect, useState } from "react";
import { Category, fetchTrades, refreshTrades } from "../lib/api";

interface Column {
  key: string;
  label: string;
}

interface TradeTableProps {
  category: Category;
  nameLabel: string;
  tickerLabel: string;
  columns: Column[];
}

export default function TradeTable({ category, nameLabel, tickerLabel, columns }: TradeTableProps) {
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [ticker, setTicker] = useState("");
  const [name, setName] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchTrades(category, { ticker, name, startDate, endDate });
      setRows(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [category]);

  const handleRefresh = async () => {
    setRefreshing(true);
    setError(null);
    try {
      await refreshTrades(category);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to refresh data");
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col text-sm text-zinc-600 dark:text-zinc-400">
          {tickerLabel}
          <input
            className="rounded border border-zinc-300 px-2 py-1 text-black dark:border-zinc-700 dark:bg-zinc-900 dark:text-white"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
          />
        </label>
        <label className="flex flex-col text-sm text-zinc-600 dark:text-zinc-400">
          {nameLabel}
          <input
            className="rounded border border-zinc-300 px-2 py-1 text-black dark:border-zinc-700 dark:bg-zinc-900 dark:text-white"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </label>
        <label className="flex flex-col text-sm text-zinc-600 dark:text-zinc-400">
          Start date
          <input
            type="date"
            className="rounded border border-zinc-300 px-2 py-1 text-black dark:border-zinc-700 dark:bg-zinc-900 dark:text-white"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
        </label>
        <label className="flex flex-col text-sm text-zinc-600 dark:text-zinc-400">
          End date
          <input
            type="date"
            className="rounded border border-zinc-300 px-2 py-1 text-black dark:border-zinc-700 dark:bg-zinc-900 dark:text-white"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
          />
        </label>
        <button
          onClick={load}
          disabled={loading}
          className="rounded bg-black px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-black"
        >
          {loading ? "Searching..." : "Search"}
        </button>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="rounded border border-zinc-300 px-3 py-1.5 text-sm font-medium disabled:opacity-50 dark:border-zinc-700"
        >
          {refreshing ? "Refreshing..." : "Refresh from source"}
        </button>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="overflow-x-auto rounded border border-zinc-200 dark:border-zinc-800">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-zinc-100 dark:bg-zinc-900">
            <tr>
              {columns.map((col) => (
                <th key={col.key} className="px-3 py-2 font-medium text-zinc-700 dark:text-zinc-300">
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-t border-zinc-200 dark:border-zinc-800">
                {columns.map((col) => (
                  <td key={col.key} className="px-3 py-2 whitespace-nowrap">
                    {String(row[col.key] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
            {rows.length === 0 && !loading && (
              <tr>
                <td colSpan={columns.length} className="px-3 py-4 text-center text-zinc-500">
                  No data yet — click &quot;Refresh from source&quot; to fetch the latest filings.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
