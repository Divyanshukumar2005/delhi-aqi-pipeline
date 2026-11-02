"""Print the numbers quoted in the README's "Key findings" section, straight from data/aqi.db.

Usage:  python src/key_findings.py

Every figure uses the same CPCB code as the dashboards (src/analysis.py), so the README can be refreshed
by running this and copying the numbers. Each line says which time window it covers.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import analysis, db

RECENT_DAYS = 14          # the window the React dashboard shows
CITY_STATION_MIN = 15     # a day counts as "well covered" with at least this many stations
LATEST_MAX_AGE_H = 3      # a station counts as "latest" if it reported within this many hours


def compute(df: pd.DataFrame) -> dict:
    """All headline numbers as a dict (None where there is not enough data)."""
    valid = analysis.with_valid_aqi(df)
    if valid.empty:
        return {}
    end = valid["ts"].max()
    recent = df[df["ts"] >= end - pd.Timedelta(days=RECENT_DAYS)]
    daily = analysis.daily_city_aqi(df)
    stations_per_day = valid.groupby(valid["ts"].dt.date)["station_id"].nunique()
    covered = daily[stations_per_day.reindex(daily.index) >= CITY_STATION_MIN]
    ranking = analysis.station_ranking(df)
    latest = analysis.latest_by_station(df, LATEST_MAX_AGE_H)
    latest = latest.assign(area=latest["station"].map(analysis.station_area))
    pm25_hourly = recent.dropna(subset=["pm25"]).groupby(recent["ts"].dt.hour)["pm25"].mean()
    return {
        "first": valid["ts"].min(), "last": end, "station_hours": len(valid),
        "monthly": valid.groupby(valid["ts"].dt.strftime("%Y-%m"))["aqi"].mean().round(0).astype(int).to_dict(),
        "pct_poor_all": analysis.pct_poor_or_worse(df), "pct_poor_recent": analysis.pct_poor_or_worse(recent),
        "worst_day": (covered.idxmax(), covered.max(), int(stations_per_day[covered.idxmax()])) if len(covered) else None,
        "best_day": (covered.idxmin(), covered.min()) if len(covered) else None,
        "days": len(daily), "days_well_covered": int((stations_per_day >= CITY_STATION_MIN).sum()),
        "most_station": ranking.iloc[0].tolist(), "least_station": ranking.iloc[-1].tolist(),
        "latest_basin": float(latest["aqi"].mean()) if len(latest) else None, "latest_n": len(latest),
        "latest_by_area": latest.groupby("area")["aqi"].mean().round(0).astype(int).sort_values(ascending=False).to_dict(),
        "latest_top": latest.iloc[0][["label", "aqi"]].tolist() if len(latest) else None,
        "latest_bottom": latest.iloc[-1][["label", "aqi"]].tolist() if len(latest) else None,
        "pm25_peak": (int(pm25_hourly.idxmax()), pm25_hourly.max()), "pm25_low": (int(pm25_hourly.idxmin()), pm25_hourly.min()),
        "weekday_test": analysis.weekday_weekend_test(df), "pm25_no2": analysis.pm25_no2_correlation(df),
        "diwali": analysis.diwali_comparison(df),
    }


def main() -> None:
    k = compute(analysis.prepare(db.load_readings()))
    if not k:
        sys.exit("No data in data/aqi.db")
    print(f"Data: {k['first']:%d %b %Y} to {k['last']:%d %b %Y %H:%M} IST, {k['station_hours']:,} station-hours with a valid AQI\n")
    print("Monthly mean AQI (station-hour weighted):", ", ".join(f"{m}: {v}" for m, v in k["monthly"].items()))
    print(f"Poor-or-worse share: {k['pct_poor_all']:.1f}% overall, {k['pct_poor_recent']:.1f}% in the last {RECENT_DAYS} days")
    if k["worst_day"]:
        d, a, n = k["worst_day"]
        print(f"Worst well-covered day: {d} (city mean {a:.0f}, {n} stations); cleanest: {k['best_day'][0]} ({k['best_day'][1]:.0f})")
    print(f"Days with >= {CITY_STATION_MIN} stations: {k['days_well_covered']} of {k['days']}")
    print(f"Station averages: {k['least_station'][1]:.0f} ({k['least_station'][0]}) to {k['most_station'][1]:.0f} ({k['most_station'][0]})")
    print(f"\nLatest ({k['latest_n']} stations within {LATEST_MAX_AGE_H} h of {k['last']:%d %b %H:%M}): basin AQI {k['latest_basin']:.0f}")
    print("  by area:", ", ".join(f"{a} {v}" for a, v in k["latest_by_area"].items()))
    print(f"  most polluted: {k['latest_top'][0]} ({k['latest_top'][1]:.0f}); cleanest: {k['latest_bottom'][0]} ({k['latest_bottom'][1]:.0f})")
    print(f"PM2.5 daily rhythm (last {RECENT_DAYS} days): peak {k['pm25_peak'][0]:02d}:00 ({k['pm25_peak'][1]:.0f}), low {k['pm25_low'][0]:02d}:00 ({k['pm25_low'][1]:.0f}) ug/m3")
    w = k["weekday_test"]
    if w:
        print(f"Weekday vs weekend (Welch, daily means): {w['weekday_mean']:.0f} vs {w['weekend_mean']:.0f}, p = {w['p_value']:.3f}, {w['n_weekday']} vs {w['n_weekend']} days")
    c = k["pm25_no2"]
    if c:
        print(f"PM2.5 vs NO2: r = {c['r']:.2f} (n = {c['n']})")
    dw = k["diwali"]
    print("Diwali benchmark:", "not enough data yet" if not dw else f"{dw['before']:.0f} before, {dw['after']:.0f} after ({dw['change_pct']:+.0f}%)")


if __name__ == "__main__":
    main()
