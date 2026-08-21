"""Static ticker -> {asset_class, sector} reference data for the portfolio
recommendation engine (Product 2). Deliberately NOT a live market-data lookup —
v1 works off this bundled table, with anything not listed reported as
"Unclassified" rather than guessed (see get_ticker_info below).

asset_class is one of: "stock", "bond", "cash", "alternative" (commodities/crypto
funds — these don't fit a stock/bond/cash split honestly, so they get their own
bucket rather than being force-classified as equity).

Covers ~180 common large-cap stocks and popular ETFs. Expand as needed when a
real portfolio screenshot surfaces a ticker not in here.
"""

TICKER_REFERENCE: dict[str, dict[str, str]] = {}


def _add(asset_class: str, sector: str, *tickers: str) -> None:
    for ticker in tickers:
        TICKER_REFERENCE[ticker] = {"asset_class": asset_class, "sector": sector}


# --- Individual stocks, by sector ---
_add("stock", "Technology",
     "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "AVGO", "ORCL", "CRM",
     "ADBE", "INTC", "AMD", "CSCO", "IBM", "QCOM", "TXN", "NOW", "INTU", "AMAT",
     "MU", "PANW", "SNPS", "CDNS", "ANET", "LRCX", "KLAC", "ADI", "MRVL", "DELL", "HPQ")
_add("stock", "Communication Services",
     "NFLX", "DIS", "CMCSA", "T", "VZ", "TMUS", "WBD", "EA", "TTWO", "PINS", "SNAP")
_add("stock", "Financials",
     "JPM", "BAC", "WFC", "C", "GS", "MS", "SCHW", "BLK", "AXP", "V", "MA", "PYPL",
     "SPGI", "ICE", "CME", "USB", "PNC", "TFC", "COF", "AIG", "MET", "PRU", "ALL")
_add("stock", "Healthcare",
     "UNH", "JNJ", "LLY", "ABBV", "MRK", "PFE", "TMO", "ABT", "DHR", "BMY", "AMGN",
     "GILD", "CVS", "CI", "ISRG", "VRTX", "REGN", "MDT", "SYK", "BSX", "HUM", "ELV", "ZTS")
_add("stock", "Consumer Discretionary",
     "TSLA", "HD", "MCD", "NKE", "SBUX", "LOW", "TJX", "BKNG", "TGT", "MAR", "GM",
     "F", "CMG", "ORLY", "ROST", "YUM", "EBAY", "ETSY", "ABNB", "UBER", "LYFT")
_add("stock", "Consumer Staples",
     "PG", "KO", "PEP", "WMT", "COST", "PM", "MO", "MDLZ", "CL", "KMB", "GIS",
     "KHC", "STZ", "KR", "SYY", "ADM")
_add("stock", "Industrials",
     "BA", "CAT", "HON", "UPS", "RTX", "LMT", "GE", "DE", "UNP", "MMM", "NOC",
     "GD", "EMR", "ETN", "FDX", "CSX", "NSC", "WM", "ITW")
_add("stock", "Energy",
     "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "WMB", "KMI")
_add("stock", "Utilities",
     "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "ED", "WEC")
_add("stock", "Real Estate",
     "AMT", "PLD", "CCI", "EQIX", "PSA", "O", "SPG", "DLR", "WELL", "AVB")
_add("stock", "Materials",
     "LIN", "APD", "SHW", "ECL", "FCX", "NEM", "DOW", "DD", "PPG")

# --- Broad-market equity ETFs ---
_add("stock", "US Broad Market",
     "SPY", "VOO", "IVV", "VTI", "QQQ", "DIA", "IWM", "VUG", "VTV", "SCHX",
     "IJH", "IJR", "MDY", "SCHD", "VYM", "VIG", "DVY", "SCHB")
_add("stock", "International Equity",
     "VEA", "VWO", "VXUS", "EFA", "IEMG", "EEM", "IXUS", "SCHF")

# --- Sector equity ETFs ---
_add("stock", "Technology", "XLK", "VGT", "SMH", "SOXX")
_add("stock", "Financials", "XLF", "VFH")
_add("stock", "Healthcare", "XLV", "VHT")
_add("stock", "Energy", "XLE", "VDE")
_add("stock", "Consumer Discretionary", "XLY", "VCR")
_add("stock", "Consumer Staples", "XLP", "VDC")
_add("stock", "Industrials", "XLI", "VIS")
_add("stock", "Utilities", "XLU", "VPU")
_add("stock", "Real Estate", "XLRE", "VNQ")
_add("stock", "Materials", "XLB", "VAW")
_add("stock", "Communication Services", "XLC", "VOX")

# --- Bond ETFs ---
_add("bond", "Aggregate/Broad Bond", "BND", "AGG", "BNDX", "SCHZ")
_add("bond", "Treasury", "TLT", "IEF", "SHY", "GOVT", "VGIT", "VGSH", "VGLT")
_add("bond", "Corporate Bond", "LQD", "VCIT", "VCSH", "VCLT")
_add("bond", "High Yield", "HYG", "JNK", "SHYG")
_add("bond", "Municipal", "MUB", "VTEB")
_add("bond", "TIPS", "TIP", "SCHP", "VTIP")

# --- Cash-equivalent ---
_add("cash", "Cash & Equivalents", "BIL", "SGOV", "SHV", "VMFXX", "SPAXX", "CASH")

# --- Alternatives (commodities, crypto) ---
_add("alternative", "Precious Metals", "GLD", "IAU", "SLV", "GLDM")
_add("alternative", "Cryptocurrency", "IBIT", "FBTC", "GBTC", "ETHE", "BITO")
_add("alternative", "Commodities (Broad)", "DBC", "PDBC", "GSG")


def get_ticker_info(ticker: str) -> dict[str, str]:
    """Looks up a ticker's asset class + sector. Anything not in the bundled
    reference returns "Unclassified" for both fields rather than a guess —
    honesty about coverage gaps matters more than a plausible-looking default."""
    ticker = (ticker or "").strip().upper()
    return TICKER_REFERENCE.get(ticker, {"asset_class": "Unclassified", "sector": "Unclassified"})
