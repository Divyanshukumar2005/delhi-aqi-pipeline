"""List OpenAQ PM2.5 stations near a point, so you can pick ones to track.

Usage:  python src/find_station.py LAT LON [RADIUS_KM]
Example: python src/find_station.py 28.4595 77.0266 5
Then put the ids you want into config.EXTRA_STATION_IDS and run discover.py.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config
from src.discover import haversine_km
from src.openaq_client import OpenAQClient


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 1
    lat, lon = float(argv[1]), float(argv[2])
    radius_km = min(float(argv[3]) if len(argv) > 3 else 5.0, 25.0)
    try:
        from dotenv import load_dotenv
        load_dotenv(config.ROOT_DIR / ".env")
    except ImportError:
        pass
    key = os.getenv(config.OPENAQ_KEY_ENV)
    if not key:
        print("OPENAQ_API_KEY is not set (add it to .env).")
        return 1
    found = OpenAQClient(key).find_locations(lat, lon, int(radius_km * 1000))
    rows = []
    for loc in found:
        c = loc.get("coordinates") or {}
        if c.get("latitude") is None:
            continue
        last = ((loc.get("datetimeLast") or {}).get("utc") or "never")[:16]
        rows.append((haversine_km(lat, lon, c["latitude"], c["longitude"]), loc["id"],
                     loc.get("name") or "?", "monitor" if loc.get("isMonitor") else "low-cost",
                     "mobile" if loc.get("isMobile") else "fixed", last))
    if not rows:
        print(f"No PM2.5 stations within {radius_km:g} km of {lat}, {lon}.")
        return 0
    print(f"{'km':>5}  {'id':>8}  {'type':8} {'fixed':6} {'last reading (UTC)':17}  name")
    for km, i, name, kind, mob, last in sorted(rows):
        print(f"{km:5.1f}  {i:>8}  {kind:8} {mob:6} {last:17}  {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
