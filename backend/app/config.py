import os

from dotenv import load_dotenv

load_dotenv()

SEC_EDGAR_CONTACT_EMAIL = os.getenv("SEC_EDGAR_CONTACT_EMAIL", "").strip()

if not SEC_EDGAR_CONTACT_EMAIL:
    raise RuntimeError(
        "SEC_EDGAR_CONTACT_EMAIL must be set in .env — SEC's fair-access policy "
        "requires a real contact email in the User-Agent header of automated requests."
    )

SEC_USER_AGENT = f"Stocks personal project ({SEC_EDGAR_CONTACT_EMAIL})"

HOUSE_CLERK_USER_AGENT = "Mozilla/5.0 (compatible; StocksPersonalProject/1.0)"

DB_PATH = os.getenv("STOCKS_DB_PATH", "stocks.db")

# Comma-separated list of allowed frontend origins for CORS. Defaults to local
# dev; set this in production (e.g. Railway) to the deployed frontend's URL.
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

# Optional — unlike SEC_EDGAR_CONTACT_EMAIL above, the rest of the app must keep
# working without this. Only required by Senate trade tracking, which checks
# at call time and reports a clear error rather than failing app startup.
FMP_API_KEY = os.getenv("FMP_API_KEY", "").strip()
