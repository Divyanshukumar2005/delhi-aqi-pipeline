"""Delhi AQI Tracker - Streamlit dashboard.

Run locally:  streamlit run app.py
All numbers in the Insights section are computed live from data/aqi.db.
"""
from __future__ import annotations

import json
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from src import analysis, config, db

st.set_page_config(page_title="Delhi AQI Tracker", page_icon="🌫️", layout="wide")

NOT_ENOUGH = "Not enough data yet."
CATEGORY_ORDER = [name for _u, name, _c in config.AQI_CATEGORIES]
COLOURS = analysis.category_colours()


# ------------------------------------------------------------------ data
@st.cache_data(ttl=3600)  # re-read the DB at most once an hour
def load_data() -> pd.DataFrame:
    return analysis.prepare(db.load_readings())


@st.cache_data(ttl=3600)
def load_coordinates() -> pd.DataFrame:
    """Station coordinates for the map: OpenAQ stations.json + fallback points."""
    rows = [{"station_id": loc["station_id"], "lat": loc["lat"], "lon": loc["lon"]}
            for loc in config.FALLBACK_LOCATIONS]
    if config.STATIONS_PATH.exists():
        try:
            for s in json.loads(config.STATIONS_PATH.read_text(encoding="utf-8")):
                rows.append({"station_id": str(s["id"]), "lat": s["lat"], "lon": s["lon"]})
        except (json.JSONDecodeError, KeyError):
            pass
    return pd.DataFrame(rows)


def show_chart(fig) -> None:
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, width="stretch")


# ---------------------------------------------------------------- header
st.title("🌫️ Delhi AQI Tracker")
st.caption(
    "Hourly air quality for Delhi on India's CPCB National AQI scale. "
    "Measured data: [OpenAQ](https://openaq.org) (government reference monitors). "
    "Fallback model data: CAMS global forecast (Copernicus Atmosphere Monitoring Service) "
    "via [Open-Meteo](https://open-meteo.com)."
)

df_all = load_data()
if df_all.empty:
    st.info(
        "No data yet. Run `python src/collect.py` (or the GitHub Actions workflow) "
        "to fill `data/aqi.db`, then refresh this page. See the README setup guide."
    )
    st.stop()

# --------------------------------------------------------------- sidebar
st.sidebar.header("Filters")
sources = sorted(df_all["source"].unique())
chosen_sources = st.sidebar.multiselect("Data source", sources, default=sources)
labels = sorted(df_all.loc[df_all["source"].isin(chosen_sources), "label"].unique())
chosen_labels = st.sidebar.multiselect("Stations", labels, default=labels)

min_day, max_day = df_all["ts"].min().date(), df_all["ts"].max().date()
picked = st.sidebar.date_input("Date range", value=(min_day, max_day),
                               min_value=min_day, max_value=max_day)
# While the user is mid-selection Streamlit returns a single date; handle both.
if isinstance(picked, (tuple, list)):
    start_day = picked[0] if len(picked) > 0 else min_day
    end_day = picked[1] if len(picked) > 1 else start_day
else:
    start_day = end_day = picked if isinstance(picked, date) else min_day

day = df_all["ts"].dt.date
df = df_all[
    df_all["source"].isin(chosen_sources)
    & df_all["label"].isin(chosen_labels)
    & (day >= start_day) & (day <= end_day)
].copy()

if df.empty:
    st.warning("No rows match the current filters.")
    st.stop()

if (df["source"] == "open-meteo").any():
    share = (df["source"] == "open-meteo").mean() * 100
    st.warning(
        f"⚠️ {share:.0f}% of the selected rows come from the **Open-Meteo / CAMS model fallback** "
        "(marked “(model)”). These are model estimates on a ~45 km grid, not station "
        "measurements, so nearby points can look almost identical."
    )

c1, c2, c3 = st.columns(3)
c1.metric("Last updated (IST)", df_all["ts"].max().strftime("%d %b %Y, %H:%M"))
c2.metric("Days of data", int(df["ts"].dt.date.nunique()))
c3.metric("Stations", int(df["label"].nunique()))

# ----------------------------------------------------------- top metrics
st.subheader("Right now")
latest = analysis.latest_by_station(df)
m1, m2, m3 = st.columns(3)
if latest.empty:
    m1.metric("Latest AQI", "—", help=NOT_ENOUGH + " AQI needs 16+ hours of PM data.")
    m2.metric("Worst station now", "—")
else:
    city_now = latest["aqi"].mean()
    m1.metric("Latest AQI (avg of stations)", f"{city_now:.0f}",
              analysis.aqi_category(city_now), delta_color="off")
    worst = latest.iloc[0]
    m2.metric("Worst station now", worst["label"], f"AQI {worst['aqi']:.0f} · {worst['category']}",
              delta_color="off")
pct = analysis.pct_poor_or_worse(df)
m3.metric("Hours in Poor or worse", "—" if pct is None else f"{pct:.0f}%")

# ---------------------------------------------------------------- charts
st.subheader("Trends")
daily = analysis.daily_station_aqi(df)
if daily.empty:
    st.info(NOT_ENOUGH)
else:
    show_chart(px.line(daily, x="date", y="aqi", color="label", markers=True,
                       title="Daily average AQI per station",
                       labels={"aqi": "AQI", "date": "Date", "label": "Station"}))

left, right = st.columns(2)
with left:
    profile = analysis.hourly_profile(df)
    if profile.empty:
        st.info(NOT_ENOUGH)
    else:
        show_chart(px.bar(x=profile.index, y=profile.values, title="Average AQI by hour of day (IST)",
                          labels={"x": "Hour of day", "y": "AQI"}))
with right:
    valid = analysis.with_valid_aqi(df)
    if valid.empty:
        st.info(NOT_ENOUGH)
    else:
        box = valid.assign(day_type=valid["ts"].dt.day_of_week.map(
            lambda d: "Weekend" if d >= 5 else "Weekday"))
        show_chart(px.box(box, x="day_type", y="aqi", color="day_type",
                          category_orders={"day_type": ["Weekday", "Weekend"]},
                          title="Hourly AQI: weekday vs weekend",
                          labels={"aqi": "AQI", "day_type": ""}))

left, right = st.columns(2)
with left:
    ranking = analysis.station_ranking(df)
    if ranking.empty:
        st.info(NOT_ENOUGH)
    else:
        fig = px.bar(ranking, x="aqi", y="label", orientation="h",
                     title="Station comparison (mean AQI, worst on top)",
                     labels={"aqi": "Mean AQI", "label": ""})
        fig.update_yaxes(autorange="reversed")
        show_chart(fig)
with right:
    valid = analysis.with_valid_aqi(df)
    if valid.empty:
        st.info(NOT_ENOUGH)
    else:
        dist = (valid["category"].value_counts().reindex(CATEGORY_ORDER, fill_value=0)
                .rename_axis("category").reset_index(name="hours"))
        show_chart(px.bar(dist, x="category", y="hours", color="category",
                          color_discrete_map=COLOURS, title="Hours in each CPCB category",
                          labels={"category": "", "hours": "Hours"}))

left, right = st.columns(2)
with left:
    corr = analysis.correlation_matrix(df)
    if corr is None:
        st.info(NOT_ENOUGH)
    else:
        show_chart(px.imshow(corr, text_auto=".2f", zmin=-1, zmax=1,
                             color_continuous_scale="RdBu_r",
                             title="Pollutant correlation (hourly concentrations)"))
with right:
    if latest.empty:
        st.info(NOT_ENOUGH)
    else:
        points = latest.merge(load_coordinates(), on="station_id", how="inner")
        if points.empty:
            st.info("Station coordinates not found yet.")
        else:
            fig = px.scatter_map(
                points, lat="lat", lon="lon", color="category", color_discrete_map=COLOURS,
                size=[14] * len(points), size_max=14, hover_name="label",
                hover_data={"aqi": ":.0f", "lat": False, "lon": False},
                category_orders={"category": CATEGORY_ORDER},
                zoom=9.3, center={"lat": config.DELHI_CENTER[0], "lon": config.DELHI_CENTER[1]},
                map_style="carto-positron", title="Latest AQI by station",
            )
            show_chart(fig)

# -------------------------------------------------------------- insights
st.subheader("Insights (computed live)")


def insight(title: str, body: str | None) -> None:
    st.markdown(f"**{title}**  \n{body if body else NOT_ENOUGH}")


hours = analysis.peak_and_cleanest_hour(df)
insight("Peak and cleanest hour", None if hours is None else (
    f"Air is worst around **{hours['peak_hour']:02d}:00 IST** (avg AQI {hours['peak_aqi']:.0f}) "
    f"and cleanest around **{hours['clean_hour']:02d}:00 IST** (avg AQI {hours['clean_aqi']:.0f})."))

stations_rank = analysis.most_least_polluted(df)
insight("Most and least polluted station", None if stations_rank is None else (
    f"**{stations_rank['most']}** has the highest mean AQI ({stations_rank['most_aqi']:.0f}); "
    f"**{stations_rank['least']}** the lowest ({stations_rank['least_aqi']:.0f})."))

diwali = analysis.diwali_comparison(df_all[df_all["label"].isin(chosen_labels)])
insight(f"Diwali {config.DIWALI_DATE:%d %b %Y}: 7 days before vs after", None if diwali is None else (
    f"Average AQI went from **{diwali['before']:.0f}** before to **{diwali['after']:.0f}** "
    f"from Diwali onwards ({diwali['change_pct']:+.0f}%), based on {diwali['days_before']} and "
    f"{diwali['days_after']} days of data."))

ww = analysis.weekday_weekend_test(df)
insight("Weekday vs weekend (Welch's t-test on daily averages)", None if ww is None else (
    f"Weekday mean {ww['weekday_mean']:.0f} vs weekend mean {ww['weekend_mean']:.0f} "
    f"({ww['n_weekday']} vs {ww['n_weekend']} days). {ww['text']}"))

corr_pn = analysis.pm25_no2_correlation(df)
insight("PM2.5 vs NO₂", None if corr_pn is None else corr_pn["text"])

# ------------------------------------------------------------ footer
st.divider()
st.caption(
    "AQI method: CPCB National Air Quality Index (2014) using 24-hour rolling PM2.5/PM10 means "
    "with at least 16 valid hours; AQI = max(sub-indices), capped at 500. Gas columns are shown "
    "for context only. Data: OpenAQ (openaq.org), licensed per data provider. Model fallback: "
    "Generated using Copernicus Atmosphere Monitoring Service information, provided via the "
    "Open-Meteo API (open-meteo.com, CC BY 4.0)."
)
