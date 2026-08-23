"use client";

import { Plus, Trash, UploadSimple, WarningCircle } from "@phosphor-icons/react";
import { useRef, useState } from "react";
import { Holding, saveSnapshot, uploadScreenshot, VisionNotConfiguredError } from "../lib/portfolioApi";

const FOCUS_RING = "focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/50";

interface PortfolioUploadProps {
  onSaved: () => void;
}

function emptyHolding(): Holding {
  return { ticker: "", shares: null, value: null };
}

export default function PortfolioUpload({ onSaved }: PortfolioUploadProps) {
  const [holdings, setHoldings] = useState<Holding[] | null>(null);
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [visionUnavailable, setVisionUnavailable] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (file: File | undefined) => {
    if (!file) return;
    setUploading(true);
    setError(null);
    setVisionUnavailable(null);
    try {
      const extracted = await uploadScreenshot(file);
      setHoldings(extracted.length > 0 ? extracted : [emptyHolding()]);
    } catch (err) {
      if (err instanceof VisionNotConfiguredError) {
        setVisionUnavailable(err.message);
      } else {
        setError("Couldn't read that screenshot — try again, or enter holdings manually below.");
      }
    } finally {
      setUploading(false);
    }
  };

  const startManualEntry = () => setHoldings([emptyHolding()]);

  const updateHolding = (i: number, patch: Partial<Holding>) => {
    setHoldings((prev) => (prev ? prev.map((h, idx) => (idx === i ? { ...h, ...patch } : h)) : prev));
  };

  const removeHolding = (i: number) => {
    setHoldings((prev) => (prev ? prev.filter((_, idx) => idx !== i) : prev));
  };

  const addHolding = () => setHoldings((prev) => [...(prev ?? []), emptyHolding()]);

  const missingTickerCount = holdings?.filter((h) => h.ticker.trim() === "").length ?? 0;
  const hasNegativeValue = holdings?.some((h) => (h.shares ?? 0) < 0 || (h.value ?? 0) < 0) ?? false;

  const handleSave = async () => {
    if (!holdings) return;
    if (hasNegativeValue) {
      setError("Shares and value can't be negative — fix the highlighted row(s) below.");
      return;
    }
    const valid = holdings.filter((h) => h.ticker.trim() !== "");
    if (valid.length === 0) {
      setError("Add at least one holding with a ticker before saving.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await saveSnapshot(valid);
      onSaved();
    } catch {
      setError("Couldn't save your holdings — try again.");
    } finally {
      setSaving(false);
    }
  };

  if (holdings) {
    return (
      <div className="flex flex-col gap-4 rounded-xl border border-border bg-card p-6">
        <div className="flex flex-col gap-1">
          <h2 className="text-lg font-semibold text-card-foreground">Review your holdings</h2>
          <p className="text-sm text-muted-foreground">
            Check this against your actual portfolio and correct anything that&apos;s off before saving — nothing is stored until you confirm.
          </p>
        </div>

        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-muted">
              <tr>
                <th className="px-3 py-2 font-medium text-muted-foreground">Ticker</th>
                <th className="px-3 py-2 font-medium text-muted-foreground">Shares</th>
                <th className="px-3 py-2 font-medium text-muted-foreground">Value ($)</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              {holdings.map((h, i) => (
                <tr key={i} className="border-t border-border">
                  <td className="px-3 py-2">
                    <input
                      value={h.ticker}
                      onChange={(e) => updateHolding(i, { ticker: e.target.value.toUpperCase() })}
                      placeholder="AAPL or CASH"
                      className={`w-28 rounded-md border bg-card px-2 py-1.5 font-mono text-sm text-card-foreground outline-none focus:border-accent ${FOCUS_RING} ${
                        h.ticker.trim() === "" ? "border-warning" : "border-border"
                      }`}
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="number"
                      min="0"
                      value={h.shares ?? ""}
                      onChange={(e) => updateHolding(i, { shares: e.target.value === "" ? null : Number(e.target.value) })}
                      className={`w-24 rounded-md border bg-card px-2 py-1.5 font-mono text-sm text-card-foreground outline-none focus:border-accent ${FOCUS_RING} ${
                        (h.shares ?? 0) < 0 ? "border-destructive" : "border-border"
                      }`}
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="number"
                      min="0"
                      value={h.value ?? ""}
                      onChange={(e) => updateHolding(i, { value: e.target.value === "" ? null : Number(e.target.value) })}
                      className={`w-28 rounded-md border bg-card px-2 py-1.5 font-mono text-sm text-card-foreground outline-none focus:border-accent ${FOCUS_RING} ${
                        (h.value ?? 0) < 0 ? "border-destructive" : "border-border"
                      }`}
                    />
                  </td>
                  <td className="px-3 py-2">
                    <button
                      onClick={() => removeHolding(i)}
                      aria-label="Remove holding"
                      className={`flex h-7 w-7 cursor-pointer items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-destructive ${FOCUS_RING}`}
                    >
                      <Trash size={14} aria-hidden="true" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <button
          onClick={addHolding}
          className={`flex w-fit cursor-pointer items-center gap-1.5 text-sm font-medium text-accent hover:underline ${FOCUS_RING} rounded`}
        >
          <Plus size={14} aria-hidden="true" />
          Add holding
        </button>

        {missingTickerCount > 0 && (
          <div className="flex items-start gap-2 rounded-lg border border-warning/40 bg-warning/10 px-4 py-3 text-sm text-warning">
            <WarningCircle size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
            <span>
              {missingTickerCount === 1 ? "1 row is" : `${missingTickerCount} rows are`} missing a ticker and won&apos;t be
              saved. Add one (use &quot;CASH&quot; for uninvested cash) or remove the row.
            </span>
          </div>
        )}

        {error && <p className="text-sm text-destructive">{error}</p>}

        <div className="flex gap-3">
          <button
            onClick={handleSave}
            disabled={saving}
            className={`cursor-pointer rounded-lg bg-accent px-5 py-2.5 text-sm font-medium text-on-accent transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50 ${FOCUS_RING}`}
          >
            {saving ? "Saving…" : "Confirm & Save"}
          </button>
          <button
            onClick={() => setHoldings(null)}
            className={`cursor-pointer rounded-lg border border-border px-5 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-muted ${FOCUS_RING}`}
          >
            Start over
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 rounded-xl border border-border bg-card p-6">
      <div className="flex flex-col gap-1">
        <h2 className="text-lg font-semibold text-card-foreground">Upload your holdings</h2>
        <p className="text-sm text-muted-foreground">
          Upload a screenshot of your portfolio (from any broker app) and it&apos;ll be read into a holdings list you can review before saving.
          This is a snapshot at upload time, not a live-updating connection.
        </p>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/png,image/jpeg,image/webp,image/gif"
        className="hidden"
        onChange={(e) => handleFileChange(e.target.files?.[0])}
      />
      <button
        onClick={() => fileInputRef.current?.click()}
        disabled={uploading}
        className={`flex items-center justify-center gap-2 rounded-lg border border-dashed border-border px-6 py-8 text-sm font-medium text-muted-foreground transition-colors hover:border-accent hover:text-foreground disabled:cursor-not-allowed disabled:opacity-50 ${FOCUS_RING}`}
      >
        <UploadSimple size={18} aria-hidden="true" />
        {uploading ? "Reading screenshot…" : "Choose a screenshot"}
      </button>

      {visionUnavailable && (
        <div className="flex items-start gap-2 rounded-lg border border-warning/40 bg-warning/10 px-4 py-3 text-sm text-warning">
          <WarningCircle size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
          <span>{visionUnavailable}</span>
        </div>
      )}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          <WarningCircle size={16} aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}

      <button
        onClick={startManualEntry}
        className={`self-start text-sm font-medium text-accent hover:underline ${FOCUS_RING} rounded`}
      >
        Or enter holdings manually
      </button>
    </div>
  );
}
