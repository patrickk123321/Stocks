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

# Optional — unlike SEC_EDGAR_CONTACT_EMAIL above, the rest of the app must keep
# working without these. Each is only required by the specific feature that
# needs it (Senate trade tracking / portfolio screenshot parsing), which checks
# at call time and reports a clear error rather than failing app startup.
FMP_API_KEY = os.getenv("FMP_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
