"""Parses a portfolio screenshot into structured holdings via Claude's vision
API. This is Product 2's only ML-derived data source in the whole app — the
output is NEVER written to storage directly. app/routers/portfolio.py returns
it to the frontend for the user to review/correct, and only a user-confirmed
payload reaches db.save_portfolio_snapshot — same "don't trust extraction
straight into storage" principle used for source-verification elsewhere.
"""

import base64

import anthropic
from pydantic import BaseModel, Field

from app.config import ANTHROPIC_API_KEY

MODEL = "claude-opus-5"

EXTRACTION_PROMPT = (
    "This is a screenshot of a brokerage/investment app showing a portfolio's holdings. "
    "Extract every individual position visible: its ticker symbol, number of shares (if "
    "shown), and current dollar market value (if shown). If a field isn't visible for a "
    "position, leave it null rather than guessing at a number. Ignore totals/summary rows "
    "and anything that isn't an individual holding. For uninvested cash, a money-market "
    "sweep fund, or any settlement/cash balance line, use the ticker \"CASH\" rather than "
    "leaving it blank — do not omit it."
)


class ExtractedHolding(BaseModel):
    ticker: str
    shares: float | None = Field(None, ge=0)
    value: float | None = Field(None, ge=0)


class ExtractedHoldings(BaseModel):
    holdings: list[ExtractedHolding]


class VisionNotConfiguredError(Exception):
    """Raised when ANTHROPIC_API_KEY isn't set — a router-level 503, not a crash."""


def extract_holdings_from_image(image_bytes: bytes, media_type: str) -> list[dict]:
    if not ANTHROPIC_API_KEY:
        raise VisionNotConfiguredError("ANTHROPIC_API_KEY is not set — add it to .env to use screenshot upload.")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    image_data = base64.standard_b64encode(image_bytes).decode("utf-8")

    response = client.messages.parse(
        model=MODEL,
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
                {"type": "text", "text": EXTRACTION_PROMPT},
            ],
        }],
        output_format=ExtractedHoldings,
    )
    return [h.model_dump() for h in response.parsed_output.holdings]
