"""Machine-learning forecast of the city-mean AQI (an upgrade of the statistical baseline in forecast.py).

What it does
------------
For a chosen horizon h (for example 6, 12 or 24 hours) it learns to predict the city AQI at time t+h
from what is known at time t: the AQI now, its recent lags, rolling statistics and calendar features
(and, optionally, weather from `src/fetch_weather.py`).

Design choices that matter
--------------------------
* **No look-ahead.** Every feature at time t uses only data up to t (checked in tests/test_ml_forecast.py).
* **Time-ordered evaluation.** Random train/test splits leak the future in time series. Models are scored with
  rolling-origin folds: train on the past, test on the following days, and leave a gap of h hours between them.
* **Honest baselines.** Every model is compared with "same as now" (persistence), "same hour yesterday" and the
  project's own statistical forecast (`src/forecast.py`). A model that cannot beat them is not an improvement.
* **Predict the change, not the level.** The models predict (AQI at t+h) minus (AQI now). Tree models cannot
  predict values outside the range they were trained on, and AQI rises a lot from August to November.

scikit-learn is imported lazily so the rest of the project (and its CI) does not need it.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from src import config, forecast as baseline_forecast

HORIZONS: tuple[int, ...] = (6, 12, 24)
LAGS: tuple[int, ...] = (1, 2, 3, 6, 12, 24, 48)
MIN_TRAIN_ROWS = 300
WEATHER_COLUMNS: tuple[str, ...] = (
    "temperature_2m", "relative_humidity_2m", "wind_speed_10m", "precipitation", "surface_pressure",
)


# ------------------------------------------------------------------ features
def _cyclic(values: pd.Index | np.ndarray, period: int, name: str) -> dict[str, np.ndarray]:
    angle = 2 * np.pi * np.asarray(values) / period
    return {f"{name}_sin": np.sin(angle), f"{name}_cos": np.cos(angle)}


def origin_features(s: pd.Series) -> pd.DataFrame:
    """Features known at each hour t (only data up to and including t is used)."""
    s = s.asfreq("h")
    feats = pd.DataFrame({"aqi_now": s}, index=s.index)
    for lag in LAGS:
        feats[f"aqi_lag_{lag}"] = s.shift(lag)
    feats["aqi_mean_24h"] = s.rolling(24, min_periods=18).mean()
    feats["aqi_std_24h"] = s.rolling(24, min_periods=18).std()
    feats["aqi_change_3h"] = s - s.shift(3)
    for col, vals in _cyclic(s.index.hour, 24, "hour").items():
        feats[col] = vals
    return feats


def _add_target_features(X: pd.DataFrame, horizon: int, weather: pd.DataFrame | None) -> pd.DataFrame:
    """Add features about the hour being predicted (t + horizon), and optional weather."""
    target_time = X.index + pd.Timedelta(hours=horizon)
    for col, vals in _cyclic(target_time.hour, 24, "target_hour").items():
        X[col] = vals
    X["target_is_weekend"] = (target_time.dayofweek >= 5).astype(int)
    if weather is not None:
        # Weather at the origin, and weather at the target hour. The second assumes a weather
        # forecast is available at time t (Open-Meteo provides one), so it is not a leak in practice.
        for c in [c for c in WEATHER_COLUMNS if c in weather.columns]:
            X[f"wx_{c}"] = weather[c].reindex(X.index).to_numpy()
            X[f"wx_{c}_target"] = weather[c].reindex(target_time).to_numpy()
    return X


def build_dataset(
    s: pd.Series, horizon: int, weather: pd.DataFrame | None = None
) -> tuple[pd.DataFrame, pd.Series]:
    """Return (X, y): features at origin t and the AQI at t + horizon. Rows with any gap are dropped."""
    s = s.asfreq("h")
    X = _add_target_features(origin_features(s), horizon, weather)
    y = s.shift(-horizon).rename("aqi_target")
    data = pd.concat([X, y], axis=1).dropna()
    return data.drop(columns="aqi_target"), data["aqi_target"]


# ------------------------------------------------------------ time-ordered folds
def rolling_origin_folds(
    index: pd.DatetimeIndex, horizon: int, n_folds: int = 4, fold_days: int = 7
) -> list[tuple[np.ndarray, np.ndarray]]:
    """(train, test) positions for consecutive test windows at the end of the data.

    A training row at origin t has its target at t + horizon, so training stops `horizon` hours before the
    test window starts. That gap keeps any training target from overlapping the test period.
    """
    step = pd.Timedelta(days=fold_days)
    last = index.max()
    folds = []
    for k in range(n_folds, 0, -1):
        test_end = last - step * (k - 1) + pd.Timedelta(hours=1)  # exclusive
        test_start = test_end - step
        test = np.flatnonzero((index >= test_start) & (index < test_end))
        train = np.flatnonzero(index <= test_start - pd.Timedelta(hours=horizon + 1))
        folds.append((train, test))
    return folds


# ------------------------------------------------------------------- models
class DeltaModel:
    """Wraps a regressor so it predicts the change from the current AQI, and returns a level in 0-500."""

    def __init__(self, estimator):
        self.estimator = estimator
        self.feature_names_: list[str] = []
        self.n_rows_: int = 0

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "DeltaModel":
        self.feature_names_ = list(X.columns)
        self.n_rows_ = len(X)
        self.estimator.fit(X, y - X["aqi_now"])
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        X = X[self.feature_names_]
        return np.clip(X["aqi_now"].to_numpy() + self.estimator.predict(X), 0, 500)


def make_models() -> dict[str, object]:
    """The candidate regressors (fixed settings, chosen in advance; nothing is tuned on the test folds)."""
    from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    return {
        "ridge": make_pipeline(StandardScaler(), Ridge(alpha=10.0)),
        "random_forest": RandomForestRegressor(
            n_estimators=200, min_samples_leaf=5, max_features=0.5, n_jobs=-1, random_state=42
        ),
        "hist_gb": HistGradientBoostingRegressor(
            max_iter=200, learning_rate=0.05, max_depth=3, min_samples_leaf=20, random_state=42
        ),
    }


# ----------------------------------------------------------------- baselines
def _baseline_forecasts(base: pd.Series, origins: pd.DatetimeIndex, cache: dict) -> dict:
    """The project's statistical forecast (src/forecast.py) as it would have been issued at each origin."""
    for t in origins:
        if t not in cache:
            f = baseline_forecast.forecast_24h(base.loc[:t])
            cache[t] = None if f is None else f["aqi"].to_numpy()
    return cache


# ---------------------------------------------------------------- evaluation
def evaluate(
    s: pd.Series,
    horizons: tuple[int, ...] = HORIZONS,
    weather: pd.DataFrame | None = None,
    n_folds: int = 4,
    fold_days: int = 7,
    include_baselines: bool = True,
) -> pd.DataFrame:
    """Rolling-origin predictions for every horizon. One row per test origin, one column per method."""
    s = s.asfreq("h")
    base = s.dropna()
    suffix = "+weather" if weather is not None else ""
    cache: dict = {}
    frames = []
    for h in horizons:
        X, y = build_dataset(s, h, weather)
        for k, (tr, te) in enumerate(rolling_origin_folds(X.index, h, n_folds, fold_days), start=1):
            if len(tr) < MIN_TRAIN_ROWS or len(te) == 0:
                continue
            Xte = X.iloc[te]
            frame = pd.DataFrame(
                {"horizon": h, "fold": k, "origin": Xte.index, "actual": y.iloc[te].to_numpy()}
            )
            if include_baselines:
                frame["persistence"] = Xte["aqi_now"].to_numpy()
                frame["same_hour_yesterday"] = (
                    s.shift(24 - h).reindex(Xte.index).to_numpy() if h <= 24 else np.nan
                )
                _baseline_forecasts(base, Xte.index, cache)
                frame["project_baseline"] = [
                    (cache[t][h - 1] if cache[t] is not None and h <= 24 else np.nan) for t in Xte.index
                ]
            for name, est in make_models().items():
                frame[name + suffix] = DeltaModel(est).fit(X.iloc[tr], y.iloc[tr]).predict(Xte)
            frames.append(frame)
    return pd.concat(frames, ignore_index=True)


METADATA = ("horizon", "fold", "origin", "actual")


def method_columns(preds: pd.DataFrame) -> list[str]:
    return [c for c in preds.columns if c not in METADATA]


def summarize(preds: pd.DataFrame) -> pd.DataFrame:
    """Pooled MAE / RMSE per horizon and method, on rows where every method has a prediction."""
    rows = []
    methods = method_columns(preds)
    for h, grp in preds.groupby("horizon"):
        grp = grp.dropna(subset=methods)
        if grp.empty:
            continue
        persistence_mae = (grp["persistence"] - grp["actual"]).abs().mean() if "persistence" in grp else np.nan
        for m in methods:
            err = grp[m] - grp["actual"]
            rows.append({
                "horizon": h, "method": m, "n": len(grp),
                "mae": err.abs().mean(), "rmse": float(np.sqrt((err**2).mean())),
                "skill_vs_persistence": 1 - err.abs().mean() / persistence_mae,
            })
    return pd.DataFrame(rows)


def folds_won(preds: pd.DataFrame, method: str, versus: str = "persistence") -> pd.DataFrame:
    """For each horizon: in how many test folds does `method` have a lower MAE than `versus`?"""
    rows = []
    for h, grp in preds.groupby("horizon"):
        won, total = 0, 0
        for _, f in grp.dropna(subset=[method, versus]).groupby("fold"):
            total += 1
            won += int((f[method] - f["actual"]).abs().mean() < (f[versus] - f["actual"]).abs().mean())
        rows.append({"horizon": h, "folds_won": won, "folds": total})
    return pd.DataFrame(rows)


# ------------------------------------------------------------ final training
def fit_final(s: pd.Series, horizon: int, method: str, weather: pd.DataFrame | None = None) -> DeltaModel:
    """Fit one named model on all available data."""
    name = method.replace("+weather", "")
    X, y = build_dataset(s, horizon, weather)
    return DeltaModel(make_models()[name]).fit(X, y)


MAX_ORIGIN_AGE_H = 6


def predict_latest(model: DeltaModel, s: pd.Series, horizon: int, weather: pd.DataFrame | None = None) -> float | None:
    """Predict the AQI `horizon` hours after the newest hour of `s` that has complete features.

    Returns None when that hour is more than MAX_ORIGIN_AGE_H hours older than the end of the series
    (the recent data has gaps) or when its features are incomplete.
    """
    s = s.asfreq("h")
    X = _add_target_features(origin_features(s), horizon, weather)
    X = X[X["aqi_now"].notna()]
    if X.empty or (s.index[-1] - X.index[-1]) > pd.Timedelta(hours=MAX_ORIGIN_AGE_H):
        return None
    last = X.iloc[[-1]]
    if not set(model.feature_names_) <= set(last.columns) or last[model.feature_names_].isna().any(axis=None):
        return None
    return float(model.predict(last)[0])


# ------------------------------------------------- model files and library versions
# A joblib file is only guaranteed to load (and predict the same) with the scikit-learn version that wrote it.
# train_forecast.py writes data/models/meta.json next to the models; everything that loads a model checks it first.
META_NAME = "meta.json"
RETRAIN_HINT = "run python src/train_forecast.py to retrain."


class ModelVersionError(RuntimeError):
    """The saved models cannot be trusted with the installed libraries (or have no version record)."""


def installed_sklearn_version() -> str:
    import sklearn

    return sklearn.__version__


def write_meta(models_dir: Path | str, models: dict[int, dict]) -> dict:
    """Write models_dir/meta.json. `models` maps horizon -> {"method", "rows_used", "feature_names"}."""
    import sklearn

    meta = {
        "sklearn_version": sklearn.__version__,
        "numpy_version": np.__version__,
        "training_date": datetime.now(config.IST).isoformat(timespec="seconds"),
        "models": {str(h): models[h] for h in sorted(models)},
    }
    models_dir = Path(models_dir)
    models_dir.mkdir(parents=True, exist_ok=True)
    (models_dir / META_NAME).write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def check_models_usable(models_dir: Path | str) -> None:
    """Raise ModelVersionError unless meta.json exists and its scikit-learn version equals the installed one."""
    path = Path(models_dir) / META_NAME
    try:
        trained = json.loads(path.read_text(encoding="utf-8"))["sklearn_version"]
    except (OSError, ValueError, KeyError, TypeError):
        raise ModelVersionError(f"Models have no readable {META_NAME} (trained before version tracking); {RETRAIN_HINT}") from None
    if str(trained) != installed_sklearn_version():
        raise ModelVersionError(f"Models were trained with scikit-learn {trained}; {RETRAIN_HINT}")
