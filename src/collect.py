"""Daily collector: fetch the last 48 hours and store them in data/aqi.db.

Usage (from the repo root):  python src/collect.py   or   python -m src.collect

Flow:
  1. OpenAQ (real monitors) if OPENAQ_API_KEY is set.
  2. Open-Meteo (model) ONLY if the key is missing/invalid or fewer than
     MIN_OPENAQ_STATIONS stations returned usable data.
  3. Clean rows (sanity filter, drop future hours, drop rows with no PM).
  4. INSERT OR IGNORE into SQLite.
Exit code 1 if neither source produced any data, so GitHub Actions shows a red cross.
"""
from __future__ import annotations

import logging
import math
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

if __package__ in (None, ""):  # lets `python src/collect.py` find the `src` package
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config, db, openmeteo_client
from src.discover import ensure_stations
from src.openaq_client import OpenAQAuthError, OpenAQClient, parse_hours

logger = logging.getLogger(__name__)

POLLUTANTS = ("pm25", "pm10", "no2", "o3")


# --------------------------------------------------------------- cleaning
def clean_value(value: object, pollutant: str) -> float | None:
    """Return a float, or None for missing, negative or absurd values."""
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(v) or v < 0 or v > config.MAX_VALID[pollutant]:
        return None
    return round(v, 2)


def clean_rows(rows: list[dict], now: datetime) -> list[dict]:
    """Apply the data rules: sanity filter, no future hours, need PM2.5 or PM10."""
    cleaned: list[dict] = []
    for row in rows:
        ts: datetime = row["ts"]
        if ts > now:  # forecasts / clock skew - we only keep observed hours
            continue
        out = dict(row)
        for p in POLLUTANTS:
            out[p] = clean_value(row.get(p), p)
        if out["pm25"] is None and out["pm10"] is None:
            continue
        out["ts"] = ts.astimezone(config.IST).isoformat(timespec="seconds")
        cleaned.append(out)
    return cleaned


# ----------------------------------------------------------------- OpenAQ
def fetch_station_rows(client: OpenAQClient, station: dict, start: datetime, end: datetime) -> list[dict]:
    """Download every pollutant of one station and merge them into hourly rows."""
    by_hour: dict[datetime, dict] = {}
    for param, sensor_id in station["sensors"].items():
        results = client.get_hours(sensor_id, start, end)
        for ts, value in parse_hours(results, param, station.get("units", {}).get(param)).items():
            row = by_hour.setdefault(ts, {
                "station_id": str(station["id"]), "station": station["name"], "ts": ts,
                "pm25": None, "pm10": None, "no2": None, "o3": None, "source": "openaq",
            })
            row[param] = value
    return list(by_hour.values())


def collect_openaq(client: OpenAQClient, stations: list[dict], start: datetime, end: datetime,
                   now: datetime) -> tuple[list[dict], int]:
    """Clean rows from all stations plus the number of stations with usable data."""
    all_rows: list[dict] = []
    usable = 0
    for station in stations:
        try:
            rows = clean_rows(fetch_station_rows(client, station, start, end), now)
        except OpenAQAuthError:
            raise  # a bad key affects every station - stop and fall back
        except Exception as exc:  # one broken station must not stop the run
            logger.error("Station %s failed: %s", station.get("name"), exc)
            continue
        logger.info("%s: %d usable hours", station["name"], len(rows))
        if rows:
            usable += 1
            all_rows.extend(rows)
    return all_rows, usable


# ------------------------------------------------------------------ main
def run(hours: int = config.COLLECT_HOURS, now: datetime | None = None,
        db_path: Path = config.DB_PATH) -> int:
    """Collect `hours` of history. Returns the number of usable rows fetched."""
    now = now or datetime.now(config.IST)
    start = now - timedelta(hours=hours)
    rows: list[dict] = []
    usable_stations = 0

    api_key = os.getenv(config.OPENAQ_KEY_ENV, "").strip()
    if api_key:
        try:
            client = OpenAQClient(api_key)
            stations = ensure_stations(client)
            rows, usable_stations = collect_openaq(client, stations, start, now, now)
            logger.info("OpenAQ: %d rows from %d stations", len(rows), usable_stations)
        except OpenAQAuthError as exc:
            logger.error("%s", exc)
        except Exception as exc:
            logger.error("OpenAQ collection failed: %s", exc)
    else:
        logger.warning("OPENAQ_API_KEY not set - using the Open-Meteo model fallback.")

    if usable_stations < config.MIN_OPENAQ_STATIONS:
        logger.warning("Only %d OpenAQ stations usable (< %d) - adding Open-Meteo fallback.",
                       usable_stations, config.MIN_OPENAQ_STATIONS)
        past_days = math.ceil(hours / 24)
        fallback = clean_rows(openmeteo_client.fetch_all(past_days), now)
        # The API returns whole days; keep only the requested window.
        start_iso = start.isoformat(timespec="seconds")
        fallback = [r for r in fallback if r["ts"] >= start_iso]
        logger.info("Open-Meteo: %d rows", len(fallback))
        rows.extend(fallback)

    db.insert_readings(rows, db_path)
    return len(rows)


def _load_env() -> None:
    """Load .env for local runs; in GitHub Actions the secret is already an env var."""
    try:
        from dotenv import load_dotenv
        load_dotenv(config.ROOT_DIR / ".env")
    except ImportError:
        pass


def main(hours: int = config.COLLECT_HOURS) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    _load_env()
    fetched = run(hours)
    logger.info("Done. %d rows fetched, %d rows in database.", fetched, db.count_rows())
    if fetched == 0:
        logger.error("No data from OpenAQ or Open-Meteo - failing the run.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
