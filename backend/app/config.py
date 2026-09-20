import os

from dotenv import load_dotenv

load_dotenv()

SEC_EDGAR_CONTACT_EMAIL = os.getenv("SEC_EDGAR_CONTACT_EMAIL", "").strip()

if not SEC_EDGAR_CONTACT_EMAIL:
    raise RuntimeError(
        "SEC_EDGAR_CONTACT_EMAIL must be set in .env — SEC's fair-access policy "
        "requires a real contact email in the User-Agent header of automated requests."
    )

SEC_USER_AGENT = f"ToTheMoon personal project ({SEC_EDGAR_CONTACT_EMAIL})"

HOUSE_CLERK_USER_AGENT = "Mozilla/5.0 (compatible; ToTheMoonPersonalProject/1.0)"

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

# Shared secret gating the three /refresh endpoints and /api/status (see app/auth.py).
# Leaving this unset doesn't skip a feature — it locks those endpoints, since
# require_admin_key always rejects with 401 when this is empty.
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "").strip()

# Same Clerk publishable key the frontend uses (NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) —
# needed here too so app/auth_clerk.py can derive Clerk's Frontend API host (and
# therefore its JWKS URL) to verify session tokens. Optional at the config level
# (this app ran fine with zero user concept before the watchlist feature); checked
# at call time in auth_clerk.py instead of failing startup like SEC_EDGAR_CONTACT_EMAIL.
CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY", "").strip()

# Resend (resend.com) — sends watchlist-alert emails. Optional; app/notifications/email.py
# logs and skips sending rather than raising when unset, same pattern as FMP_API_KEY.
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "").strip()
