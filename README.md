# Stocks

A personal investing platform, built in three parts:

1. **Trade tracker** — corporate insider trades (SEC Form 4), institutional 13F filings, and congressional trades, shown as three separate categories.
2. **Portfolio recommendation bot** — recommends stocks/ETFs and allocation percentages based on your risk/diversification/sector preferences and your current holdings (via Alpaca connection or screenshot upload).
3. **Auto-trading bot** — paper-trades via Alpaca based on the outputs of parts 1 and 2.

Built one part at a time. Part 1 is in progress.

## Stack
- `frontend/` — Next.js (TypeScript)
- `backend/` — FastAPI (Python)

## Setup
See `.env.example` for required environment variables. Copy it to `.env` and fill in real values locally — `.env` is git-ignored and should never be committed.
