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


def test_latest_by_station_ignores_stale_stations():
    import pandas as pd
    from src import analysis

    def rows(sid, name, end, hours=30):
        ts = pd.date_range(end=end, periods=hours, freq="h", tz="Asia/Kolkata")
        return pd.DataFrame({"station_id": sid, "station": name, "ts": ts, "pm25": 60.0,
                             "pm10": 90.0, "no2": 20.0, "o3": 20.0, "source": "openaq"})

    now = pd.Timestamp("2026-10-31 15:00", tz="Asia/Kolkata")
    df = pd.concat([rows("1", "Active", now), rows("2", "Offline since days", now - pd.Timedelta(hours=60))])
    out = analysis.latest_by_station(analysis.prepare(df))
    assert list(out["station"]) == ["Active"]
    both = analysis.latest_by_station(analysis.prepare(df), max_age_hours=None)
    assert len(both) == 2


# ---------------------------------------------------------------- peak lens
def test_extended_matches_cpcb_below_cap_and_exceeds_it_above():
    assert analysis.compute_aqi_extended(150, None) == analysis.compute_aqi(150, None)
    assert analysis.compute_aqi(993, None) == 500                 # CPCB value stays capped
    assert analysis.compute_aqi_extended(993, None) > 500         # uncapped keeps climbing
    assert analysis.compute_aqi_extended(380, None) == 500        # continuous at the CPCB top


def test_peak_lens_exposes_spike_and_coverage():
    ts = pd.date_range("2026-11-08 20:00", periods=30, freq="h", tz=config.IST)
    rows = []
    for i, t in enumerate(ts):
        for sid in ("a", "b", "c"):
            if i == 25 and sid != "a":            # at the spike two stations go offline
                continue
            rows.append({"station_id": sid, "station": sid, "ts": t, "source": "openaq",
                         "pm25": 900.0 if i == 25 else 100.0, "pm10": None, "no2": None, "o3": None})
    lens = analysis.peak_lens(analysis.prepare(pd.DataFrame(rows)), hours=30)
    s = analysis.peak_summary(lens)
    assert s["pm25_max"] == 900.0
    assert s["aqi_hourly"] == 500.0 and s["aqi_ext_max"] > 500
    assert s["stations_at_peak"] == 1 and s["stations_typical"] == 3


def test_diwali_night_benchmark_like_for_like():
    ts = pd.date_range("2026-10-25 00:00", "2026-11-10 08:00", freq="h", tz=config.IST)
    rows = []
    for t in ts:
        in_night = pd.Timestamp("2026-11-08 18:00", tz=config.IST) <= t < pd.Timestamp("2026-11-09 12:00", tz=config.IST)
        gap = t.date() == pd.Timestamp("2026-11-03").date()          # one baseline day with no data
        for sid in range(6):
            if gap:
                continue
            rows.append({"station_id": str(sid), "station": f"s{sid}", "ts": t, "source": "openaq",
                         "pm25": 300.0 if in_night else 100.0, "pm10": None, "no2": None, "o3": None})
    res = analysis.diwali_night_benchmark(pd.DataFrame(rows))
    assert res is not None
    assert res["baseline_mean"] == 100.0 and res["event_mean"] == 300.0 and res["change_pct"] == 200.0
    # the 3 Nov gap leaves only 6 valid hours in the window that opens on 2 Nov, so that window is skipped
    assert res["baseline_days"] == 6 and res["skipped_days"] == ["2026-11-02"]
    # festival night not collected yet -> no result instead of a made-up one
    early = pd.DataFrame(rows)
    early = early[early["ts"] < pd.Timestamp("2026-11-08 20:00", tz=config.IST)]
    assert analysis.diwali_night_benchmark(early) is None
