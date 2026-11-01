"""Tests for the SQL analytics in sql/.

They run offline on a small synthetic database and check three things:
1. every query file executes and returns rows,
2. the SQL AQI matches the reference Python implementation in src/analysis.py,
3. the CPCB rules (45 ug/m3 -> 75, the 16-hour minimum) hold in SQL.
"""
from __future__ import annotations

import importlib.util
import math
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from src import analysis, db

REPO = Path(__file__).resolve().parent.parent
SQL_DIR = REPO / "sql"
IST = timezone(timedelta(hours=5, minutes=30))

pytestmark = pytest.mark.skipif(sqlite3.sqlite_version_info < (3, 25, 0),
                                reason="needs SQLite 3.25+ for window functions")


def _load_runner():
    spec = importlib.util.spec_from_file_location("sql_run", SQL_DIR / "run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = _load_runner()
QUERY_FILES = runner.query_files()


# ----------------------------------------------------------- synthetic data
def _synthetic_rows() -> list[dict]:
    """16 stations x 25 days of hourly data with a daily cycle, a bad spell and a gap."""
    names = (
        [f"Delhi Station {i}, Delhi - DPCC" for i in range(11)]
        + [f"Sector {i}, Gurugram - HSPCB" for i in range(2)]
        + [f"Sector {i}, Noida - UPPCB" for i in range(2)]
        + ["Arya Nagar, Bahadurgarh - HSPCB"]
    )
    start = datetime(2026, 10, 1, 0, 0, tzinfo=IST)
    rows = []
    for s, name in enumerate(names):
        for h in range(25 * 24):
            ts = start + timedelta(hours=h)
            day = h // 24
            base = 45 + 3 * s + 25 * math.sin(h / 24 * 2 * math.pi)
            if 10 <= day <= 12:                       # a three-day severe spell
                base += 110
            pm25 = base if h % 29 else None          # sprinkle in missing values
            pm10 = base * 1.8 if (s % 2 == 0 and h % 31) else None
            no2 = 30 + 0.2 * base + (h % 7)
            if s == 0 and 300 <= h < 312:             # a 12-hour outage at station 0
                continue
            rows.append({"station_id": str(100 + s), "station": name, "ts": ts.isoformat(),
                         "pm25": pm25, "pm10": pm10, "no2": no2, "o3": 20.0, "source": "openaq"})
    return rows


@pytest.fixture(scope="module")
def db_path(tmp_path_factory) -> Path:
    path = tmp_path_factory.mktemp("sqltest") / "aqi.db"
    db.insert_readings(_synthetic_rows(), path)
    return path


@pytest.fixture()
def con(db_path):
    connection = runner.connect(db_path)
    yield connection
    connection.close()


# ------------------------------------------------------------------ tests
def test_setup_creates_the_expected_views(con):
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_temp_master WHERE type = 'view'")}
    assert {"v_bands", "v_hourly", "v_roll", "v_aqi"} <= names


def test_there_are_fifteen_queries_in_order():
    assert [p.name[:2] for p in QUERY_FILES] == [f"{n:02d}" for n in range(1, 16)]
    assert all(runner.title_of(p).startswith(f"Q{p.name[:2]}") for p in QUERY_FILES)


@pytest.mark.parametrize("path", QUERY_FILES, ids=[p.stem for p in QUERY_FILES])
def test_every_query_runs_and_returns_rows(con, path):
    columns, rows = runner.run_query(con, path)
    assert columns, f"{path.name} returned no columns"
    assert rows, f"{path.name} returned no rows on the synthetic data"


def test_sql_aqi_matches_the_python_implementation(db_path, con):
    sql = pd.read_sql("SELECT station_id, ts, aqi, category FROM v_aqi", con)
    py = analysis.add_aqi(db.load_readings(db_path))
    py["ts"] = (py["ts"].dt.strftime("%Y-%m-%dT%H:%M:%S%z")
                .str.replace(r"(\d\d)(\d\d)$", r"\1:\2", regex=True))
    merged = sql.merge(py[["station_id", "ts", "aqi", "category"]], on=["station_id", "ts"],
                       suffixes=("_sql", "_py"), how="outer", indicator=True)
    assert (merged["_merge"] == "both").all()                       # same rows on both sides
    assert (merged["aqi_sql"].isna() == merged["aqi_py"].isna()).all()   # NULL exactly where Python has none
    valid = merged.dropna(subset=["aqi_sql", "aqi_py"])
    assert len(valid) > 1000
    assert ((valid["aqi_sql"] - valid["aqi_py"]).abs() <= 1).all()  # 1 point of tolerance for float rounding


def _single_station(tmp_path, pm25_values, pm10_values=None, name="one.db") -> sqlite3.Connection:
    start = datetime(2026, 10, 1, 0, 0, tzinfo=IST)
    rows = [{"station_id": "1", "station": "Test, Delhi - DPCC", "ts": (start + timedelta(hours=h)).isoformat(),
             "pm25": v, "pm10": (pm10_values[h] if pm10_values else None), "no2": None, "o3": None,
             "source": "openaq"} for h, v in enumerate(pm25_values)]
    path = tmp_path / name          # a new file per call: inserts are idempotent, so reuse would keep old rows
    db.insert_readings(rows, path)
    return runner.connect(path)


def test_cpcb_worked_example_45_ugm3_gives_aqi_75(tmp_path):
    connection = _single_station(tmp_path, [45.0] * 24)
    aqi, category = connection.execute("SELECT aqi, category FROM v_aqi ORDER BY ts DESC LIMIT 1").fetchone()
    assert (aqi, category) == (75, "Satisfactory")
    connection.close()


def test_sixteen_valid_hours_are_required(tmp_path):
    fifteen_valid = [45.0] * 15 + [None] * 9          # only 15 valid hours in the 24-hour window
    connection = _single_station(tmp_path, fifteen_valid)
    assert connection.execute("SELECT aqi FROM v_aqi ORDER BY ts DESC LIMIT 1").fetchone()[0] is None
    connection.close()
    sixteen_valid = [45.0] * 16 + [None] * 8
    connection = _single_station(tmp_path, sixteen_valid, name="sixteen.db")
    assert connection.execute("SELECT aqi FROM v_aqi ORDER BY ts DESC LIMIT 1").fetchone()[0] == 75
    connection.close()


def test_aqi_is_the_worse_of_pm25_and_pm10(tmp_path):
    # PM2.5 45 -> 75, PM10 150 -> 100 + 100/150 * 50 = 133.3 -> 133, so PM10 decides.
    connection = _single_station(tmp_path, [45.0] * 24, [150.0] * 24)
    assert connection.execute("SELECT aqi FROM v_aqi ORDER BY ts DESC LIMIT 1").fetchone()[0] == 133
    connection.close()


def test_aqi_is_capped_at_500(tmp_path):
    connection = _single_station(tmp_path, [900.0] * 24)
    assert connection.execute("SELECT aqi, category FROM v_aqi ORDER BY ts DESC LIMIT 1").fetchone() == (500, "Severe")
    connection.close()


def test_runner_opens_the_database_read_only(db_path):
    connection = runner.connect(db_path)
    with pytest.raises(sqlite3.OperationalError):
        connection.execute("DELETE FROM readings")
    connection.close()


def test_runner_formats_plain_and_markdown_tables():
    columns, rows = ["a", "b"], [(1, 2.0), (None, "x|y")]
    plain = runner.format_plain(columns, rows)
    assert plain.splitlines()[0].split() == ["a", "b"]
    markdown = runner.format_markdown(columns, rows)
    assert markdown.splitlines()[1] == "|---|---|"
    assert "x/y" in markdown                       # pipes inside values are escaped
