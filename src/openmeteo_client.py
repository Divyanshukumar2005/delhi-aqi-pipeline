"""Open-Meteo Air Quality API client (fallback source, no API key).

Checked against https://open-meteo.com/en/docs/air-quality-api :
  base URL  https://air-quality-api.open-meteo.com/v1/air-quality
  hourly    pm2_5, pm10, nitrogen_dioxide, ozone  (all µg/m³)
  past_days 0-92, forecast_days 0-7, timezone=Asia/Kolkata

IMPORTANT: these are MODEL estimates from the CAMS global forecast (~45 km
grid over India), not measurements. Nearby Delhi points can return almost
identical numbers. Attribution required: CAMS (Copernicus) + Open-Meteo.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime

import requests

from src import config

logger = logging.getLogger(__name__)


def fetch_location(
    lat: float,
    lon: float,
    past_days: int,
    session: requests.Session | None = None,
) -> dict:
    """Fetch hourly pollutants for one point, with timeout and exponential backoff."""
    session = session or requests.Session()
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(config.OPENMETEO_VARIABLES),
        "timezone": "Asia/Kolkata",
        "past_days": max(0, min(past_days, config.OPENMETEO_MAX_PAST_DAYS)),
        # forecast_days=1 returns today's hours; future hours are dropped later.
        "forecast_days": 1,
    }
    last_error: Exception | None = None
    for attempt in range(config.MAX_RETRIES + 1):
        try:
            resp = session.get(config.OPENMETEO_URL, params=params, timeout=config.REQUEST_TIMEOUT_S)
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


def parse_response(data: dict, station_id: str, station: str) -> list[dict]:
    """Convert the hourly arrays into one row dict per hour (timestamps in IST)."""
    hourly = data.get("hourly") or {}
    times = hourly.get("time") or []
    rows: list[dict] = []
    for i, t in enumerate(times):
        # With timezone=Asia/Kolkata the API returns local times without an offset.
        ts = datetime.fromisoformat(t).replace(tzinfo=config.IST)
        row: dict = {"station_id": station_id, "station": station, "ts": ts, "source": "open-meteo"}
        for api_name, col in config.OPENMETEO_VARIABLES.items():
            values = hourly.get(api_name) or []
            row[col] = values[i] if i < len(values) else None
        rows.append(row)
    return rows


def fetch_all(past_days: int, session: requests.Session | None = None) -> list[dict]:
    """Fetch every fallback location; a failing location is logged and skipped."""
    rows: list[dict] = []
    for loc in config.FALLBACK_LOCATIONS:
        try:
            data = fetch_location(loc["lat"], loc["lon"], past_days, session=session)
            rows.extend(parse_response(data, loc["station_id"], loc["station"]))
        except Exception as exc:  # one bad location must not stop the run
            logger.error("Open-Meteo failed for %s: %s", loc["station"], exc)
    return rows
