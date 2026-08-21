"use client";

import { useState } from "react";
import { RiskProfileInput, RiskTolerance, saveRiskProfile } from "../lib/portfolioApi";

const FOCUS_RING = "focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/50";

const RISK_OPTIONS: { value: RiskTolerance; label: string; description: string }[] = [
  { value: "conservative", label: "Conservative", description: "Prioritize protecting what you have (~30% stocks / 60% bonds / 10% cash)." },
  { value: "moderate", label: "Moderate", description: "Balance growth and stability (~60% stocks / 30% bonds / 10% cash)." },
  { value: "aggressive", label: "Aggressive", description: "Prioritize long-term growth (~90% stocks / 10% bonds)." },
];

const TIME_HORIZONS = ["Under 5 years", "5–15 years", "15+ years"];
const GOALS = ["Growth", "Income", "Capital preservation"];

interface RiskQuestionnaireProps {
  onSaved: () => void;
}

export default function RiskQuestionnaire({ onSaved }: RiskQuestionnaireProps) {
  const [riskTolerance, setRiskTolerance] = useState<RiskTolerance | null>(null);
  const [timeHorizon, setTimeHorizon] = useState<string>(TIME_HORIZONS[1]);
  const [primaryGoal, setPrimaryGoal] = useState<string>(GOALS[0]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!riskTolerance) return;
    setSaving(true);
    setError(null);
    try {
      const input: RiskProfileInput = { risk_tolerance: riskTolerance, time_horizon: timeHorizon, primary_goal: primaryGoal };
      await saveRiskProfile(input);
      onSaved();
    } catch {
      setError("Couldn't save your risk profile — try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 rounded-xl border border-border bg-card p-6">
      <div className="flex flex-col gap-1">
        <h2 className="text-lg font-semibold text-card-foreground">A few quick questions</h2>
        <p className="text-sm text-muted-foreground">
          This sets your target allocation — a starting point for the recommendations, not a locked-in plan. You can retake this any time.
        </p>
      </div>

      <div className="flex flex-col gap-2">
        <p className="text-sm font-medium text-card-foreground">How would you describe your risk tolerance?</p>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          {RISK_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setRiskTolerance(opt.value)}
              className={`flex flex-col gap-1 rounded-lg border px-4 py-3 text-left transition-colors ${FOCUS_RING} ${
                riskTolerance === opt.value ? "border-accent bg-accent/10" : "border-border hover:bg-muted"
              }`}
            >
              <span className="text-sm font-semibold text-card-foreground">{opt.label}</span>
              <span className="text-xs leading-relaxed text-muted-foreground">{opt.description}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium text-card-foreground">Time horizon</span>
          <select
            value={timeHorizon}
            onChange={(e) => setTimeHorizon(e.target.value)}
            className={`rounded-lg border border-border bg-card px-3 py-2 text-sm text-card-foreground outline-none focus:border-accent ${FOCUS_RING}`}
          >
            {TIME_HORIZONS.map((h) => (
              <option key={h} value={h}>{h}</option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium text-card-foreground">Primary goal</span>
          <select
            value={primaryGoal}
            onChange={(e) => setPrimaryGoal(e.target.value)}
            className={`rounded-lg border border-border bg-card px-3 py-2 text-sm text-card-foreground outline-none focus:border-accent ${FOCUS_RING}`}
          >
            {GOALS.map((g) => (
              <option key={g} value={g}>{g}</option>
            ))}
          </select>
        </label>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <button
        onClick={handleSubmit}
        disabled={!riskTolerance || saving}
        className={`self-start cursor-pointer rounded-lg bg-accent px-5 py-2.5 text-sm font-medium text-on-accent transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50 ${FOCUS_RING}`}
      >
        {saving ? "Saving…" : "Continue"}
      </button>
    </div>
  );
}
