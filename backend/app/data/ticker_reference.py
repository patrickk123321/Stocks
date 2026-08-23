"""Static ticker -> {asset_class, sector} reference data for the portfolio
recommendation engine (Product 2). Deliberately NOT a live market-data lookup —
v1 works off this bundled table, with anything not listed reported as
"Unclassified" rather than guessed (see get_ticker_info below).

asset_class is one of: "stock", "bond", "cash", "alternative" (commodities/crypto
funds — these don't fit a stock/bond/cash split honestly, so they get their own
bucket rather than being force-classified as equity).

Covers roughly 700 tickers: S&P 500-weight large/mid-cap stocks, popular small-cap
and growth/retail names, major international ADRs, and a broad set of ETFs and
mutual funds (broad-market, sector, thematic, dividend, bond, country-specific).
Expand as needed when a real portfolio screenshot surfaces a ticker not in here.
"""

TICKER_REFERENCE: dict[str, dict[str, str]] = {}


def _add(asset_class: str, sector: str, *tickers: str) -> None:
    for ticker in tickers:
        TICKER_REFERENCE[ticker] = {"asset_class": asset_class, "sector": sector}


# --- Individual stocks, by sector ---
_add("stock", "Technology",
     "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "AVGO", "ORCL", "CRM",
     "ADBE", "INTC", "AMD", "CSCO", "IBM", "QCOM", "TXN", "NOW", "INTU", "AMAT",
     "MU", "PANW", "SNPS", "CDNS", "ANET", "LRCX", "KLAC", "ADI", "MRVL", "DELL", "HPQ",
     "CRWD", "ZS", "NET", "DDOG", "SNOW", "MDB", "TEAM", "WDAY", "PLTR", "SMCI", "ARM",
     "ON", "SWKS", "MPWR", "FTNT", "GEN", "AKAM", "JNPR", "NTAP", "STX", "WDC", "TER",
     "GRMN", "HPE", "TYL", "ROP", "GDDY", "PTC", "ZBRA", "TRMB", "FICO", "APH", "GLW",
     "KEYS", "CTSH", "ACN", "IT", "EPAM", "FSLR", "ENPH", "SEDG", "SHOP", "SQ", "AFRM",
     "U", "RBLX", "TTD", "DOCU", "OKTA", "TWLO", "HUBS", "BILL", "PATH", "GTLB", "S")
_add("stock", "Communication Services",
     "NFLX", "DIS", "CMCSA", "T", "VZ", "TMUS", "WBD", "EA", "TTWO", "PINS", "SNAP",
     "SPOT", "MTCH", "IAC", "LYV", "NWSA", "FOXA", "PARA", "CHTR", "OMC", "IPG", "ROKU")
_add("stock", "Financials",
     "JPM", "BAC", "WFC", "C", "GS", "MS", "SCHW", "BLK", "AXP", "V", "MA", "PYPL",
     "SPGI", "ICE", "CME", "USB", "PNC", "TFC", "COF", "AIG", "MET", "PRU", "ALL",
     "SOFI", "COIN", "ALLY", "DFS", "SYF", "TROW", "BX", "KKR", "APO", "ARES", "STT",
     "BK", "FITB", "HBAN", "RF", "CFG", "KEY", "MTB", "NTRS", "AJG", "MMC", "AON",
     "WTW", "BRO", "CB", "TRV", "PGR", "HIG", "AFL", "GL", "MSCI", "MCO", "NDAQ",
     "CBOE", "TW", "HOOD", "UPST", "LC", "AXON")
_add("stock", "Healthcare",
     "UNH", "JNJ", "LLY", "ABBV", "MRK", "PFE", "TMO", "ABT", "DHR", "BMY", "AMGN",
     "GILD", "CVS", "CI", "ISRG", "VRTX", "REGN", "MDT", "SYK", "BSX", "HUM", "ELV", "ZTS",
     "MRNA", "BIIB", "ILMN", "IDXX", "DXCM", "ALGN", "HCA", "CNC", "MOH", "GEHC",
     "RMD", "IQV", "A", "WAT", "MTD", "BDX", "BAX", "COO", "STE", "ZBH", "EW", "HOLX",
     "INCY", "VTRS", "CTLT", "TECH", "DVA", "UHS", "CAH", "MCK", "COR")
_add("stock", "Consumer Discretionary",
     "TSLA", "HD", "MCD", "NKE", "SBUX", "LOW", "TJX", "BKNG", "TGT", "MAR", "GM",
     "F", "CMG", "ORLY", "ROST", "YUM", "EBAY", "ETSY", "ABNB", "UBER", "LYFT",
     "RIVN", "LCID", "NIO", "LI", "XPEV", "GME", "AMC", "DPZ", "WING", "SHAK", "CAVA",
     "CROX", "DECK", "LULU", "RH", "BBY", "DG", "DLTR", "GPS", "ANF", "AZO", "POOL",
     "EXPE", "TRIP", "CCL", "RCL", "NCLH", "DAL", "UAL", "AAL", "LUV", "HLT", "WYNN",
     "MGM", "LVS", "DKNG", "PENN", "ULTA", "BURL", "TSCO", "DASH", "CVNA", "KMX")
_add("stock", "Consumer Staples",
     "PG", "KO", "PEP", "WMT", "COST", "PM", "MO", "MDLZ", "CL", "KMB", "GIS",
     "KHC", "STZ", "KR", "SYY", "ADM", "HSY", "MKC", "CLX", "CHD", "TAP", "CAG",
     "SJM", "CPB", "TSN", "HRL", "BG", "K", "KDP", "MNST", "EL", "KVUE")
_add("stock", "Industrials",
     "BA", "CAT", "HON", "UPS", "RTX", "LMT", "GE", "DE", "UNP", "MMM", "NOC",
     "GD", "EMR", "ETN", "FDX", "CSX", "NSC", "WM", "ITW", "PH", "CMI", "PCAR",
     "ROK", "CARR", "OTIS", "IR", "DOV", "XYL", "AME", "FTV", "SWK", "PWR", "J",
     "GNRC", "URI", "PAYX", "ADP", "VRSK", "CTAS", "RSG", "WCN", "EXPD", "CHRW",
     "JBHT", "ODFL")
_add("stock", "Energy",
     "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "WMB", "KMI",
     "HES", "DVN", "FANG", "BKR", "HAL", "TRGP", "OKE", "CTRA", "EQT", "MRO")
_add("stock", "Utilities",
     "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "ED", "WEC", "ES", "PEG",
     "AWK", "PPL", "FE", "AEE", "CMS", "CNP", "ATO", "NI", "LNT", "EVRG", "PNW")
_add("stock", "Real Estate",
     "AMT", "PLD", "CCI", "EQIX", "PSA", "O", "SPG", "DLR", "WELL", "AVB",
     "EQR", "VTR", "ARE", "INVH", "MAA", "ESS", "UDR", "CPT", "EXR", "SUI",
     "IRM", "WY", "HST", "KIM", "REG", "BXP", "VNO")
_add("stock", "Materials",
     "LIN", "APD", "SHW", "ECL", "FCX", "NEM", "DOW", "DD", "PPG", "NUE", "STLD",
     "VMC", "MLM", "ALB", "CTVA", "IFF", "PKG", "IP", "AVY", "BALL", "CE")

# --- Major international ADRs ---
# Split by actual GICS-aligned sector rather than one catch-all "Consumer" bucket —
# a single mixed bucket would silently defeat sector-concentration detection (e.g. a
# portfolio heavy in SHEL+BP+TTE would never trigger an energy-concentration flag).
_add("stock", "International — Technology", "TSM", "ASML", "SAP", "BABA", "JD", "PDD",
     "BIDU", "TCEHY", "SONY", "SFTBY")
_add("stock", "International — Energy", "SHEL", "TTE", "BP")
_add("stock", "International — Healthcare", "NVO", "GSK", "AZN", "SNY")
_add("stock", "International — Financials", "HSBC")
_add("stock", "International — Materials", "RIO", "BHP")
_add("stock", "International — Consumer", "UL", "DEO", "BUD", "TM", "HMC", "NSANY")

# --- Broad-market equity ETFs ---
_add("stock", "US Broad Market",
     "SPY", "VOO", "IVV", "VTI", "QQQ", "DIA", "IWM", "VUG", "VTV", "SCHX",
     "IJH", "IJR", "MDY", "SCHD", "VYM", "VIG", "DVY", "SCHB", "SPLG", "RSP",
     "VB", "VBR", "VBK", "VO", "VOT", "VOE", "IWO", "IWN", "IJS", "IJK", "IWF", "IWD")
_add("stock", "International Equity",
     "VEA", "VWO", "VXUS", "EFA", "IEMG", "EEM", "IXUS", "SCHF", "SCHE", "IEFA",
     "SPDW", "SPEM", "ACWI", "ACWX", "VT")
_add("stock", "International — Country/Region",
     "EWJ", "EWZ", "EWG", "EWU", "EWC", "EWA", "EWY", "EWT", "INDA", "FXI", "MCHI",
     "KWEB", "EWH", "EWS", "RSX", "EZA", "EIDO", "EPI")

# --- Sector equity ETFs ---
_add("stock", "Technology", "XLK", "VGT", "SMH", "SOXX", "IGV", "SKYY", "FDN", "HACK", "CIBR")
_add("stock", "Financials", "XLF", "VFH", "KRE", "KBE", "IAI")
_add("stock", "Healthcare", "XLV", "VHT", "IBB", "XBI")
_add("stock", "Energy", "XLE", "VDE", "XOP", "AMLP")
_add("stock", "Consumer Discretionary", "XLY", "VCR")
_add("stock", "Consumer Staples", "XLP", "VDC")
_add("stock", "Industrials", "XLI", "VIS", "ITA", "PPA")
_add("stock", "Utilities", "XLU", "VPU")
_add("stock", "Real Estate", "XLRE", "VNQ", "RWO", "REZ", "SCHH", "IYR")
_add("stock", "Materials", "XLB", "VAW")
_add("stock", "Communication Services", "XLC", "VOX")

# --- Thematic / growth ETFs ---
_add("stock", "Thematic — Innovation", "ARKK", "ARKG", "ARKW", "ARKF", "ARKQ")
_add("stock", "Thematic — Clean Energy", "ICLN", "TAN", "PBW", "QCLN")
_add("stock", "Thematic — Robotics/AI", "ROBO", "BOTZ", "IRBO")
_add("stock", "Dividend-Focused", "DGRO", "HDV", "NOBL", "SPHD", "SCHY", "SDY", "SPYD")
_add("stock", "Style — Growth/Value", "MGK", "MGV", "VONG", "VONV", "VTWG", "VTWV")

# --- Bond ETFs ---
_add("bond", "Aggregate/Broad Bond", "BND", "AGG", "BNDX", "SCHZ", "BIV", "SPAB")
_add("bond", "Treasury", "TLT", "IEF", "SHY", "GOVT", "VGIT", "VGSH", "VGLT",
     "EDV", "SPTL", "SPTS", "IEI", "SCHR", "SCHO")
_add("bond", "Corporate Bond", "LQD", "VCIT", "VCSH", "VCLT", "SPIB", "SPLB", "IGIB")
_add("bond", "High Yield", "HYG", "JNK", "SHYG", "USHY")
_add("bond", "Municipal", "MUB", "VTEB", "TFI", "HYD")
_add("bond", "TIPS", "TIP", "SCHP", "VTIP", "STIP")
_add("bond", "International Bond", "BNDW", "IAGG", "EMB", "PCY")

# --- Cash-equivalent ---
_add("cash", "Cash & Equivalents", "BIL", "SGOV", "SHV", "VMFXX", "SPAXX", "CASH", "ICSH")

# --- Alternatives (commodities, crypto) ---
_add("alternative", "Precious Metals", "GLD", "IAU", "SLV", "GLDM", "SGOL", "PPLT")
_add("alternative", "Cryptocurrency", "IBIT", "FBTC", "GBTC", "ETHE", "BITO", "ARKB", "MSTR")
_add("alternative", "Commodities (Broad)", "DBC", "PDBC", "GSG", "USO")

# --- Common mutual funds (5-letter symbols ending in X) ---
_add("stock", "US Broad Market", "VFIAX", "VTSAX", "FXAIX", "FSKAX", "FZROX", "SWPPX",
     "SWTSX", "VIGAX", "VTCLX", "FSPGX")
_add("stock", "International Equity", "VTIAX", "FTIHX", "FSPSX", "VGTSX")
_add("bond", "Aggregate/Broad Bond", "VBTLX", "FXNAX", "SWAGX", "VBMFX")

# Target-date/allocation funds (VFORX, VTHRX, VTTSX, FDKLX, TRRIX, etc.) are
# deliberately NOT listed here — they're genuinely blended stock/bond/cash funds,
# and forcing one into a single asset_class would overstate equity exposure and
# skew sector percentages. Left unclassified rather than guessed, matching
# get_ticker_info's stated fallback philosophy.


def get_ticker_info(ticker: str) -> dict[str, str]:
    """Looks up a ticker's asset class + sector. Anything not in the bundled
    reference returns "Unclassified" for both fields rather than a guess —
    honesty about coverage gaps matters more than a plausible-looking default."""
    ticker = (ticker or "").strip().upper()
    return TICKER_REFERENCE.get(ticker, {"asset_class": "Unclassified", "sector": "Unclassified"})
