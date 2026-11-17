# Author: Siddhant Shukla <sidz0124@gmail.com>
from datetime import date
from pathlib import Path

AUTHOR_NAME = "Siddhant Shukla"
AUTHOR_EMAIL = "sidz0124@gmail.com"
AUTHOR_EDUCATION = "BITS Pilani (Birla Institute of Technology and Science, Pilani)"
AUTHOR_DEGREE = "Dual major: MSc Economics and BE Electronics & Communication Engineering (BE ECE)"

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
RAW_FO = DATA / "raw" / "fo"
RAW_PART = DATA / "raw" / "participant"
RAW_PRICES = DATA / "raw" / "prices"
PROCESSED = DATA / "processed"
OUTPUT = ROOT / "output"
FIGURES = OUTPUT / "figures"
TABLES = OUTPUT / "tables"
REPORT_PDF = OUTPUT / "India_Retail_Options_Research.pdf"

for _p in (RAW_FO, RAW_PART, RAW_PRICES, PROCESSED, FIGURES, TABLES):
    _p.mkdir(parents=True, exist_ok=True)

START = date(2020, 1, 1)
END = date.today()

# NSE switched from the legacy F&O bhavcopy to the UDiFF format on this date.
UDIFF_START = date(2024, 7, 8)

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Referer": "https://www.nseindia.com/",
    "Accept": "*/*",
}
DOWNLOAD_THREADS = 4
DOWNLOAD_SLEEP = 0.25

RISK_FREE = 0.065
TRADING_DAYS = 252

# Universe split, mirroring the U.S. study's "Top 100 vs Rest" scaled to the ~200-name NSE F&O list.
TOP_N = 30
BASELINE_PERIOD = ("2020-01-01", "2020-12-31")
PEAK_PERIOD = ("2023-01-01", "2024-11-19")

INDEX_SYMBOLS = ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTYNXT50"]

EVENTS = {
    "2020-03-23": "COVID crash low",
    "2020-12-01": "Peak-margin rules phase-in",
    "2024-10-01": "STT hike on F&O",
    "2024-11-20": "SEBI F&O curbs",
    "2025-07-03": "SEBI Jane Street order",
}
SEBI_CURB_DATE = "2024-11-20"

# Backtest parameters
VOLSCORE_N = 20
CALLSPREAD_N = 10
CALLSPREAD_OTM = 0.05
CALLSPREAD_BUDGET = 0.05  # fraction of NAV spent on call-spread premium each month

# NSE symbol -> Yahoo ticker overrides for renamed / merged names
YAHOO_RENAMES = {
    "ZOMATO": "ETERNAL",
    "MCDOWELL-N": "UNITDSPR",
    "CADILAHC": "ZYDUSLIFE",
    "LTI": "LTM",
    "LTIM": "LTM",
    "GMRINFRA": "GMRAIRPORT",
    "CENTURYTEX": "ABREL",
    "TATAGLOBAL": "TATACONSUM",
    "SRTRANSFIN": "SHRIRAMFIN",
    "PVR": "PVRINOX",
    "ADANITRANS": "ADANIENSOL",
    "MOTHERSUMI": "MOTHERSON",
    "INFRATEL": "INDUSTOWER",
    "AMARAJABAT": "ARE&M",
    "NIITTECH": "COFORGE",
    "IBULHSGFIN": "SAMMAANCAP",
    "TATAMOTORS": "TMPV",
    "L&TFH": "LTF",
    "M&M": "M&M",
    "M&MFIN": "M&MFIN",
}

YAHOO_INDEX = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK", "INDIAVIX": "^INDIAVIX"}

COLORS = {
    "navy": "#00395D",
    "teal": "#00AEEF",
    "grey": "#7F7F7F",
    "orange": "#E87722",
    "green": "#2E8B57",
    "red": "#C0392B",
    "purple": "#6C3483",
}
