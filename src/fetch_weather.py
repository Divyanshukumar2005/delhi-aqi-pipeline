"""Download hourly Delhi weather from Open-Meteo (no API key) for the ML forecast.

Usage:  python src/fetch_weather.py            (last 92 days + 2 forecast days -> data/weather.csv)
Re-running merges into the existing CSV, so history keeps growing beyond Open-Meteo's 92-day window.

Variables (all standard Open-Meteo hourly variables): temperature_2m, relative_humidity_2m,
wind_speed_10m, precipitation, surface_pressure. Times are requested in Asia/Kolkata (IST).
One point (central Delhi) is used for the whole city, which is a simplification.
"""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import pandas as pd
import requests

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config
from src.ml_forecast import WEATHER_COLUMNS

logger = logging.getLogger(__name__)

URL = "https://api.open-meteo.com/v1/forecast"
CENTRE = (28.6139, 77.2090)           # central Delhi
MAX_PAST_DAYS = 92
WEATHER_PATH: Path = config.DATA_DIR / "weather.csv"


def fetch(past_days: int = MAX_PAST_DAYS, forecast_days: int = 2, session: requests.Session | None = None) -> dict:
    """One request with timeout and exponential backoff (same pattern as the other API clients)."""
    session = session or requests.Session()
    params = {
        "latitude": CENTRE[0], "longitude": CENTRE[1],
        "hourly": ",".join(WEATHER_COLUMNS),
        "timezone": "Asia/Kolkata",
        "past_days": max(0, min(past_days, MAX_PAST_DAYS)),
        "forecast_days": forecast_days,
    }
    last_error: Exception | None = None
    for attempt in range(config.MAX_RETRIES + 1):
        try:
            resp = session.get(URL, params=params, timeout=config.REQUEST_TIMEOUT_S)
            if resp.status_code == 429 or resp.status_code >= 500:
                raise requests.HTTPError(f"HTTP {resp.status_code}")
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            last_error = exc
            if attempt < config.MAX_RETRIES:
                wait = config.BACKOFF_BASE_S * (2**attempt)
                logger.warning("Open-Meteo error (%s) - retry %d in %.0fs", exc, attempt + 1, wait)
                time.sleep(wait)
    raise RuntimeError(f"Open-Meteo failed after {config.MAX_RETRIES} retries: {last_error}")


def parse(data: dict) -> pd.DataFrame:
    """Hourly arrays -> DataFrame indexed by an IST timestamp, one column per variable."""
    hourly = data.get("hourly") or {}
    if "time" not in hourly:
        raise ValueError("Open-Meteo response has no hourly data")
    frame = pd.DataFrame({c: hourly.get(c) for c in WEATHER_COLUMNS})
    frame.index = pd.DatetimeIndex(pd.to_datetime(hourly["time"])).tz_localize(config.IST)
    frame.index.name = "ts"
    return frame.apply(pd.to_numeric, errors="coerce")


def load_weather(path: Path | str = WEATHER_PATH) -> pd.DataFrame | None:
    """Read the saved CSV (None if it does not exist yet)."""
    path = Path(path)
    if not path.exists():
        return None
    frame = pd.read_csv(path, index_col="ts")
    frame.index = pd.to_datetime(frame.index, utc=True).tz_convert(config.IST)
    return frame.sort_index()


def save_weather(new: pd.DataFrame, path: Path | str = WEATHER_PATH) -> pd.DataFrame:
    """Merge into the existing CSV (newer values win) and write it."""
    path = Path(path)
    old = load_weather(path)
    merged = new if old is None else pd.concat([old, new])
    merged = merged[~merged.index.duplicated(keep="last")].sort_index()
    path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(path, index_label="ts")
    return merged


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    merged = save_weather(parse(fetch()))
    print(f"Saved {len(merged)} hourly rows to {WEATHER_PATH} ({merged.index.min()} -> {merged.index.max()})")


if __name__ == "__main__":
    main()
