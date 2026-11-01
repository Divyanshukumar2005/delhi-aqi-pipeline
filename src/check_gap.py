"""Does OpenAQ really have no data for the Oct 23-27 outage? Checks the hourly AND the raw endpoint.

Usage:  python src/check_gap.py                       (default window = 23 Oct 21:00 -> 27 Oct 08:00 IST)
        python src/check_gap.py 2026-10-24 2026-10-26  (any window, IST dates)
Prints, for a few stations, how many PM2.5 values OpenAQ returns for that window.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config
from src.openaq_client import OpenAQClient, _iso_utc

DEFAULT_START = datetime(2026, 10, 23, 21, 0, tzinfo=config.IST)
DEFAULT_END = datetime(2026, 10, 27, 8, 0, tzinfo=config.IST)
RAW_LIMIT = 1000


def count_window(client, sensor_id: int, start: datetime, end: datetime) -> dict:
    """Number of values OpenAQ returns for one sensor: hourly averages vs raw measurements."""
    out = {"hours": None, "raw": None, "raw_capped": False, "error": None}
    try:
        hours = client.get_hours(sensor_id, start, end)
        out["hours"] = sum(1 for r in hours if r.get("value") is not None)
    except Exception as exc:                                   # keep going: report what we can
        out["error"] = f"hours: {exc}"
    try:
        raw = client._get(f"/sensors/{sensor_id}/measurements", {
            "datetime_from": _iso_utc(start), "datetime_to": _iso_utc(end), "limit": RAW_LIMIT}).get("results", [])
        out["raw"] = len(raw)
        out["raw_capped"] = len(raw) >= RAW_LIMIT
    except Exception as exc:
        out["error"] = (out["error"] + " | " if out["error"] else "") + f"raw: {exc}"
    return out


def verdict(rows: list[dict]) -> str:
    hours = sum(r["hours"] or 0 for r in rows)
    raw = sum(r["raw"] or 0 for r in rows)
    if hours > 0:
        return "OpenAQ HAS hourly data for this window -> run the backfill again, it will fill the gap."
    if raw > 0:
        return "Hourly is empty but RAW measurements exist -> the gap can be rebuilt from raw data (tell Claude)."
    return "OpenAQ has NOTHING for this window (hourly and raw) -> the gap is upstream, it cannot be recovered."


def main(argv: list[str]) -> int:
    start, end = DEFAULT_START, DEFAULT_END
    if len(argv) >= 3:
        start = datetime.fromisoformat(argv[1]).replace(tzinfo=config.IST)
        end = datetime.fromisoformat(argv[2]).replace(tzinfo=config.IST) + timedelta(days=1)
    try:
        from dotenv import load_dotenv
        load_dotenv(config.ROOT_DIR / ".env")
    except ImportError:
        pass
    key = os.getenv(config.OPENAQ_KEY_ENV)
    if not key:
        print("OPENAQ_API_KEY is not set (add it to .env).")
        return 1
    stations = [s for s in json.loads(config.STATIONS_PATH.read_text(encoding="utf-8")) if s.get("sensors", {}).get("pm25")][:5]
    client = OpenAQClient(key)
    print(f"Window: {start:%d %b %H:%M} -> {end:%d %b %H:%M} IST\n")
    print(f"{'station':42s} {'hourly values':>13s} {'raw rows':>9s}")
    rows = []
    for s in stations:
        r = count_window(client, s["sensors"]["pm25"], start, end)
        rows.append(r)
        raw = "-" if r["raw"] is None else f"{r['raw']}{'+' if r['raw_capped'] else ''}"
        print(f"{s['name'][:42]:42s} {str(r['hours']):>13s} {raw:>9s}" + (f"   ({r['error']})" if r["error"] else ""))
    print("\n" + verdict(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
