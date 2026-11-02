"""Tests for the Flask API and the key_findings helper, on a small synthetic database."""
from __future__ import annotations

import json
import shutil

import numpy as np
import pandas as pd
import pytest

from src import analysis, config, db, forecast, key_findings

flask = pytest.importorskip("flask")
pytest.importorskip("sklearn")
import joblib  # noqa: E402

from api import create_app  # noqa: E402
from src import ml_forecast as ml  # noqa: E402


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    """A 14-day database for 3 stations plus a trained horizon-6 model, all in a temp folder."""
    tmp = tmp_path_factory.mktemp("api")
    db_path, models = tmp / "aqi.db", tmp / "models"
    rng = np.random.default_rng(1)
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
    joblib.dump({"model": ml.fit_final(series, 6, "ridge"), "horizon": 6, "method": "ridge", "uses_weather": False,
                 "cv_mae": 9.5, "persistence_mae": 14.0, "trained_through": str(series.index.max())},
                models / "forecast_h6.joblib")
    ml.write_meta(models, {6: {"method": "ridge", "rows_used": 1, "feature_names": []}})   # the API refuses models without it
    return db_path, models


@pytest.fixture()
def client(world):
    db_path, models = world
    return create_app(db_path, models).test_client()


def test_health_reports_the_newest_reading_and_the_models(client):
    body = client.get("/health").get_json()
    assert body["status"] == "ok"
    assert body["newest_reading"].startswith("2026-10-14")
    assert body["models"] == ["forecast_h6"]


def test_latest_returns_every_reporting_station_and_a_basin_figure(client):
    body = client.get("/api/latest").get_json()
    assert body["stations_reporting"] == 3 == len(body["stations"])
    assert 0 <= body["basin_aqi"] <= 500 and body["basin_category"]
    assert {"station", "area", "aqi", "category", "time"} <= set(body["stations"][0])


def test_forecast_returns_a_prediction_with_its_backtest_error(client):
    r = client.get("/api/forecast?horizon=6")
    body = r.get_json()
    assert r.status_code == 200
    assert body["horizon_hours"] == 6 and body["model"] == "ridge"
    assert 0 <= body["predicted_aqi"] <= 500
    assert (body["backtest_mae"], body["same_as_now_mae"]) == (9.5, 14.0)
    assert pd.Timestamp(body["forecast_for"]) - pd.Timestamp(body["based_on"]) == pd.Timedelta(hours=6)


def test_bad_horizons_are_rejected_with_400(client):
    assert client.get("/api/forecast?horizon=7").status_code == 400
    assert client.get("/api/forecast?horizon=abc").status_code == 400


def test_a_horizon_without_a_trained_model_gives_503_and_a_hint(client):
    r = client.get("/api/forecast?horizon=12")
    assert r.status_code == 503
    assert "train_forecast" in r.get_json()["error"]


def test_key_findings_computes_on_a_small_database(world):
    k = key_findings.compute(analysis.prepare(db.load_readings(world[0])))
    assert k["station_hours"] > 0 and "2026-10" in k["monthly"]
    assert k["worst_day"] is None            # needs 15 stations a day; the test data has 3
    assert k["latest_n"] == 3


# ------------------------------------------------ scikit-learn version guard (meta.json)
def _client_with_meta(world, tmp_path, meta: dict | None):
    """A client whose models folder is a copy of the fixture's, with meta.json replaced (or removed if None)."""
    db_path, models = world
    copy = tmp_path / "models"
    shutil.copytree(models, copy)
    if meta is None:
        (copy / ml.META_NAME).unlink()
    else:
        (copy / ml.META_NAME).write_text(json.dumps(meta), encoding="utf-8")
    return create_app(db_path, copy).test_client()


def test_models_trained_with_another_sklearn_version_give_503(world, tmp_path):
    r = _client_with_meta(world, tmp_path, {"sklearn_version": "0.0.1"}).get("/api/forecast?horizon=6")
    assert r.status_code == 503
    assert r.get_json()["error"] == "Models were trained with scikit-learn 0.0.1; run python src/train_forecast.py to retrain."


def test_models_without_meta_json_give_503(world, tmp_path):
    r = _client_with_meta(world, tmp_path, None).get("/api/forecast?horizon=6")
    assert r.status_code == 503
    assert "train_forecast.py" in r.get_json()["error"]


def test_models_with_a_matching_meta_json_are_used(world, tmp_path):
    import sklearn

    r = _client_with_meta(world, tmp_path, {"sklearn_version": sklearn.__version__}).get("/api/forecast?horizon=6")
    assert r.status_code == 200
