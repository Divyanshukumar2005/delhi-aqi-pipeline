"""data/ml_forecast.json: the export must write a useful file when it can, and {"available": false} (never crash) when not."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("sklearn")
import joblib  # noqa: E402

from src import analysis, config, db, export_json, forecast, ml_forecast as ml  # noqa: E402


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    """A 14-day database for 3 stations and a trained horizon-6 and horizon-12 model with meta.json."""
    tmp = tmp_path_factory.mktemp("exportml")
    db_path, models = tmp / "aqi.db", tmp / "models"
    rng = np.random.default_rng(2)
    idx = pd.date_range("2026-10-01", periods=14 * 24, freq="h", tz=config.IST)
    rows = []
    for sid in ("a", "b", "c"):
        base = 70 + 30 * np.sin(2 * np.pi * np.arange(len(idx)) / 24) + rng.normal(0, 5, len(idx))
        for ts, v in zip(idx, base):
            rows.append({"station_id": sid, "station": f"Station {sid.upper()}, Delhi", "ts": ts.isoformat(),
                         "pm25": float(v), "pm10": float(v * 1.6), "no2": 40.0, "o3": 30.0, "source": "openaq"})
    db.insert_readings(rows, db_path)
    series = forecast.city_hourly(analysis.prepare(db.load_readings(db_path)), fill_limit=0)
    models.mkdir()
    for h, cv in ((6, 9.54), (12, 14.0)):
        joblib.dump({"model": ml.fit_final(series, h, "ridge"), "horizon": h, "method": "ridge", "uses_weather": False,
                     "cv_mae": cv, "persistence_mae": cv + 5, "trained_through": str(series.index.max())},
                    models / f"forecast_h{h}.joblib")
    ml.write_meta(models, {6: {"method": "ridge", "rows_used": 1, "feature_names": []},
                           12: {"method": "ridge", "rows_used": 1, "feature_names": []}})
    return db_path, models, series.dropna().index[-1]


def run(world, tmp_path, hours_after_origin=1.0, models=None, db_path=None):
    db0, models0, origin = world
    out = tmp_path / "ml_forecast.json"
    payload = export_json.export_ml_forecast(db_path or db0, models or models0, out,
                                             now=(origin + pd.Timedelta(hours=hours_after_origin)).to_pydatetime())
    assert json.loads(out.read_text()) == payload       # what is returned is what is on disk
    return payload


def test_a_fresh_export_has_the_documented_fields(world, tmp_path):
    p = run(world, tmp_path)
    assert p["available"] is True
    assert {"generated_at", "origin_ts", "current_aqi", "horizons"} <= set(p)
    assert pd.Timestamp(p["origin_ts"]) == world[2]
    assert 0 <= p["current_aqi"] <= 500
    assert [h["h"] for h in p["horizons"]] == [6, 12]          # no model file for 24 h, so it is left out
    first = p["horizons"][0]
    assert {"h", "predicted_aqi", "category", "model", "backtest_mae"} <= set(first)
    assert first["model"] == "ridge" and first["backtest_mae"] == 9.5 and first["persistence_mae"] == 14.5
    assert first["category"] == analysis.aqi_category(first["predicted_aqi"])


def test_stale_data_gives_available_false_not_a_crash(world, tmp_path):
    p = run(world, tmp_path, hours_after_origin=export_json.ML_MAX_AGE_H + 5)
    assert p["available"] is False and "stale" in p["reason"]
    assert "horizons" not in p


def test_models_from_another_sklearn_version_give_available_false(world, tmp_path):
    models = tmp_path / "models"
    models.mkdir()
    for f in world[1].glob("forecast_h*.joblib"):
        (models / f.name).write_bytes(f.read_bytes())
    (models / "meta.json").write_text(json.dumps({"sklearn_version": "0.0.1"}), encoding="utf-8")
    p = run(world, tmp_path, models=models)
    assert p["available"] is False
    assert p["reason"] == "Models were trained with scikit-learn 0.0.1; run python src/train_forecast.py to retrain."


def test_missing_models_give_available_false(world, tmp_path):
    p = run(world, tmp_path, models=tmp_path / "nothing_here")
    assert p["available"] is False and "train_forecast.py" in p["reason"]


def test_an_empty_database_gives_available_false(world, tmp_path):
    p = run(world, tmp_path, db_path=tmp_path / "missing.db")
    assert p["available"] is False and "No usable" in p["reason"]


def test_a_corrupt_model_file_is_reported_not_raised(world, tmp_path):
    models = tmp_path / "models"
    models.mkdir()
    (models / "forecast_h6.joblib").write_bytes(b"garbage")
    (models / "meta.json").write_bytes((world[1] / "meta.json").read_bytes())
    p = run(world, tmp_path, models=models)
    assert p["available"] is False and p["reason"]
