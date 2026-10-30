"""Find active Delhi monitoring stations on OpenAQ and save them to data/stations.json.

Run manually with `python src/discover.py` to refresh the station list.
The collector calls ensure_stations(), which only re-discovers when the file
is missing - keeping the station set stable between daily runs.
"""
from __future__ import annotations

import json
import logging
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

if __package__ in (None, ""):  # lets `python src/discover.py` find the `src` package
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config
from src.openaq_client import OpenAQClient

logger = logging.getLogger(__name__)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km (used to rank stations by closeness to the centre)."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def summarise_location(loc: dict) -> dict | None:
    """Reduce an OpenAQ location to what we store; None if it has no PM2.5 sensor."""
    coords = loc.get("coordinates") or {}
    lat, lon = coords.get("latitude"), coords.get("longitude")
    if lat is None or lon is None:
        return None
    sensors: dict[str, int] = {}
    units: dict[str, str] = {}
    for sensor in loc.get("sensors", []):
        param = (sensor.get("parameter") or {}).get("name")
        if param in config.OPENAQ_PARAMETERS and param not in sensors:
            sensors[param] = sensor["id"]
            units[param] = sensor["parameter"].get("units", "")
    if "pm25" not in sensors:
        return None
    return {
        "id": loc["id"],
        "name": loc.get("name") or f"Location {loc['id']}",
        "lat": lat,
        "lon": lon,
        "sensors": sensors,
        "units": units,
        "is_monitor": bool(loc.get("isMonitor", False)),
        "distance_km": round(haversine_km(*config.DELHI_CENTER, lat, lon), 2),
        "datetime_last": ((loc.get("datetimeLast") or {}).get("utc")),
    }


def rank_candidates(locations: list[dict]) -> list[dict]:
    """Stationary PM2.5 stations, reference monitors only (if any exist), closest first.

    Why monitors only: OpenAQ also lists low-cost sensors; mixing them with
    government reference monitors would make station comparisons unfair.
    """
    candidates = []
    for loc in locations:
        if loc.get("isMobile", False):
            continue
        summary = summarise_location(loc)
        if summary is not None:
            candidates.append(summary)
    monitors = [c for c in candidates if c["is_monitor"]]
    if monitors:
        candidates = monitors
    else:
        logger.warning("No reference monitors found; using all PM2.5 locations.")
    return sorted(candidates, key=lambda c: c["distance_km"])


def pm25_is_fresh(client: OpenAQClient, station: dict, now: datetime) -> bool:
    """True if the station's PM2.5 sensor reported a value in the last 24 hours."""
    cutoff = now - timedelta(hours=config.STATION_FRESHNESS_HOURS)
    try:
        latest = client.get_latest(station["id"])
        for item in latest:
            if item.get("sensorsId") == station["sensors"]["pm25"] and item.get("value") is not None:
                ts = _parse_utc((item.get("datetime") or {}).get("utc"))
                return ts is not None and ts >= cutoff
        return False
    except Exception as exc:  # fall back to the location-level timestamp
        logger.warning("Latest check failed for %s (%s); using datetimeLast.", station["name"], exc)
        ts = _parse_utc(station.get("datetime_last"))
        return ts is not None and ts >= cutoff


def discover(client: OpenAQClient, now: datetime | None = None) -> list[dict]:
    """Search OpenAQ, keep up to MAX_STATIONS fresh stations and save them."""
    now = now or datetime.now(timezone.utc)
    locations = client.find_locations()
    logger.info("OpenAQ returned %d PM2.5 locations within %d km", len(locations),
                config.SEARCH_RADIUS_M // 1000)
    chosen: list[dict] = []
    for cand in rank_candidates(locations):
        if len(chosen) >= config.MAX_STATIONS:
            break
        if pm25_is_fresh(client, cand, now):
            chosen.append(cand)
            logger.info("Selected %s (%.1f km)", cand["name"], cand["distance_km"])
    save_stations(chosen)
    return chosen


def save_stations(stations: list[dict], path: Path = config.STATIONS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(stations, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Saved %d stations to %s", len(stations), path.name)


def load_stations(path: Path = config.STATIONS_PATH) -> list[dict] | None:
    """Saved stations, or None if the file is missing/broken/empty."""
    if not path.exists():
        return None
    try:
        stations = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("stations.json is not valid JSON; it will be rebuilt.")
        return None
    return stations or None


def ensure_stations(client: OpenAQClient) -> list[dict]:
    """Use the saved station list; discover only when it does not exist yet."""
    stations = load_stations()
    if stations is None:
        logger.info("No saved stations - running discovery.")
        stations = discover(client)
    return stations


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        from dotenv import load_dotenv
        load_dotenv(config.ROOT_DIR / ".env")
    except ImportError:
        pass
    key = os.getenv(config.OPENAQ_KEY_ENV)
    if not key:
        logger.error("OPENAQ_API_KEY is not set. Add it to .env (see README).")
        return 1
    stations = discover(OpenAQClient(key))
    if not stations:
        logger.error("No active stations found. Try again later (see README troubleshooting).")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
