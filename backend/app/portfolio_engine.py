"""Pure recommendation logic for Product 2 (Portfolio Recommendations) — v1 is
a simple rules-based allocator, not a portfolio optimizer. No live market data:
everything here works off the dollar values a holdings snapshot already carries
(as extracted from a user-confirmed screenshot upload), not a live price feed.
"""

from app.data.ticker_reference import get_ticker_info

# Preset target allocations by risk tolerance. This is deliberately simple for
# v1: time_horizon and primary_goal are collected and stored (see db.risk_profile)
# for future refinement, but only risk_tolerance drives the target allocation
# right now — a documented v1 simplification, not an oversight.
RISK_PROFILES: dict[str, dict[str, float]] = {
    "conservative": {"stock": 30.0, "bond": 60.0, "cash": 10.0},
    "moderate": {"stock": 60.0, "bond": 30.0, "cash": 10.0},
    "aggressive": {"stock": 90.0, "bond": 10.0, "cash": 0.0},
}

# Only recommend a shift if the gap between current and target exceeds this —
# avoids noisy suggestions over a 1-2 point difference that isn't meaningful.
GAP_THRESHOLD_PCT = 10.0

# A stock-sector's share of total equity value above this is flagged as concentrated.
SECTOR_CONCENTRATION_THRESHOLD_PCT = 30.0

# Generic, representative low-cost index funds per asset class — not personalized
# stock-picking, just a plain-language starting point for an underweight bucket.
SUGGESTED_FUNDS = {
    "stock": ["VTI (Vanguard Total Stock Market ETF)", "VOO (Vanguard S&P 500 ETF)"],
    "bond": ["BND (Vanguard Total Bond Market ETF)", "AGG (iShares Core U.S. Aggregate Bond ETF)"],
    "cash": ["SGOV (iShares 0-3 Month Treasury Bond ETF)", "a high-yield savings account or money market fund"],
}


def derive_target_allocation(risk_tolerance: str) -> dict[str, float]:
    """Maps a risk-tolerance preset to a target stock/bond/cash split. Falls back
    to "moderate" for an unrecognized value rather than erroring — a bad/missing
    profile shouldn't break the recommendations view."""
    return RISK_PROFILES.get(risk_tolerance, RISK_PROFILES["moderate"])


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


def compute_recommendations(holdings: list[dict], risk_tolerance: str) -> dict:
    """Diffs the current allocation (from `holdings`) against the target for
    `risk_tolerance`, returning plain-language gap suggestions and sector
    concentration flags. Pure function — no I/O — so it's directly testable."""
    target = derive_target_allocation(risk_tolerance)
    allocation = compute_allocation(holdings)
    current_pct = {k: v["pct"] for k, v in allocation["asset_class"].items()}

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
                    f"You're {abs(diff):.0f} points {direction} {asset_class}s "
                    f"({current:.0f}% vs. your {target_pct:.0f}% target)."
                ),
                "suggested_funds": SUGGESTED_FUNDS.get(asset_class, []) if direction == "underweight" else [],
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
