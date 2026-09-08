# Pelo$i

A personal investing platform: track corporate insider trades (SEC Form 4), institutional 13F filings, and congressional trades, shown as three searchable, filterable categories with a dashboard of the most recent activity.

Insider trades refresh twice daily (9:00 AM and 9:00 PM Eastern); institutional and congressional data refresh once daily. US-only for now — Canadian insider-trading data (SEDI) has no bulk/discovery API, only per-issuer search, and the paid third-party alternatives found weren't worth it yet; revisit if a viable free/cheap source turns up.

## Stack
- `frontend/` — Next.js (TypeScript)
- `backend/` — FastAPI (Python)

## Setup
See `.env.example` for required environment variables. Copy it to `.env` and fill in real values locally — `.env` is git-ignored and should never be committed.
