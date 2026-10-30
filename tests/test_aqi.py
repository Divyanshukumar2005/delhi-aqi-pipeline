"""Tests for the CPCB AQI calculation and the insight helpers."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src import analysis, config


# Known pairs. The first two are CPCB's own worked examples.
@pytest.mark.parametrize(
    ("conc", "pollutant", "expected"),
    [
        (45, "pm25", 75),     # CPCB example: 50 + (45-30)*50/30
        (150, "pm25", 323),   # CPCB example: 300 + (150-120)*100/130
        (0, "pm25", 0),
        (30, "pm25", 50),     # top of Good
        (60, "pm25", 100),    # top of Satisfactory
        (90, "pm25", 200),
        (250, "pm25", 400),
        (80, "pm10", 80),     # 50 + (80-50)*50/50
        (250, "pm10", 200),
        (400, "pm10", 363),   # 300 + (400-350)*100/80 = 362.5 -> rounds half up
    ],
)
def test_sub_index_known_values(conc, pollutant, expected):
    assert analysis.compute_aqi(conc if pollutant == "pm25" else None,
                                conc if pollutant == "pm10" else None) == expected


def test_aqi_is_max_of_sub_indices():
    # PM2.5 45 -> 75, PM10 80 -> 80 ; AQI = 80
    assert analysis.compute_aqi(45, 80) == 80


def test_aqi_capped_at_500_and_missing_inputs():
    assert analysis.compute_aqi(1000, None) == 500
    assert analysis.compute_aqi(None, None) is None
    assert analysis.compute_aqi(np.nan, np.nan) is None
    assert analysis.sub_index(-5, "pm25") is None


@pytest.mark.parametrize(
    ("aqi", "category"),
    [(0, "Good"), (50, "Good"), (51, "Satisfactory"), (100, "Satisfactory"),
     (101, "Moderate"), (200, "Moderate"), (250, "Poor"), (301, "Very Poor"),
     (401, "Severe"), (500, "Severe")],
)
def test_categories(aqi, category):
    assert analysis.aqi_category(aqi) == category


def _hourly(n_hours: int, pm25: float = 45.0, start: str = "2026-10-01 00:00",
            station: str = "s1") -> pd.DataFrame:
    ts = pd.date_range(start, periods=n_hours, freq="h", tz=config.IST)
    return pd.DataFrame({"station_id": station, "station": station, "ts": ts,
                         "pm25": pm25, "pm10": np.nan, "no2": 20.0, "o3": 30.0,
                         "source": "openaq"})


def test_rolling_window_needs_16_hours():
    out = analysis.add_aqi(_hourly(20))
    assert out["aqi"].iloc[:15].isna().all()      # hours 1-15: not enough data
    assert out["aqi"].iloc[15] == 75               # 16th hour: first valid AQI
    assert out["category"].iloc[19] == "Satisfactory"


def test_rolling_ignores_missing_hours():
    df = _hourly(24)
    df.loc[df.index[:10], "pm25"] = np.nan          # only 14 valid hours in the window
    out = analysis.add_aqi(df)
    assert out["aqi"].isna().all()


def test_empty_frame_is_safe():
    out = analysis.prepare(pd.DataFrame(columns=["station_id", "station", "ts", "pm25",
                                                 "pm10", "no2", "o3", "source"]))
    assert out.empty
    assert analysis.peak_and_cleanest_hour(out) is None
    assert analysis.weekday_weekend_test(out) is None
    assert analysis.diwali_comparison(out) is None
    assert analysis.pct_poor_or_worse(out) is None


def test_weekday_weekend_and_diwali_insights():
    rng = np.random.default_rng(0)
    df = _hourly(24 * 40, start="2026-10-15 00:00")
    weekend = df["ts"].dt.day_of_week >= 5
    df["pm25"] = np.where(weekend, 60.0, 120.0) + rng.normal(0, 5, len(df))
    out = analysis.prepare(df)
    result = analysis.weekday_weekend_test(out)
    assert result is not None and result["significant"] and result["diff"] > 0
    assert analysis.diwali_comparison(out) is not None


def test_pm25_no2_correlation():
    df = _hourly(100)
    df["pm25"] = np.arange(100, dtype=float)
    df["no2"] = df["pm25"] * 0.5 + 3
    result = analysis.pm25_no2_correlation(df)
    assert result is not None and result["r"] == pytest.approx(1.0)
