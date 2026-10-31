"""Export the latest readings from SQLite to JSON for the React dashboard.

Why: the web dashboard cannot open a SQLite file in the browser, so after every
collection run we write two small JSON files that it can fetch:

    data/readings.json   last N days of hourly readings (compact)
    data/stations.json   already written by discover.py (left untouched)

Run from the repo root:  python src/export_json.py
"""
from __future__ import annotations

import json
import logging
import sqlite3
import sys
from pathlib import Path

# Allow `python src/export_json.py` as well as `python -m src.export_json`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config  # noqa: E402

logger = logging.getLogger(__name__)

EXPORT_DAYS = 14                      # enough for 24h averages + trends, keeps the file small
OUT_PATH = Path("data/readings.json")


def export_readings(db_path: Path | str = config.DB_PATH,
                    out_path: Path | str = OUT_PATH,
                    days: int = EXPORT_DAYS) -> int:
    """Write the last `days` days of readings to JSON and return the row count.

    The window is measured from the NEWEST timestamp in the DB (not from the
    wall clock), so the export still works if a collection run was missed.
    """
    conn = sqlite3.connect(db_path)
    try:
        newest = conn.execute("SELECT MAX(ts) FROM readings").fetchone()[0]
        if newest is None:
            raise RuntimeError("readings table is empty, nothing to export")
        # ts is ISO text in IST; SQLite's datetime() understands the +05:30 offset
        # and converts to UTC, so we compare in UTC for correctness.
        rows = conn.execute(
            """
            SELECT station_id, station, ts, pm25, pm10, no2, o3, source
            FROM readings
            WHERE datetime(ts) >= datetime(?, ?)
            ORDER BY ts
            """,
            (newest, f"-{int(days)} days"),
        ).fetchall()
    finally:
        conn.close()

    keys = ["station_id", "station", "ts", "pm25", "pm10", "no2", "o3", "source"]
    records = [dict(zip(keys, r)) for r in rows]

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # separators=(",", ":") removes spaces -> roughly 20% smaller file.
    out_path.write_text(json.dumps(records, separators=(",", ":")), encoding="utf-8")
    logger.info("Exported %d rows (%s days) to %s", len(records), days, out_path)
    return len(records)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    export_readings()
