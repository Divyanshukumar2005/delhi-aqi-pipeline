"""Tests for the SQLite helpers."""
from __future__ import annotations

from src import db


def _rows():
    return [
        {"station_id": "1", "station": "A", "ts": "2026-10-30T10:00:00+05:30",
         "pm25": 100.0, "pm10": 200.0, "no2": 40.0, "o3": 20.0, "source": "openaq"},
        {"station_id": "1", "station": "A", "ts": "2026-10-30T11:00:00+05:30",
         "pm25": 110.0, "pm10": None, "no2": None, "o3": None, "source": "openaq"},
    ]


def test_duplicates_are_not_inserted(tmp_path):
    path = tmp_path / "aqi.db"
    assert db.insert_readings(_rows(), path) == 2
    assert db.insert_readings(_rows(), path) == 0   # rerun is idempotent
    assert db.count_rows(path) == 2


def test_same_hour_different_source_is_kept(tmp_path):
    path = tmp_path / "aqi.db"
    row = dict(_rows()[0], source="open-meteo")
    db.insert_readings(_rows() + [row], path)
    assert db.count_rows(path) == 3


def test_load_readings_types(tmp_path):
    path = tmp_path / "aqi.db"
    db.insert_readings(_rows(), path)
    df = db.load_readings(path)
    assert len(df) == 2
    assert str(df["ts"].dt.tz) == "Asia/Kolkata"
    assert df["pm10"].isna().sum() == 1


def test_missing_or_empty_db(tmp_path):
    assert db.load_readings(tmp_path / "nope.db").empty
    assert db.count_rows(tmp_path / "nope.db") == 0
    path = tmp_path / "empty.db"
    db.init_db(path)
    assert db.load_readings(path).empty
    assert db.insert_readings([], path) == 0
