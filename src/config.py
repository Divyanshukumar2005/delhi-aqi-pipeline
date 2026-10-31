"""Central configuration: paths, API settings, thresholds and CPCB AQI breakpoints.

Everything that a reviewer might want to tweak lives here as plain data,
so the logic files stay free of "magic numbers".
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

# ---------------------------------------------------------------------------
# Paths (relative to the repo root, so the project works on any machine / CI)
# ---------------------------------------------------------------------------
ROOT_DIR: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = ROOT_DIR / "data"
DB_PATH: Path = DATA_DIR / "aqi.db"
STATIONS_PATH: Path = DATA_DIR / "stations.json"

# All timestamps in the DB are stored in Indian Standard Time.
IST = ZoneInfo("Asia/Kolkata")

# ---------------------------------------------------------------------------
# OpenAQ API v3 (primary source) - verified against https://docs.openaq.org
# ---------------------------------------------------------------------------
OPENAQ_BASE_URL: str = "https://api.openaq.org/v3"
OPENAQ_KEY_ENV: str = "OPENAQ_API_KEY"   # header name used by the API: X-API-Key
DELHI_CENTER: tuple[float, float] = (28.5400, 77.1300)   # Delhi-NCR centre
SEARCH_RADIUS_M: int = 25_000            # API maximum for coordinates+radius search (25 km)
MAX_STATIONS: int = 30
# OpenAQ location IDs that must always be tracked (find them with `python src/find_station.py LAT LON`).
EXTRA_STATION_IDS: list[int] = []
STATION_FRESHNESS_HOURS: int = 24        # a station must have reported within this window
MIN_OPENAQ_STATIONS: int = 3             # below this we switch to the Open-Meteo fallback
OPENAQ_PAGE_LIMIT: int = 1000            # results per page for /hours
OPENAQ_PARAMETERS: tuple[str, ...] = ("pm25", "pm10", "no2", "o3")

# Free tier: 60 requests/minute and 2,000/hour. Sleeping ~1.1 s between calls
# keeps us safely under 60/min even before we look at the rate-limit headers.
REQUEST_SLEEP_S: float = 1.1
REQUEST_TIMEOUT_S: int = 30
MAX_RETRIES: int = 3
BACKOFF_BASE_S: float = 2.0              # waits 2s, 4s, 8s between retries

# ---------------------------------------------------------------------------
# Open-Meteo Air Quality API (fallback, model-based CAMS data, no key needed)
# ---------------------------------------------------------------------------
OPENMETEO_URL: str = "https://air-quality-api.open-meteo.com/v1/air-quality"
OPENMETEO_MAX_PAST_DAYS: int = 92        # API allows 0-92
FALLBACK_LOCATIONS: list[dict] = [
    {"station_id": "om-anand-vihar", "station": "Anand Vihar", "lat": 28.6469, "lon": 77.3160},
    {"station_id": "om-rk-puram", "station": "RK Puram", "lat": 28.5633, "lon": 77.1869},
    {"station_id": "om-ito", "station": "ITO", "lat": 28.6289, "lon": 77.2410},
    {"station_id": "om-dwarka", "station": "Dwarka", "lat": 28.5921, "lon": 77.0460},
    {"station_id": "om-rohini", "station": "Rohini", "lat": 28.7324, "lon": 77.1176},
    {"station_id": "om-gurugram", "station": "Gurugram", "lat": 28.4595, "lon": 77.0266},
]
# Maps Open-Meteo variable names to our column names.
OPENMETEO_VARIABLES: dict[str, str] = {
    "pm2_5": "pm25",
    "pm10": "pm10",
    "nitrogen_dioxide": "no2",
    "ozone": "o3",
}

# ---------------------------------------------------------------------------
# Collection windows
# ---------------------------------------------------------------------------
COLLECT_HOURS: int = 48      # daily run re-fetches 48 h so a missed day self-heals
BACKFILL_DAYS: int = 90      # one-time history pull

# ---------------------------------------------------------------------------
# Sanity filter (µg/m³). Values below 0 or ABOVE these limits are set to NULL.
# Why these numbers: Delhi's worst real hourly PM2.5 readings are ~1,000 µg/m³
# and PM10 ~2,000 µg/m³ during dust storms; anything higher is almost
# certainly a sensor fault (e.g. 9999 error codes). Gas limits are far above
# any value ever recorded at Delhi CPCB stations.
# ---------------------------------------------------------------------------
MAX_VALID: dict[str, float] = {
    "pm25": 1500.0,
    "pm10": 2500.0,
    "no2": 1000.0,
    "o3": 1000.0,
}

# Molecular weights for ppm/ppb -> µg/m³ conversion (25 °C, 1 atm: 24.45 L/mol).
# Some OpenAQ providers report gases in ppm; Indian CPCB data is usually µg/m³.
MOLECULAR_WEIGHT: dict[str, float] = {"no2": 46.0055, "o3": 47.9982}
MOLAR_VOLUME_L: float = 24.45

# ---------------------------------------------------------------------------
# CPCB National Air Quality Index (NAQI) breakpoints - 24-hour averages, µg/m³
# Source: CPCB, "National Air Quality Index", Control of Urban Pollution Series
# CUPS/82/2014-15 (Oct 2014), Table 3.2 (publisher site: https://cpcb.nic.in).
# Copy of the report: https://smartnet.niua.org/sites/default/files/resources/Air%20Quality%20Index.pdf
# Government summary with the worked examples used in our tests:
# https://ies.gov.in/arthapedia/concept/national-air-quality-index
#
# The report prints bands as 0-30, 31-60, ... but its own worked examples
# (PM2.5 45 -> 75, PM2.5 150 -> 323) interpolate from the *previous band's
# upper value* (30, 120). So we store continuous bands (c_lo, c_hi, i_lo, i_hi).
# The report gives the Severe band only as "250+" / "430+"; we assume the same
# width as the Very Poor band (PM2.5 250-380, PM10 430-510) and cap AQI at 500,
# as CPCB's own portal does.
# ---------------------------------------------------------------------------
AQI_BREAKPOINTS: dict[str, list[tuple[float, float, int, int]]] = {
    "pm25": [
        (0, 30, 0, 50),
        (30, 60, 50, 100),
        (60, 90, 100, 200),
        (90, 120, 200, 300),
        (120, 250, 300, 400),
        (250, 380, 400, 500),
    ],
    "pm10": [
        (0, 50, 0, 50),
        (50, 100, 50, 100),
        (100, 250, 100, 200),
        (250, 350, 200, 300),
        (350, 430, 300, 400),
        (430, 510, 400, 500),
    ],
}
AQI_MAX: int = 500
ROLLING_WINDOW: str = "24h"
MIN_HOURS_IN_WINDOW: int = 16   # CPCB: minimum 16 hours of data for a 24-h sub-index

# (upper AQI limit, category name, colour) - colours follow the CPCB display scheme.
AQI_CATEGORIES: list[tuple[int, str, str]] = [
    (50, "Good", "#00B050"),
    (100, "Satisfactory", "#92D050"),
    (200, "Moderate", "#FFFF00"),
    (300, "Poor", "#FF9900"),
    (400, "Very Poor", "#FF0000"),
    (500, "Severe", "#C00000"),
]
POOR_OR_WORSE: tuple[str, ...] = ("Poor", "Very Poor", "Severe")

# ---------------------------------------------------------------------------
# Insights
# ---------------------------------------------------------------------------
DIWALI_DATE: date = date(2026, 11, 8)   # Lakshmi Puja day, Sunday 8 Nov 2026 (verified)
DIWALI_WINDOW_DAYS: int = 7
MIN_DAYS_PER_DIWALI_SIDE: int = 4       # need >= 4 of 7 days on each side to compare
SIGNIFICANCE_LEVEL: float = 0.05