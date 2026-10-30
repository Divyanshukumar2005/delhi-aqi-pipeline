"""SQLite helpers: create the table, insert rows idempotently, load data."""
from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Iterator

import pandas as pd

from src import config

logger = logging.getLogger(__name__)

COLUMNS: list[str] = ["station_id", "station", "ts", "pm25", "pm10", "no2", "o3", "source"]

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS readings (
    station_id TEXT NOT NULL,
    station    TEXT,
    ts         TEXT NOT NULL,   -- ISO 8601 in IST, e.g. 2026-10-30T13:00:00+05:30
    pm25       REAL,
    pm10       REAL,
    no2        REAL,
    o3         REAL,
    source     TEXT NOT NULL,   -- 'openaq' or 'open-meteo'
    PRIMARY KEY (station_id, ts, source)
);
"""


@contextmanager
def get_connection(db_path: Path | str = config.DB_PATH) -> Iterator[sqlite3.Connection]:
    """Open a connection, commit on success and ALWAYS close it.

    sqlite3's own context manager commits but does not close, which leaves the
    file locked on Windows; this helper does both.
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path | str = config.DB_PATH) -> None:
    """Create the readings table if it does not exist yet."""
    with get_connection(db_path) as conn:
        conn.execute(CREATE_TABLE_SQL)


def insert_readings(rows: Iterable[dict], db_path: Path | str = config.DB_PATH) -> int:
    """Insert rows with INSERT OR IGNORE and return how many were actually new.

    INSERT OR IGNORE + the composite primary key makes re-runs safe: the
    daily job re-downloads 48 h, so most rows already exist and are skipped.
    """
    records = [tuple(row.get(col) for col in COLUMNS) for row in rows]
    if not records:
        return 0
    init_db(db_path)
    with get_connection(db_path) as conn:
        before = conn.total_changes
        conn.executemany(
            f"INSERT OR IGNORE INTO readings ({', '.join(COLUMNS)}) "
            f"VALUES ({', '.join('?' for _ in COLUMNS)})",
            records,
        )
        inserted = conn.total_changes - before
    logger.info("Inserted %d new rows (%d already present)", inserted, len(records) - inserted)
    return inserted


def load_readings(db_path: Path | str = config.DB_PATH) -> pd.DataFrame:
    """Load all readings as a DataFrame with a tz-aware IST 'ts' column.

    Returns an empty DataFrame (with the right columns) if the DB or table is
    missing, so the dashboard never crashes on a fresh clone.
    """
    db_path = Path(db_path)
    empty = pd.DataFrame(columns=COLUMNS)
    if not db_path.exists():
        return empty
    try:
        with get_connection(db_path) as conn:
            df = pd.read_sql_query(f"SELECT {', '.join(COLUMNS)} FROM readings", conn)
    except (sqlite3.OperationalError, pd.errors.DatabaseError) as exc:
        logger.warning("Could not read readings table: %s", exc)
        return empty
    if df.empty:
        return empty
    df["ts"] = pd.to_datetime(df["ts"], utc=True).dt.tz_convert(config.IST)
    for col in ["pm25", "pm10", "no2", "o3"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values(["station_id", "ts"]).reset_index(drop=True)


def count_rows(db_path: Path | str = config.DB_PATH) -> int:
    """Number of rows in the readings table (0 if missing)."""
    if not Path(db_path).exists():
        return 0
    try:
        with get_connection(db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
    except sqlite3.OperationalError:
        return 0
