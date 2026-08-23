from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel, Field, field_validator

from app.db import (
    get_latest_portfolio_snapshot,
    get_risk_profile,
    save_portfolio_snapshot,
    save_risk_profile,
)
from app.portfolio_engine import compute_recommendations, derive_target_allocation
from app.sources.portfolio_vision import VisionNotConfiguredError, extract_holdings_from_image

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

ACCEPTED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}


class HoldingInput(BaseModel):
    ticker: str
    shares: float | None = Field(None, ge=0)
    value: float | None = Field(None, ge=0)

    @field_validator("ticker")
    @classmethod
    def ticker_must_be_non_empty(cls, v: str) -> str:
        trimmed = v.strip().upper()
        if not trimmed:
            raise ValueError("ticker must not be empty")
        return trimmed


class RiskProfileInput(BaseModel):
    time_horizon: str | None = None
    risk_tolerance: str  # "conservative" | "moderate" | "aggressive"
    primary_goal: str | None = None


@router.post("/upload")
async def upload_screenshot(file: UploadFile):
    """Parses a portfolio screenshot into holdings for the user to review —
    does NOT save anything. Call POST /snapshots with the (possibly corrected)
    result to actually store it."""
    content_type = file.content_type or ""
    if content_type not in ACCEPTED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported image type: {content_type or 'unknown'}")

    image_bytes = await file.read()
    try:
        holdings = extract_holdings_from_image(image_bytes, content_type)
    except VisionNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {"holdings": holdings}


@router.post("/snapshots")
def create_snapshot(holdings: list[HoldingInput]):
    snapshot_id = save_portfolio_snapshot([h.model_dump() for h in holdings])
    return {"id": snapshot_id}


@router.get("/latest")
def latest_snapshot():
    snapshot = get_latest_portfolio_snapshot()
    if not snapshot:
        raise HTTPException(status_code=404, detail="No portfolio snapshot saved yet.")
    return snapshot


@router.get("/risk-profile")
def read_risk_profile():
    return get_risk_profile()


@router.post("/risk-profile")
def write_risk_profile(payload: RiskProfileInput):
    target = derive_target_allocation(payload.risk_tolerance, payload.time_horizon)
    save_risk_profile(
        time_horizon=payload.time_horizon,
        risk_tolerance=payload.risk_tolerance,
        primary_goal=payload.primary_goal,
        target_stock_pct=target["stock"],
        target_bond_pct=target["bond"],
        target_cash_pct=target["cash"],
    )
    return get_risk_profile()


@router.get("/recommendations")
def recommendations():
    snapshot = get_latest_portfolio_snapshot()
    profile = get_risk_profile()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Upload a portfolio screenshot first.")
    if not profile:
        raise HTTPException(status_code=404, detail="Complete the risk questionnaire first.")
    return compute_recommendations(
        snapshot["holdings"],
        profile["risk_tolerance"],
        profile.get("time_horizon"),
        profile.get("primary_goal"),
    )
