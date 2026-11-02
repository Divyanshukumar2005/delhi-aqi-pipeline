"""Tests for the ML forecast helpers. Features, splits and the weather client need only pandas;
the model tests are skipped automatically when scikit-learn is not installed."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src import config, fetch_weather, ml_forecast as ml


def synthetic_series(days: int = 60, seed: int = 0) -> pd.Series:
    """Hourly AQI-like series: daily cycle + slow trend + noise, on an IST index."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2026-08-01", periods=days * 24, freq="h", tz=config.IST)
    hours = np.arange(len(idx))
    noise = np.zeros(len(idx))
    for i in range(1, len(idx)):
        noise[i] = 0.9 * noise[i - 1] + rng.normal(0, 4)
    return pd.Series(120 + 0.05 * hours + 30 * np.sin(2 * np.pi * hours / 24) + noise, index=idx, name="aqi")


# ------------------------------------------------------------ features (no sklearn)
def test_features_use_only_the_past():
    s = synthetic_series()
    t = s.index[500]
    changed = s.copy()
    changed.iloc[501:] += 1000          # alter everything after t
    a = ml.origin_features(s).loc[t]
    b = ml.origin_features(changed).loc[t]
    pd.testing.assert_series_equal(a, b)


def test_target_is_the_value_horizon_hours_later():
    s = synthetic_series()
    X, y = ml.build_dataset(s, horizon=6)
    t = X.index[10]
    assert y.loc[t] == pytest.approx(s.loc[t + pd.Timedelta(hours=6)])


def test_rows_with_gaps_are_dropped():
    s = synthetic_series()
    s.iloc[300:310] = np.nan
    X, y = ml.build_dataset(s, horizon=6)
    assert not X.isna().any(axis=None) and not y.isna().any()
    assert s.index[305] not in X.index


def test_folds_are_time_ordered_with_a_gap():
    s = synthetic_series()
    X, _ = ml.build_dataset(s, horizon=24)
    for train, test in ml.rolling_origin_folds(X.index, horizon=24, n_folds=3, fold_days=5):
        assert len(train) and len(test)
        # the last training target (origin + 24 h) is still before the first test origin
        assert X.index[train].max() + pd.Timedelta(hours=24) < X.index[test].min()
    ends = [X.index[t].max() for _, t in ml.rolling_origin_folds(X.index, 24, 3, 5)]
    assert ends == sorted(ends)          # test windows move forward in time


def test_weather_columns_are_added_for_origin_and_target_hour():
    s = synthetic_series()
    idx = pd.date_range(s.index[0], s.index[-1] + pd.Timedelta(days=2), freq="h")
    weather = pd.DataFrame({"temperature_2m": np.arange(len(idx), dtype=float),
                            "wind_speed_10m": 3.0}, index=idx)
    X, _ = ml.build_dataset(s, horizon=6, weather=weather)
    assert {"wx_temperature_2m", "wx_temperature_2m_target", "wx_wind_speed_10m"} <= set(X.columns)
    t = X.index[20]
    assert X.loc[t, "wx_temperature_2m_target"] - X.loc[t, "wx_temperature_2m"] == 6


# --------------------------------------------------------- weather client (no network)
SAMPLE = {"hourly": {
    "time": ["2026-11-01T00:00", "2026-11-01T01:00"],
    "temperature_2m": [19.5, 19.0], "relative_humidity_2m": [60, 62], "wind_speed_10m": [4.0, 3.5],
    "precipitation": [0.0, 0.0], "surface_pressure": [1008.0, 1008.2],
}}


def test_parse_weather_gives_ist_index_and_numeric_columns():
    df = fetch_weather.parse(SAMPLE)
    assert list(df.columns) == list(ml.WEATHER_COLUMNS)
    assert str(df.index.tz) == "Asia/Kolkata" and df.index[0].hour == 0
    assert df["temperature_2m"].iloc[0] == 19.5


def test_parse_weather_rejects_a_response_without_hourly_data():
    with pytest.raises(ValueError):
        fetch_weather.parse({"error": True})


def test_save_weather_merges_and_keeps_newer_values(tmp_path):
    path = tmp_path / "weather.csv"
    fetch_weather.save_weather(fetch_weather.parse(SAMPLE), path)
    newer = {"hourly": {**SAMPLE["hourly"], "time": ["2026-11-01T01:00", "2026-11-01T02:00"],
                        "temperature_2m": [25.0, 24.0]}}
    merged = fetch_weather.save_weather(fetch_weather.parse(newer), path)
    assert len(merged) == 3
    assert merged["temperature_2m"].tolist() == [19.5, 25.0, 24.0]
    assert len(fetch_weather.load_weather(path)) == 3


# -------------------------------------------------------------- models (need sklearn)
def test_delta_model_predicts_levels_in_range_and_beats_persistence_on_a_cycle():
    pytest.importorskip("sklearn")
    s = synthetic_series()
    X, y = ml.build_dataset(s, horizon=6)
    split = int(len(X) * 0.8)
    model = ml.DeltaModel(ml.make_models()["ridge"]).fit(X.iloc[:split], y.iloc[:split])
    pred = model.predict(X.iloc[split:])
    assert pred.min() >= 0 and pred.max() <= 500
    assert np.abs(pred - y.iloc[split:]).mean() < np.abs(X["aqi_now"].iloc[split:] - y.iloc[split:]).mean()


def test_evaluate_returns_all_methods_and_summary():
    pytest.importorskip("sklearn")
    preds = ml.evaluate(synthetic_series(), horizons=(6,), n_folds=2, fold_days=3)
    for col in ["persistence", "same_hour_yesterday", "project_baseline", "ridge", "random_forest", "hist_gb"]:
        assert col in preds.columns
    summary = ml.summarize(preds)
    assert set(summary["method"]) >= {"persistence", "ridge"}
    assert summary.loc[summary["method"] == "persistence", "skill_vs_persistence"].iloc[0] == pytest.approx(0)


def test_predict_latest_skips_an_empty_last_hour_but_not_a_long_gap():
    pytest.importorskip("sklearn")
    s = synthetic_series()
    model = ml.fit_final(s, 6, "ridge")
    assert isinstance(ml.predict_latest(model, s, 6), float)
    last_hour_missing = s.copy()
    last_hour_missing.iloc[-1] = np.nan            # a partly collected newest hour
    assert isinstance(ml.predict_latest(model, last_hour_missing, 6), float)
    long_gap = s.copy()
    long_gap.iloc[-10:] = np.nan                   # 10 hours with no data: too stale
    assert ml.predict_latest(model, long_gap, 6) is None
