"""Simple 24-hour city AQI forecast (statistical baseline, not a trained model).

Idea: the next hours look like "now", fading (half-life 12 h) towards the recent
24-hour level plus the typical hour-of-day pattern of the last 14 days.
The band is an ~80% range taken from how much AQI usually changes in 24 h.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src import analysis


def city_hourly(df: pd.DataFrame) -> pd.Series:
    """Hourly city-mean AQI (average of all selected stations), IST index."""
    valid = analysis.with_valid_aqi(df)
    if valid.empty:
        return pd.Series(dtype=float)
    s = valid.groupby("ts")["aqi"].mean().sort_index()
    return s.resample("1h").mean().interpolate(limit=3).dropna()


def forecast_24h(s: pd.Series, horizon: int = 24) -> pd.DataFrame | None:
    """Return columns ts, aqi, lo, hi for the next `horizon` hours (None if < 72 h of data)."""
    if len(s) < 72:
        return None
    recent = s.iloc[-24 * 14:]
    profile = recent.groupby(recent.index.hour).mean() - recent.mean()
    level, anchor = recent.iloc[-24:].mean(), s.iloc[-1]
    sigma = s.diff(24).dropna().std() / np.sqrt(2)
    idx = pd.date_range(s.index[-1] + pd.Timedelta(hours=1), periods=horizon, freq="h")
    rows = []
    for k, t in enumerate(idx, start=1):
        w = 0.5 ** (k / 12)
        pred = w * anchor + (1 - w) * (level + profile.get(t.hour, 0.0))
        band = 1.28 * sigma * np.sqrt(k / 24)
        rows.append({"ts": t, "aqi": pred, "lo": pred - band, "hi": pred + band})
    return _clip(pd.DataFrame(rows))


def _clip(f: pd.DataFrame) -> pd.DataFrame:
    for c in ("aqi", "lo", "hi"):
        f[c] = f[c].clip(0, 500)
    return f
