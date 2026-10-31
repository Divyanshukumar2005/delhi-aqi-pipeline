"""Delhi AQI Tracker - dashboard v2.  Run locally:  streamlit run app.py
(The earlier single-page version is kept as app_classic.py.)"""
from __future__ import annotations

import json
from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import analysis, config, db, forecast

st.set_page_config(page_title="Delhi AQI Tracker", page_icon="🌫️", layout="wide")

NOT_ENOUGH = "Not enough data yet."
ORDER = [n for _u, n, _c in config.AQI_CATEGORIES]
COL = analysis.category_colours()
MUTED, FONT = "#9AA0A8", "Bricolage Grotesque, sans-serif"
ADVICE = {  # general guidance in the spirit of CPCB's health statements, not medical advice
    "Good": ("Clean air", "Great time to be outside. Open the windows.",
             "No special precautions."),
    "Satisfactory": ("Fine for most people", "Normal outdoor activity is fine.",
                     "Very sensitive people may notice mild breathing discomfort."),
    "Moderate": ("Go easier outdoors", "Keep long or heavy exercise outdoors short.",
                 "Children, older adults and people with asthma or heart conditions should cut back."),
    "Poor": ("Wear a mask outside", "Avoid long outdoor exertion; an N95 helps on the road.",
             "People with lung or heart disease should stay indoors where possible."),
    "Very Poor": ("Stay indoors if you can", "Skip outdoor exercise. Wear an N95 if you must go out.",
                  "Sensitive groups should avoid going out and run an air purifier."),
    "Severe": ("Health emergency", "Avoid all outdoor activity. Keep windows shut, run a purifier.",
               "Everyone is at risk; seek medical help if symptoms appear."),
}

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@400;600;800&display=swap');
html, body, [class*="css"], .stMarkdown, button { font-family: 'Bricolage Grotesque', sans-serif; }
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; }
.block-container { padding-top: 1.6rem; max-width: 1250px; }
h1 { font-weight: 800; letter-spacing: -0.02em; margin-bottom: 0; }
[data-testid="stMetric"] { background: #1E2126; border: 1px solid #2E333B; border-radius: 10px; padding: 14px 16px; }
.advice { background: #1E2126; border-left: 6px solid var(--c); border-radius: 10px; padding: 22px 26px; }
.advice h2 { margin: 0 0 6px 0; font-weight: 800; font-size: 2rem; }
.advice .cat { color: var(--c); font-weight: 600; font-size: 1.05rem; margin-bottom: 14px; }
.advice p { margin: 0 0 8px 0; line-height: 1.5; max-width: 60ch; }
.stTabs [data-baseweb="tab"] { font-weight: 600; }
</style>""", unsafe_allow_html=True)


# ------------------------------------------------------------------ helpers
def rgba(hex_: str, a: float) -> str:
    h = hex_.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a})"


def show(fig, height: int | None = None) -> None:
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(family=FONT),
                      margin=dict(l=10, r=10, t=50, b=10), height=height,
                      legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, width="stretch")


def msg(text: str = NOT_ENOUGH) -> None:
    st.info(text)


def colour_scale() -> list:
    out, lo = [], 0
    for upper, _n, c in config.AQI_CATEGORIES:
        out += [[lo / 500, c], [upper / 500, c]]
        lo = upper
    return out


@st.cache_data(ttl=3600)
def load_data() -> pd.DataFrame:
    return analysis.prepare(db.load_readings())


@st.cache_data(ttl=3600)
def load_coordinates() -> pd.DataFrame:
    rows = [{"station_id": loc["station_id"], "lat": loc["lat"], "lon": loc["lon"]}
            for loc in config.FALLBACK_LOCATIONS]
    if config.STATIONS_PATH.exists():
        try:
            for s in json.loads(config.STATIONS_PATH.read_text(encoding="utf-8")):
                rows.append({"station_id": str(s["id"]), "lat": s["lat"], "lon": s["lon"]})
        except (json.JSONDecodeError, KeyError):
            pass
    return pd.DataFrame(rows)


def gauge(value: float, colour: str) -> go.Figure:
    steps, lo = [], 0
    for upper, _n, c in config.AQI_CATEGORIES:
        steps.append({"range": [lo, upper], "color": rgba(c, 0.30)})
        lo = upper
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value,
        number={"font": {"size": 70, "color": colour, "family": FONT}},
        gauge={"axis": {"range": [0, 500], "tickcolor": MUTED}, "bar": {"color": colour, "thickness": 0.3},
               "bgcolor": "rgba(0,0,0,0)", "borderwidth": 0, "steps": steps}))
    fig.update_layout(height=290, margin=dict(l=20, r=20, t=30, b=0),
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(family=FONT))
    return fig


# ------------------------------------------------------------------- header
st.title("🌫️ Delhi AQI Tracker")
st.caption("Hourly air quality on India's CPCB scale. Measured data: OpenAQ government monitors. "
           "Fallback model data: CAMS via Open-Meteo.")

df_all = load_data()
if df_all.empty:
    st.info("No data yet. Run `python src/collect.py` (or the GitHub Actions workflow), then refresh.")
    st.stop()

# ------------------------------------------------------------------ sidebar
st.sidebar.header("Filters")
sources = sorted(df_all["source"].unique())
chosen_sources = st.sidebar.multiselect("Data source", sources, default=sources)
labels = sorted(df_all.loc[df_all["source"].isin(chosen_sources), "label"].unique())
chosen_labels = st.sidebar.multiselect("Stations", labels, default=labels)
min_day, max_day = df_all["ts"].min().date(), df_all["ts"].max().date()
picked = st.sidebar.date_input("Date range", value=(min_day, max_day),
                               min_value=min_day, max_value=max_day)
if isinstance(picked, (tuple, list)):
    start_day = picked[0] if len(picked) > 0 else min_day
    end_day = picked[1] if len(picked) > 1 else start_day
else:
    start_day = end_day = picked if isinstance(picked, date) else min_day

day = df_all["ts"].dt.date
df = df_all[df_all["source"].isin(chosen_sources) & df_all["label"].isin(chosen_labels)
            & (day >= start_day) & (day <= end_day)].copy()
if df.empty:
    st.warning("No rows match these filters. Pick at least one station and a wider date range.")
    st.stop()
if (df["source"] == "open-meteo").any():
    st.warning(f"{(df['source'] == 'open-meteo').mean() * 100:.0f}% of the selected rows are "
               "**model estimates** (Open-Meteo / CAMS, marked “(model)”), not station measurements.")

valid = analysis.with_valid_aqi(df)
latest = analysis.latest_by_station(df)

tab_over, tab_pat, tab_st, tab_fc, tab_ins = st.tabs(
    ["Overview", "Patterns", "Stations", "Forecast", "Insights & data"])

# ----------------------------------------------------------------- overview
with tab_over:
    if latest.empty:
        msg("No AQI yet. It needs 16+ hours of PM data per station.")
    else:
        now = float(latest["aqi"].mean())
        cat = analysis.aqi_category(now)
        colour = COL[cat]
        head, sub, sens = ADVICE[cat]
        g, a = st.columns([1, 1.25], gap="large")
        with g:
            st.plotly_chart(gauge(now, colour), width="stretch")
            st.caption(f"Average of {len(latest)} station(s), latest valid hour.")
        with a:
            st.markdown(f"""<div class="advice" style="--c:{colour}">
              <div class="cat">{cat} · AQI {now:.0f}</div><h2>{head}</h2>
              <p>{sub}</p><p style="color:{MUTED}">{sens}</p></div>""", unsafe_allow_html=True)
            st.caption("General guidance, not medical advice.")
        worst = latest.iloc[0]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Worst station now", worst["label"], f"AQI {worst['aqi']:.0f}", delta_color="off")
        m2.metric("Cleanest station now", latest.iloc[-1]["label"],
                  f"AQI {latest.iloc[-1]['aqi']:.0f}", delta_color="off")
        pct = analysis.pct_poor_or_worse(df)
        m3.metric("Hours Poor or worse", "—" if pct is None else f"{pct:.0f}%")
        m4.metric("Last updated (IST)", df_all["ts"].max().strftime("%d %b, %H:%M"))

        left, right = st.columns(2)
        with left:
            pts = latest.merge(load_coordinates(), on="station_id", how="inner")
            if pts.empty:
                msg("Station coordinates not found yet.")
            else:
                fig = px.scatter_map(pts, lat="lat", lon="lon", color="category",
                                     color_discrete_map=COL, category_orders={"category": ORDER},
                                     size=[16] * len(pts), size_max=16, hover_name="label",
                                     hover_data={"aqi": ":.0f", "lat": False, "lon": False},
                                     zoom=9.3, center={"lat": config.DELHI_CENTER[0],
                                                       "lon": config.DELHI_CENTER[1]},
                                     map_style="carto-darkmatter", title="Latest AQI by station")
                show(fig, 380)
        with right:
            fig = px.bar(latest, x="aqi", y="label", orientation="h", color="category",
                         color_discrete_map=COL, category_orders={"category": ORDER},
                         title="Stations right now", labels={"aqi": "AQI", "label": ""})
            fig.update_yaxes(autorange="reversed")
            show(fig, 380)

# ----------------------------------------------------------------- patterns
with tab_pat:
    if valid.empty:
        msg()
    else:
        pv = (valid.assign(date=valid["ts"].dt.date, hour=valid["ts"].dt.hour)
              .pivot_table(index="date", columns="hour", values="aqi", aggfunc="mean"))
        fig = px.imshow(pv, aspect="auto", zmin=0, zmax=500, color_continuous_scale=colour_scale(),
                        title="When is the air worst? City AQI by day and hour (IST)",
                        labels={"x": "Hour of day", "y": "", "color": "AQI"})
        show(fig, 460)
        daily = analysis.daily_station_aqi(df)
        city = analysis.daily_city_aqi(df)
        fig = px.line(daily, x="date", y="aqi", color="label", title="Daily average AQI",
                      labels={"aqi": "AQI", "date": "", "label": "Station"})
        fig.update_traces(opacity=0.45, line_width=1.5)
        fig.add_trace(go.Scatter(x=city.index, y=city.values, name="City average",
                                 line=dict(color="#FFFFFF", width=3)))
        show(fig, 380)
        l, r = st.columns(2)
        with l:
            prof = analysis.hourly_profile(df)
            show(px.bar(x=prof.index, y=prof.values, title="Average AQI by hour (IST)",
                        labels={"x": "Hour", "y": "AQI"}), 340)
        with r:
            dist = (valid["category"].value_counts().reindex(ORDER, fill_value=0)
                    .rename_axis("category").reset_index(name="hours"))
            show(px.bar(dist, x="category", y="hours", color="category", color_discrete_map=COL,
                        title="Hours in each CPCB category", labels={"category": "", "hours": "Hours"}), 340)

# ----------------------------------------------------------------- stations
with tab_st:
    if valid.empty:
        msg()
    else:
        pick = st.selectbox("Station", sorted(valid["label"].unique()))
        sv = valid[valid["label"] == pick].sort_values("ts")
        raw = df[df["label"] == pick].sort_values("ts")
        pct_s = sv["category"].isin(config.POOR_OR_WORSE).mean() * 100
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Latest AQI", f"{sv['aqi'].iloc[-1]:.0f}", sv["category"].iloc[-1], delta_color="off")
        c2.metric("Mean AQI", f"{sv['aqi'].mean():.0f}")
        c3.metric("Worst hour on record", f"{sv['aqi'].max():.0f}", sv.loc[sv['aqi'].idxmax(), 'ts'].strftime("%d %b, %H:%M"), delta_color="off")
        c4.metric("Hours Poor or worse", f"{pct_s:.0f}%")
        fig = go.Figure(go.Scatter(x=sv["ts"], y=sv["aqi"], line=dict(color="#E9E6E0", width=2)))
        top, lo = max(100, sv["aqi"].max() * 1.1), 0
        for upper, name, c in config.AQI_CATEGORIES:
            if lo < top:
                fig.add_hrect(y0=lo, y1=min(upper, top), fillcolor=c, opacity=0.12, line_width=0,
                              annotation_text=name, annotation_position="top left",
                              annotation_font_color=MUTED)
            lo = upper
        fig.update_layout(title=f"{pick}: AQI over time", yaxis=dict(range=[0, top], title="AQI"))
        show(fig, 420)
        fig = go.Figure()
        for col_name, name, c in [("pm25", "PM2.5", "#E07A5F"), ("pm10", "PM10", "#8FB8C9")]:
            fig.add_trace(go.Scatter(x=raw["ts"], y=raw[col_name], name=name, line=dict(color=c, width=1.5)))
        fig.update_layout(title="Raw PM concentrations (µg/m³)")
        show(fig, 320)

# ----------------------------------------------------------------- forecast
with tab_fc:
    s = forecast.city_hourly(df)
    fc = forecast.forecast_24h(s)
    if fc is None:
        msg("Need at least 72 hours of city AQI data to forecast.")
    else:
        hist = s.iloc[-72:]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=list(fc["ts"]) + list(fc["ts"])[::-1],
                                 y=list(fc["hi"]) + list(fc["lo"])[::-1], fill="toself",
                                 fillcolor="rgba(143,184,201,0.18)", line=dict(width=0),
                                 name="Likely range (~80%)", hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=hist.index, y=hist.values, name="Observed",
                                 line=dict(color="#E9E6E0", width=2.5)))
        fig.add_trace(go.Scatter(x=fc["ts"], y=fc["aqi"], name="Forecast",
                                 line=dict(color="#8FB8C9", width=2.5, dash="dash")))
        fig.update_layout(title="City AQI: last 72 hours and next 24 hours (IST)", yaxis_title="AQI")
        show(fig, 430)
        pk = fc.loc[fc["aqi"].idxmax()]
        avg = fc["aqi"].mean()
        c1, c2, c3 = st.columns(3)
        c1.metric("Expected average, next 24 h", f"{avg:.0f}", analysis.aqi_category(avg), delta_color="off")
        c2.metric("Expected peak", f"{pk['aqi']:.0f}", pk["ts"].strftime("%a %H:%M"), delta_color="off")
        c3.metric("Change vs now", f"{avg - s.iloc[-1]:+.0f}")
        st.caption("This is a simple statistical baseline: current level fading towards the recent "
                   "average plus the typical hour-of-day pattern. It does not know about weather, "
                   "wind or fires, so treat it as a rough guide.")

# ----------------------------------------------------------------- insights
with tab_ins:
    def insight(title: str, body: str | None) -> None:
        st.markdown(f"**{title}**  \n{body if body else NOT_ENOUGH}")

    hrs = analysis.peak_and_cleanest_hour(df)
    insight("Peak and cleanest hour", None if hrs is None else
            f"Worst around **{hrs['peak_hour']:02d}:00 IST** (AQI {hrs['peak_aqi']:.0f}), "
            f"cleanest around **{hrs['clean_hour']:02d}:00 IST** (AQI {hrs['clean_aqi']:.0f}).")
    rk = analysis.most_least_polluted(df)
    insight("Most and least polluted station", None if rk is None else
            f"**{rk['most']}** is highest (mean AQI {rk['most_aqi']:.0f}); "
            f"**{rk['least']}** is lowest ({rk['least_aqi']:.0f}).")
    dw = analysis.diwali_comparison(df_all[df_all["label"].isin(chosen_labels)])
    insight(f"Diwali {config.DIWALI_DATE:%d %b %Y}: 7 days before vs after", None if dw is None else
            f"AQI went from **{dw['before']:.0f}** to **{dw['after']:.0f}** ({dw['change_pct']:+.0f}%), "
            f"using {dw['days_before']} and {dw['days_after']} days of data.")
    ww = analysis.weekday_weekend_test(df)
    insight("Weekday vs weekend (Welch's t-test)", None if ww is None else
            f"Weekday mean {ww['weekday_mean']:.0f} vs weekend {ww['weekend_mean']:.0f} "
            f"({ww['n_weekday']} vs {ww['n_weekend']} days). {ww['text']}")
    cp = analysis.pm25_no2_correlation(df)
    insight("PM2.5 vs NO₂", None if cp is None else cp["text"])
    corr = analysis.correlation_matrix(df)
    if corr is not None:
        show(px.imshow(corr, text_auto=".2f", zmin=-1, zmax=1, color_continuous_scale="RdBu_r",
                       title="Pollutant correlation (hourly)"), 380)
    st.divider()
    cols = ["label", "ts", "pm25", "pm10", "no2", "o3", "pm25_24h", "pm10_24h", "aqi", "category", "source"]
    out = df[cols].sort_values("ts", ascending=False)
    st.download_button("Download filtered data (CSV)", out.to_csv(index=False).encode("utf-8"),
                       "delhi_aqi.csv", "text/csv")
    st.dataframe(out.head(500), width="stretch", hide_index=True)

st.caption("AQI: CPCB National AQI (2014), 24-h rolling PM2.5/PM10 means with ≥16 valid hours, "
           "AQI = max of sub-indices. Data: OpenAQ (licensed per provider). Model fallback: Copernicus "
           "Atmosphere Monitoring Service via Open-Meteo (CC BY 4.0).")
