"""AQI calculation (CPCB NAQI) and the insight functions used by the dashboard.

Every insight function returns None when there is not enough data, so the
dashboard can show "Not enough data yet" instead of crashing.
"""
from __future__ import annotations

import math
from datetime import timedelta

import numpy as np
import pandas as pd
from scipy import stats

from src import config


# ------------------------------------------------------------- CPCB AQI
def sub_index(concentration: float | None, pollutant: str) -> float | None:
    """CPCB sub-index by linear interpolation inside the matching breakpoint band.

    I = I_lo + (I_hi - I_lo) / (C_hi - C_lo) * (C - C_lo)
    Example from CPCB: PM2.5 = 45 µg/m³ -> 50 + 50/30 * 15 = 75.
    """
    if concentration is None or pd.isna(concentration) or concentration < 0:
        return None
    bands = config.AQI_BREAKPOINTS[pollutant]
    for c_lo, c_hi, i_lo, i_hi in bands:
        if concentration <= c_hi:
            return i_lo + (i_hi - i_lo) / (c_hi - c_lo) * (concentration - c_lo)
    return float(config.AQI_MAX)  # above the last band: CPCB caps the scale at 500


def compute_aqi(pm25_24h: float | None, pm10_24h: float | None) -> int | None:
    """Overall AQI = the worst (maximum) sub-index, rounded to a whole number."""
    indices = [i for i in (sub_index(pm25_24h, "pm25"), sub_index(pm10_24h, "pm10")) if i is not None]
    if not indices:
        return None
    # Round half up (362.5 -> 363) like CPCB; Python's round() would give 362.
    return int(min(math.floor(max(indices) + 0.5), config.AQI_MAX))


def aqi_category(aqi: float | None) -> str | None:
    """CPCB category name for an AQI value."""
    if aqi is None or pd.isna(aqi):
        return None
    for upper, name, _colour in config.AQI_CATEGORIES:
        if aqi <= upper:
            return name
    return "Severe"


def category_colours() -> dict[str, str]:
    return {name: colour for _upper, name, colour in config.AQI_CATEGORIES}


def add_aqi(df: pd.DataFrame) -> pd.DataFrame:
    """Add rolling 24-h PM means, the AQI and its category to every hourly row.

    CPCB computes PM sub-indices on 24-hour averages and needs >= 16 valid
    hours, so we use a time-based rolling window per station with
    min_periods=16 (pandas counts only non-missing values).
    """
    if df.empty:
        return df.assign(pm25_24h=pd.Series(dtype=float), pm10_24h=pd.Series(dtype=float),
                         aqi=pd.Series(dtype=float), category=pd.Series(dtype=object))
    parts = []
    for _key, group in df.sort_values("ts").groupby(["station_id", "source"], sort=False):
        g = group.set_index("ts")
        rolled = g[["pm25", "pm10"]].rolling(config.ROLLING_WINDOW,
                                             min_periods=config.MIN_HOURS_IN_WINDOW).mean()
        g = g.assign(pm25_24h=rolled["pm25"], pm10_24h=rolled["pm10"]).reset_index()
        parts.append(g)
    out = pd.concat(parts, ignore_index=True)
    out["aqi"] = [compute_aqi(a, b) for a, b in zip(out["pm25_24h"], out["pm10_24h"])]
    out["aqi"] = pd.to_numeric(out["aqi"], errors="coerce").astype(float)
    out["category"] = out["aqi"].map(aqi_category)
    return out


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """AQI columns + a display label that marks model-based rows clearly."""
    out = add_aqi(df)
    out["label"] = np.where(out["source"] == "open-meteo",
                            out["station"].astype(str) + " (model)", out["station"].astype(str))
    return out


# ------------------------------------------------------------ summaries
def with_valid_aqi(df: pd.DataFrame) -> pd.DataFrame:
    return df.dropna(subset=["aqi"]) if "aqi" in df else df.iloc[0:0]


def latest_by_station(df: pd.DataFrame) -> pd.DataFrame:
    """Most recent valid AQI row of each station."""
    valid = with_valid_aqi(df)
    if valid.empty:
        return valid
    return (valid.sort_values("ts").groupby(["station_id", "source"]).tail(1)
            .sort_values("aqi", ascending=False).reset_index(drop=True))


def pct_poor_or_worse(df: pd.DataFrame) -> float | None:
    valid = with_valid_aqi(df)
    if valid.empty:
        return None
    return float(valid["category"].isin(config.POOR_OR_WORSE).mean() * 100)


def daily_station_aqi(df: pd.DataFrame) -> pd.DataFrame:
    """Daily mean AQI per station (for the trend chart)."""
    valid = with_valid_aqi(df)
    if valid.empty:
        return pd.DataFrame(columns=["date", "label", "aqi"])
    valid = valid.assign(date=valid["ts"].dt.date)
    return valid.groupby(["date", "label"], as_index=False)["aqi"].mean()


def daily_city_aqi(df: pd.DataFrame) -> pd.Series:
    """Daily mean AQI across all selected stations, indexed by date."""
    valid = with_valid_aqi(df)
    if valid.empty:
        return pd.Series(dtype=float)
    return valid.groupby(valid["ts"].dt.date)["aqi"].mean()


def hourly_profile(df: pd.DataFrame) -> pd.Series:
    """Average AQI for each hour of the day (0-23, IST)."""
    valid = with_valid_aqi(df)
    if valid.empty:
        return pd.Series(dtype=float)
    return valid.groupby(valid["ts"].dt.hour)["aqi"].mean()


def station_ranking(df: pd.DataFrame) -> pd.DataFrame:
    """Mean AQI per station, most polluted first."""
    valid = with_valid_aqi(df)
    if valid.empty:
        return pd.DataFrame(columns=["label", "aqi"])
    return (valid.groupby("label", as_index=False)["aqi"].mean()
            .sort_values("aqi", ascending=False).reset_index(drop=True))


# -------------------------------------------------------------- insights
def peak_and_cleanest_hour(df: pd.DataFrame, min_days: int = 2) -> dict | None:
    profile = hourly_profile(df)
    if len(profile) < 12 or with_valid_aqi(df)["ts"].dt.date.nunique() < min_days:
        return None
    return {"peak_hour": int(profile.idxmax()), "peak_aqi": float(profile.max()),
            "clean_hour": int(profile.idxmin()), "clean_aqi": float(profile.min())}


def most_least_polluted(df: pd.DataFrame) -> dict | None:
    ranking = station_ranking(df)
    if len(ranking) < 2:
        return None
    top, bottom = ranking.iloc[0], ranking.iloc[-1]
    return {"most": top["label"], "most_aqi": float(top["aqi"]),
            "least": bottom["label"], "least_aqi": float(bottom["aqi"])}


def diwali_comparison(df: pd.DataFrame) -> dict | None:
    """Mean city AQI for the 7 days before Diwali vs Diwali day + the next 6 days.

    Diwali night itself is when firecrackers peak, so it belongs to "after".
    """
    daily = daily_city_aqi(df)
    if daily.empty:
        return None
    d = config.DIWALI_DATE
    n = config.DIWALI_WINDOW_DAYS
    before = daily[(daily.index >= d - timedelta(days=n)) & (daily.index < d)]
    after = daily[(daily.index >= d) & (daily.index < d + timedelta(days=n))]
    if len(before) < config.MIN_DAYS_PER_DIWALI_SIDE or len(after) < config.MIN_DAYS_PER_DIWALI_SIDE:
        return None
    b, a = float(before.mean()), float(after.mean())
    return {"before": b, "after": a, "change_pct": (a - b) / b * 100 if b else np.nan,
            "days_before": len(before), "days_after": len(after)}


def weekday_weekend_test(df: pd.DataFrame) -> dict | None:
    """Welch's t-test on DAILY city-mean AQI, weekdays vs weekends.

    Why daily means: consecutive hours are strongly correlated, so treating
    every hour as an independent sample would overstate significance.
    Welch's version does not assume equal variances in the two groups.
    """
    daily = daily_city_aqi(df)
    if daily.empty:
        return None
    is_weekend = pd.Series([pd.Timestamp(d).day_of_week >= 5 for d in daily.index], index=daily.index)
    weekday, weekend = daily[~is_weekend], daily[is_weekend]
    if len(weekday) < 5 or len(weekend) < 3:
        return None
    t_stat, p_value = stats.ttest_ind(weekday, weekend, equal_var=False)
    diff = float(weekday.mean() - weekend.mean())
    significant = p_value < config.SIGNIFICANCE_LEVEL
    direction = "higher" if diff > 0 else "lower"
    if significant:
        text = (f"Weekdays are {abs(diff):.0f} AQI points {direction} than weekends, and this "
                f"difference is statistically significant (p = {p_value:.3f}). Traffic and "
                f"work activity are a plausible reason, but this test alone does not prove cause.")
    else:
        text = (f"Weekdays are {abs(diff):.0f} AQI points {direction} than weekends, but the "
                f"difference is NOT statistically significant (p = {p_value:.3f}); it could be "
                f"random day-to-day variation (e.g. weather).")
    return {"weekday_mean": float(weekday.mean()), "weekend_mean": float(weekend.mean()),
            "diff": diff, "t_stat": float(t_stat), "p_value": float(p_value),
            "significant": bool(significant), "n_weekday": len(weekday),
            "n_weekend": len(weekend), "text": text}


def pm25_no2_correlation(df: pd.DataFrame, min_pairs: int = 30) -> dict | None:
    """Pearson correlation between hourly PM2.5 and NO2 concentrations."""
    pairs = df[["pm25", "no2"]].dropna() if not df.empty else df
    if len(pairs) < min_pairs or pairs["pm25"].nunique() < 2 or pairs["no2"].nunique() < 2:
        return None
    r, p_value = stats.pearsonr(pairs["pm25"], pairs["no2"])
    strength = ("strong" if abs(r) >= 0.7 else "moderate" if abs(r) >= 0.4
                else "weak" if abs(r) >= 0.2 else "very weak")
    sign = "positive" if r > 0 else "negative"
    text = (f"PM2.5 and NO₂ show a {strength} {sign} correlation (r = {r:.2f}, n = {len(pairs)} hours). "
            + ("They tend to rise together, which fits shared sources such as vehicle traffic "
               "and low night-time mixing." if r >= 0.4 else
               "They do not move together much, so they likely have different main drivers."))
    return {"r": float(r), "p_value": float(p_value), "n": int(len(pairs)), "text": text}


def correlation_matrix(df: pd.DataFrame) -> pd.DataFrame | None:
    cols = ["pm25", "pm10", "no2", "o3"]
    sub = df[cols].dropna(how="all") if not df.empty else df
    if len(sub) < 30:
        return None
    return sub.corr()
