"use client";

import { WarningCircle } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import PortfolioUpload from "../components/PortfolioUpload";
import RecommendationsView from "../components/RecommendationsView";
import RiskQuestionnaire from "../components/RiskQuestionnaire";
import SnapshotHistory from "../components/SnapshotHistory";
import {
  getLatestSnapshot,
  getRecommendations,
  getRiskProfile,
  isBackendUnreachable,
  PortfolioSnapshot,
  Recommendations,
} from "../lib/portfolioApi";

type View = "loading" | "questionnaire" | "upload" | "recommendations" | "error";

const FOCUS_RING = "focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/50";

export default function RecommendationsPage() {
  const [view, setView] = useState<View>("loading");
  const [snapshot, setSnapshot] = useState<PortfolioSnapshot | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendations | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadEverything = async () => {
    setView("loading");
    setError(null);
    try {
      const [profileResult, snapshotResult] = await Promise.all([getRiskProfile(), getLatestSnapshot()]);
      setSnapshot(snapshotResult);

      if (!profileResult) {
        setView("questionnaire");
        return;
      }
      if (!snapshotResult) {
        setView("upload");
        return;
      }
      const recs = await getRecommendations();
      setRecommendations(recs);
      setView("recommendations");
    } catch (err) {
      setError(isBackendUnreachable(err) ? (err as Error).message : "Something went wrong loading your recommendations.");
      setView("error");
    }
  };

  useEffect(() => {
    loadEverything();
  }, []);

  return (
    <div className="flex flex-1 flex-col">
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-6 py-10">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">Portfolio Recommendations</h1>
          <p className="text-sm leading-relaxed text-muted-foreground">
            A simple, rules-based allocation check against your risk profile — not a live brokerage connection.
          </p>
        </div>

        {view === "loading" && (
          <div className="flex flex-col gap-3">
            <div className="h-32 animate-pulse rounded-xl bg-muted" />
            <div className="h-32 animate-pulse rounded-xl bg-muted" />
          </div>
        )}

        {view === "error" && (
          <div className="flex items-center gap-2 rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            <WarningCircle size={18} aria-hidden="true" />
            <span>{error}</span>
          </div>
        )}

        {view === "questionnaire" && <RiskQuestionnaire onSaved={loadEverything} />}

        {view === "upload" && <PortfolioUpload onSaved={loadEverything} />}

        {view === "recommendations" && recommendations && (
          <>
            <RecommendationsView data={recommendations} />
            <div className="flex flex-wrap gap-3 border-t border-border pt-4">
              <button
                onClick={() => setView("questionnaire")}
                className={`cursor-pointer rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted ${FOCUS_RING}`}
              >
                Retake questionnaire
              </button>
              <button
                onClick={() => setView("upload")}
                className={`cursor-pointer rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted ${FOCUS_RING}`}
              >
                Upload new screenshot
              </button>
            </div>
            {snapshot && (
              <p className="text-xs text-muted-foreground/70">
                Based on a snapshot uploaded {new Date(snapshot.uploaded_at).toLocaleString()} — not live-updating.
              </p>
            )}
            <SnapshotHistory />
          </>
        )}
      </main>
    </div>
  );
}
