"""city_hourly must not turn a half-collected hour into a "city" value."""
import pandas as pd

from src import config, forecast


def frame(counts: dict[str, int]) -> pd.DataFrame:
    """One AQI row per station for each hour; counts maps an hour label to how many stations reported it."""
    rows = []
    for hour, n in counts.items():
        for i in range(n):
            rows.append({"ts": pd.Timestamp(hour, tz=config.IST), "station_id": f"s{i}", "aqi": 100.0 + 10 * i})
    return pd.DataFrame(rows)


def hours(n_hours: int, stations: int = 10, start: str = "2026-11-01 00:00") -> dict[str, int]:
    idx = pd.date_range(start, periods=n_hours, freq="h")
    return {str(t): stations for t in idx}


def test_a_partly_collected_last_hour_is_dropped():
    counts = hours(30)
    counts["2026-11-02 06:00"] = 1                       # only one station has reported the newest hour
    s = forecast.city_hourly(frame(counts))
    assert pd.Timestamp("2026-11-02 06:00", tz=config.IST) not in s.index
    assert s.index.max() == pd.Timestamp("2026-11-02 05:00", tz=config.IST)


def test_a_small_selection_of_stations_still_works():
    s = forecast.city_hourly(frame(hours(30, stations=2)))
    assert len(s) == 30                                  # the threshold adapts to the usual number of stations


def test_short_gaps_are_filled_and_long_gaps_are_not():
    counts = hours(40)
    for h in pd.date_range("2026-11-01 10:00", periods=2, freq="h"):  # 2 missing hours: filled
        del counts[str(h)]
    for h in pd.date_range("2026-11-01 20:00", periods=6, freq="h"):  # 6 missing hours: left empty
        del counts[str(h)]
    s = forecast.city_hourly(frame(counts))
    assert pd.Timestamp("2026-11-01 10:00", tz=config.IST) in s.index
    assert pd.Timestamp("2026-11-01 22:00", tz=config.IST) not in s.index
    no_fill = forecast.city_hourly(frame(counts), fill_limit=0)
    assert pd.Timestamp("2026-11-01 10:00", tz=config.IST) not in no_fill.index


def test_empty_input_gives_an_empty_series():
    assert forecast.city_hourly(pd.DataFrame({"ts": [], "station_id": [], "aqi": []})).empty
