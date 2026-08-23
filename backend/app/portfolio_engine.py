"""Pure recommendation logic for Product 2 (Portfolio Recommendations) — v1 is
a simple rules-based allocator, not a portfolio optimizer. No live market data:
everything here works off the dollar values a holdings snapshot already carries
(as extracted from a user-confirmed screenshot upload), not a live price feed.
"""

from app.data.ticker_reference import get_ticker_info

# Preset target allocations by risk tolerance — the starting point before the
# time_horizon tilt below is applied.
RISK_PROFILES: dict[str, dict[str, float]] = {
    "conservative": {"stock": 30.0, "bond": 60.0, "cash": 10.0},
    "moderate": {"stock": 60.0, "bond": 30.0, "cash": 10.0},
    "aggressive": {"stock": 90.0, "bond": 10.0, "cash": 0.0},
}

# A standard glide-path heuristic: a shorter time horizon means less time to
# recover from a downturn, so it nudges the target toward bonds regardless of
# stated risk tolerance; a longer horizon nudges toward stock. "5-15 years" is
# treated as neutral (no tilt) — it's the baseline the presets above already model.
TIME_HORIZON_TILT_PCT = 10.0

# Only recommend a shift if the gap between current and target exceeds this —
# avoids noisy suggestions over a 1-2 point difference that isn't meaningful.
GAP_THRESHOLD_PCT = 10.0

# A stock-sector's share of total equity value above this is flagged as concentrated.
SECTOR_CONCENTRATION_THRESHOLD_PCT = 30.0

# Generic, representative low-cost index funds per asset class, tilted by stated
# primary goal — not personalized stock-picking, just a plain-language starting
# point for an underweight bucket. "growth" is the fallback for an unrecognized
# or missing goal.
SUGGESTED_FUNDS: dict[str, dict[str, list[str]]] = {
    "stock": {
        "growth": ["VTI (Vanguard Total Stock Market ETF)", "VOO (Vanguard S&P 500 ETF)"],
        "income": ["SCHD (Schwab US Dividend Equity ETF)", "VYM (Vanguard High Dividend Yield ETF)"],
        "capital preservation": ["SCHD (Schwab US Dividend Equity ETF)", "VTI (Vanguard Total Stock Market ETF)"],
    },
    "bond": {
        "growth": ["BND (Vanguard Total Bond Market ETF)", "AGG (iShares Core U.S. Aggregate Bond ETF)"],
        "income": ["HYG (iShares iBoxx $ High Yield Corporate Bond ETF)", "AGG (iShares Core U.S. Aggregate Bond ETF)"],
        "capital preservation": ["SHY (iShares 1-3 Year Treasury Bond ETF)", "BND (Vanguard Total Bond Market ETF)"],
    },
    "cash": {
        "growth": ["SGOV (iShares 0-3 Month Treasury Bond ETF)", "a high-yield savings account or money market fund"],
        "income": ["SGOV (iShares 0-3 Month Treasury Bond ETF)", "a high-yield savings account or money market fund"],
        "capital preservation": ["SGOV (iShares 0-3 Month Treasury Bond ETF)", "a high-yield savings account or money market fund"],
    },
}


def _apply_time_horizon_tilt(base: dict[str, float], time_horizon: str | None) -> dict[str, float]:
    horizon = (time_horizon or "").strip().lower()
    if horizon.startswith("under"):
        tilt = -TIME_HORIZON_TILT_PCT
    elif "15+" in horizon or "15 +" in horizon:
        tilt = TIME_HORIZON_TILT_PCT
    else:
        return dict(base)

    cash = base["cash"]
    bond = min(max(base["bond"] - tilt, 0.0), 100.0 - cash)
    stock = 100.0 - bond - cash
    return {"stock": round(stock, 1), "bond": round(bond, 1), "cash": round(cash, 1)}


def derive_target_allocation(risk_tolerance: str, time_horizon: str | None = None) -> dict[str, float]:
    """Maps a risk-tolerance preset to a target stock/bond/cash split, then
    tilts it by time horizon (see _apply_time_horizon_tilt). Falls back to
    "moderate" for an unrecognized risk_tolerance rather than erroring — a
    bad/missing profile shouldn't break the recommendations view."""
    base = RISK_PROFILES.get(risk_tolerance, RISK_PROFILES["moderate"])
    return _apply_time_horizon_tilt(base, time_horizon)


def _funds_for(asset_class: str, primary_goal: str | None) -> list[str]:
    by_goal = SUGGESTED_FUNDS.get(asset_class, {})
    goal_key = (primary_goal or "growth").strip().lower()
    return by_goal.get(goal_key, by_goal.get("growth", []))


def compute_allocation(holdings: list[dict]) -> dict:
    """Groups holdings by asset_class (stock/bond/cash/alternative/Unclassified)
    and, within stocks, by sector — using the bundled ticker reference, not a
    live lookup. Returns dollar totals and percentages for each."""
    total_value = sum(h.get("value") or 0 for h in holdings)

    by_asset_class: dict[str, float] = {}
    by_sector: dict[str, float] = {}
    equity_value = 0.0

    for h in holdings:
        value = h.get("value") or 0
        info = get_ticker_info(str(h.get("ticker", "")))
        asset_class = info["asset_class"]
        by_asset_class[asset_class] = by_asset_class.get(asset_class, 0) + value
        if asset_class == "stock":
            sector = info["sector"]
            by_sector[sector] = by_sector.get(sector, 0) + value
            equity_value += value

    def pct(value: float, of: float) -> float:
        return round((value / of) * 100, 1) if of else 0.0

    return {
        "total_value": total_value,
        "asset_class": {k: {"value": v, "pct": pct(v, total_value)} for k, v in by_asset_class.items()},
        "sector": {k: {"value": v, "pct": pct(v, equity_value)} for k, v in by_sector.items()},
        "equity_value": equity_value,
    }


def compute_recommendations(
    holdings: list[dict],
    risk_tolerance: str,
    time_horizon: str | None = None,
    primary_goal: str | None = None,
) -> dict:
    """Diffs the current allocation (from `holdings`) against the target for
    `risk_tolerance` (tilted by `time_horizon`), returning plain-language gap
    suggestions (funds tilted by `primary_goal`) and sector concentration
    flags. Pure function — no I/O — so it's directly testable."""
    target = derive_target_allocation(risk_tolerance, time_horizon)
    allocation = compute_allocation(holdings)
    current_pct = {k: v["pct"] for k, v in allocation["asset_class"].items()}

    asset_class_plural = {"stock": "stocks", "bond": "bonds", "cash": "cash"}

    gaps = []
    for asset_class in ("stock", "bond", "cash"):
        current = current_pct.get(asset_class, 0.0)
        target_pct = target[asset_class]
        diff = round(current - target_pct, 1)
        if abs(diff) >= GAP_THRESHOLD_PCT:
            direction = "overweight" if diff > 0 else "underweight"
            gaps.append({
                "asset_class": asset_class,
                "current_pct": current,
                "target_pct": target_pct,
                "diff_pct": diff,
                "direction": direction,
                "message": (
                    f"You're {abs(diff):.0f} points {direction} {asset_class_plural[asset_class]} "
                    f"({current:.0f}% vs. your {target_pct:.0f}% target)."
                ),
                "suggested_funds": _funds_for(asset_class, primary_goal) if direction == "underweight" else [],
            })

    sector_flags = []
    for sector, info in allocation["sector"].items():
        if sector != "Unclassified" and info["pct"] >= SECTOR_CONCENTRATION_THRESHOLD_PCT:
            sector_flags.append({
                "sector": sector,
                "pct": info["pct"],
                "message": f"{sector} is {info['pct']:.0f}% of your equity holdings — consider diversifying.",
            })
    sector_flags.sort(key=lambda f: f["pct"], reverse=True)

    return {
        "allocation": allocation,
        "target": target,
        "gaps": gaps,
        "sector_flags": sector_flags,
    }
