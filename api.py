"""A small JSON API (Flask) that serves the latest AQI and the ML forecast.

Run:  pip install -r requirements-ml.txt
      python src/train_forecast.py        (once, to create data/models/)
      python api.py                       (http://127.0.0.1:5000)

Endpoints
  GET /health                       status and the time of the newest reading
  GET /api/latest                   latest AQI per station and the basin-wide figure
  GET /api/forecast?horizon=6|12|24 model forecast of the city AQI that many hours ahead

The database is only read. Models are loaded from data/models/ (files written by src/train_forecast.py).
"""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, request

from src import analysis, config, db, forecast, ml_forecast as ml
from src.fetch_weather import load_weather

CACHE_SECONDS = 60
LATEST_MAX_AGE_H = 3


def create_app(db_path: Path | str | None = None, models_dir: Path | str | None = None) -> Flask:
    app = Flask(__name__)
    db_path = Path(db_path or config.DB_PATH)
    models_dir = Path(models_dir or config.DATA_DIR / "models")
    cache: dict = {"stamp": None, "at": 0.0, "df": None}

    def load_data():
        """Readings with AQI, re-read at most once a minute and only when the file changed."""
        now = time.monotonic()
        stamp = db_path.stat().st_mtime if db_path.exists() else None
        if cache["df"] is None or (now - cache["at"] > CACHE_SECONDS and stamp != cache["stamp"]):
            cache.update(df=analysis.prepare(db.load_readings(db_path)), stamp=stamp, at=now)
        return cache["df"]

    def error(message: str, status: int):
        return jsonify({"error": message}), status

    @app.get("/health")
    def health():
        valid = analysis.with_valid_aqi(load_data())
        newest = None if valid.empty else valid["ts"].max().isoformat()
        return jsonify({"status": "ok", "newest_reading": newest, "models": sorted(p.stem for p in models_dir.glob("forecast_h*.joblib"))})

    @app.get("/api/latest")
    def latest():
        rows = analysis.latest_by_station(load_data(), LATEST_MAX_AGE_H)
        if rows.empty:
            return error("No station has reported recently.", 503)
        stations = [
            {"station": r.label, "area": analysis.station_area(r.station), "aqi": int(r.aqi),
             "category": r.category, "time": r.ts.isoformat()}
            for r in rows.itertuples()
        ]
        basin = float(rows["aqi"].mean())
        return jsonify({"basin_aqi": round(basin), "basin_category": analysis.aqi_category(basin),
                        "stations_reporting": len(stations), "stations": stations})

    @app.get("/api/forecast")
    def forecast_endpoint():
        try:
            horizon = int(request.args.get("horizon", 24))
        except ValueError:
            return error("horizon must be a whole number: 6, 12 or 24.", 400)
        if horizon not in ml.HORIZONS:
            return error(f"horizon must be one of {list(ml.HORIZONS)}.", 400)
        path = models_dir / f"forecast_h{horizon}.joblib"
        if not path.exists():
            return error("No trained model found. Run: python src/train_forecast.py", 503)
        try:
            ml.check_models_usable(models_dir)
        except ml.ModelVersionError as exc:
            return error(str(exc), 503)
        import joblib

        bundle = joblib.load(path)  # local file written by train_forecast.py, not user input
        weather = load_weather() if bundle["uses_weather"] else None
        if bundle["uses_weather"] and weather is None:
            return error("This model needs weather data. Run: python src/fetch_weather.py", 503)
        series = forecast.city_hourly(load_data(), fill_limit=0)
        pred = ml.predict_latest(bundle["model"], series, horizon, weather)
        if pred is None:
            return error("Recent data has gaps, so no forecast can be made right now.", 503)
        last = series.dropna().index[-1]
        return jsonify({
            "horizon_hours": horizon,
            "based_on": last.isoformat(),
            "forecast_for": (last + pd.Timedelta(hours=horizon)).isoformat(),
            "predicted_aqi": round(pred), "category": analysis.aqi_category(pred),
            "model": bundle["method"],
            "backtest_mae": round(bundle["cv_mae"], 1),
            "same_as_now_mae": round(bundle["persistence_mae"], 1),
        })

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000)
