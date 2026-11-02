"""Export the latest readings from SQLite to JSON for the React dashboard.

Why: the web dashboard cannot open a SQLite file in the browser, so after every
collection run we write two small JSON files that it can fetch:

    data/readings.json   last N days of hourly readings (compact)
    data/stations.json   already written by discover.py (left untouched)
    data/ml_forecast.json  latest 6/12/24 h ML forecast from the saved models (needs scikit-learn; see below)

Run from the repo root:
    python src/export_json.py              # readings.json and ml_forecast.json
    python src/export_json.py --skip-ml    # readings.json only (no scikit-learn needed)
    python src/export_json.py --ml-only    # ml_forecast.json only

The ML step never raises: if the models, scikit-learn, the data or the model/library versions are not usable,
it writes {"available": false, "reason": ...} so the dashboard can say "not available yet".
"""
from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Allow `python src/export_json.py` as well as `python -m src.export_json`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config  # noqa: E402

logger = logging.getLogger(__name__)

EXPORT_DAYS = 14                      # enough for 24h averages + trends, keeps the file small
OUT_PATH = Path("data/readings.json")
ML_OUT_PATH = Path("data/ml_forecast.json")
MODELS_DIR = config.DATA_DIR / "models"
ML_MAX_AGE_H = 12                     # newest city reading older than this -> the forecast is not published


def export_readings(db_path: Path | str = config.DB_PATH,
                    out_path: Path | str = OUT_PATH,
                    days: int = EXPORT_DAYS) -> int:
    """Write the last `days` days of readings to JSON and return the row count.

    The window is measured from the NEWEST timestamp in the DB (not from the
    wall clock), so the export still works if a collection run was missed.
    """
    conn = sqlite3.connect(db_path)
    try:
        newest = conn.execute("SELECT MAX(ts) FROM readings").fetchone()[0]
        if newest is None:
            raise RuntimeError("readings table is empty, nothing to export")
        # ts is ISO text in IST; SQLite's datetime() understands the +05:30 offset
        # and converts to UTC, so we compare in UTC for correctness.
        rows = conn.execute(
            """
            SELECT station_id, station, ts, pm25, pm10, no2, o3, source
            FROM readings
            WHERE datetime(ts) >= datetime(?, ?)
            ORDER BY ts
            """,
            (newest, f"-{int(days)} days"),
        ).fetchall()
    finally:
        conn.close()

    keys = ["station_id", "station", "ts", "pm25", "pm10", "no2", "o3", "source"]
    records = [dict(zip(keys, r)) for r in rows]

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # separators=(",", ":") removes spaces -> roughly 20% smaller file.
    out_path.write_text(json.dumps(records, separators=(",", ":")), encoding="utf-8")
    logger.info("Exported %d rows (%s days) to %s", len(records), days, out_path)
    return len(records)


class MlUnavailable(Exception):
    """Raised inside the ML export for an expected reason (stale data, no model); the message is published."""


def build_ml_forecast(db_path: Path | str = config.DB_PATH,
                      models_dir: Path | str = MODELS_DIR,
                      weather_path: Path | str | None = None,
                      now: datetime | None = None) -> dict:
    """Latest forecast from the saved models, as the dict written to data/ml_forecast.json.

    A horizon is included when its model file exists and predict_latest returns a value; the forecast is
    "available" when at least one horizon is. Raises MlUnavailable (or any other error) otherwise.
    """
    import joblib

    from src import analysis, db, forecast, ml_forecast as ml
    from src.fetch_weather import WEATHER_PATH, load_weather

    models_dir = Path(models_dir)
    try:
        ml.check_models_usable(models_dir)
    except ml.ModelVersionError as exc:
        raise MlUnavailable(str(exc)) from None
    series = forecast.city_hourly(analysis.prepare(db.load_readings(db_path)), fill_limit=0)
    if series.dropna().empty:
        raise MlUnavailable("No usable city AQI data in the database.")
    now = now or datetime.now(config.IST)
    origin = series.dropna().index[-1]
    age_h = (now - origin.to_pydatetime()).total_seconds() / 3600
    if age_h > ML_MAX_AGE_H:
        raise MlUnavailable(f"Latest city reading is {age_h:.0f} h old (limit {ML_MAX_AGE_H} h), so the forecast is stale.")

    weather = None
    horizons = []
    for h in ml.HORIZONS:
        path = models_dir / f"forecast_h{h}.joblib"
        if not path.exists():
            continue
        bundle = joblib.load(path)  # local file written by train_forecast.py, not user input
        if bundle["uses_weather"] and weather is None:
            weather = load_weather(weather_path or WEATHER_PATH)
        wx = weather if bundle["uses_weather"] else None
        if bundle["uses_weather"] and wx is None:
            continue                  # needs weather.csv, which is missing
        pred = ml.predict_latest(bundle["model"], series, h, wx)
        if pred is None:
            continue
        aqi = int(round(pred))
        horizons.append({
            "h": h, "predicted_aqi": aqi, "category": analysis.aqi_category(aqi), "model": bundle["method"],
            "backtest_mae": round(float(bundle["cv_mae"]), 1),
            "persistence_mae": round(float(bundle["persistence_mae"]), 1),
        })
    if not horizons:
        raise MlUnavailable("No horizon could be predicted: model files, weather data or recent hourly data are missing or have gaps.")
    return {
        "available": True,
        "generated_at": now.isoformat(timespec="seconds"),
        "origin_ts": origin.isoformat(),
        "current_aqi": int(round(float(series.dropna().iloc[-1]))),
        "backtest": "28-day back-test (4 rolling 7-day windows)",
        "horizons": horizons,
    }


def export_ml_forecast(db_path: Path | str = config.DB_PATH,
                       models_dir: Path | str = MODELS_DIR,
                       out_path: Path | str = ML_OUT_PATH,
                       weather_path: Path | str | None = None,
                       now: datetime | None = None) -> dict:
    """Write data/ml_forecast.json. Never raises: any failure is written as {"available": false, "reason": ...}."""
    try:
        payload = build_ml_forecast(db_path, models_dir, weather_path, now)
    except Exception as exc:  # noqa: BLE001 - the dashboard export must not break the pipeline
        reason = str(exc) if isinstance(exc, MlUnavailable) else f"{type(exc).__name__}: {exc}"
        logger.warning("ML forecast not exported: %s", reason)
        stamp = (now or datetime.now(config.IST)).isoformat(timespec="seconds")
        payload = {"available": False, "generated_at": stamp, "reason": reason}
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    logger.info("Wrote %s (available=%s)", out_path, payload["available"])
    return payload


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Export dashboard JSON files from the database.")
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--skip-ml", action="store_true", help="only data/readings.json")
    group.add_argument("--ml-only", action="store_true", help="only data/ml_forecast.json")
    args = ap.parse_args(argv)
    if not args.ml_only:
        export_readings()
    if not args.skip_ml:
        export_ml_forecast()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
