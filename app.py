"""Delhi-NCR Air Quality Index (AQI) Tracker — Production Dashboard (Light Theme Edition).

CPCB National AQI (2014) scale with 24-h rolling PM2.5/PM10 means.
Ultra-clean, modern light aesthetic with high contrast & vibrant CPCB category accents.
Reads data/aqi.db in read-only mode.
Run locally: streamlit run app.py
"""
from __future__ import annotations

import json
from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import analysis, config, db, forecast

# -----------------------------------------------------------------------------
# Streamlit Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Delhi-NCR AQI Tracker — Live Air Quality",
    page_icon="🌫️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# Light Theme Typography, Palette, and Custom CSS
# -----------------------------------------------------------------------------
FONT_FAMILY = "Bricolage Grotesque, -apple-system, BlinkMacSystemFont, sans-serif"
MONO_FONT = "JetBrains Mono, ui-monospace, SFMono-Regular, monospace"
BG_MAIN = "#F8FAFC"
BG_CARD = "#FFFFFF"
BG_ELEVATED = "#F1F5F9"
BORDER_COLOR = "#E2E8F0"
TEXT_PRIMARY = "#0F172A"
TEXT_SECONDARY = "#475569"
TEXT_MUTED = "#64748B"

ORDER = [name for _u, name, _c in config.AQI_CATEGORIES]
CATEGORY_COLORS = analysis.category_colours()

ADVICE_MAP = {
    "Good": {
        "tag": "Good Air Quality (0–50)",
        "head": "Air is clean and fresh",
        "action": "Ideal time for outdoor activities, morning walks, and opening windows for ventilation.",
        "sensitive": "No health precautions needed. Zero health risk for all population groups.",
    },
    "Satisfactory": {
        "tag": "Satisfactory Air Quality (51–100)",
        "head": "Air quality is acceptable",
        "action": "Normal outdoor exertion and daily routines can continue without restriction.",
        "sensitive": "Unusually sensitive individuals may notice minor breathing discomfort with prolonged exertion.",
    },
    "Moderate": {
        "tag": "Moderate Air Quality (101–200)",
        "head": "Keep long outdoor workouts shorter",
        "action": "Shorten intense outdoor sports or heavy physical workouts along busy transit corridors.",
        "sensitive": "Children, the elderly, and individuals with asthma or heart conditions should take regular breaks.",
    },
    "Poor": {
        "tag": "Poor Air Quality (201–300)",
        "head": "Mask recommended for outdoor commutes",
        "action": "Avoid prolonged outdoor exertion. Wear a well-fitting N95 mask when on roads or in traffic.",
        "sensitive": "People with lung or heart disease, pregnant women, and children should limit outdoor exposure.",
    },
    "Very Poor": {
        "tag": "Very Poor Air Quality (301–400)",
        "head": "High pollution alert · Restrict outdoor activity",
        "action": "Keep windows closed. Avoid outdoor jogging or cycling. Run indoor HEPA air purifiers.",
        "sensitive": "Sensitive individuals must stay indoors. Everyone may experience throat irritation or cough.",
    },
    "Severe": {
        "tag": "Severe Air Emergency (401–500)",
        "head": "Public health emergency · Stay indoors",
        "action": "Avoid all non-essential outdoor activity. Keep air purifiers running in sealed rooms. Seek medical attention if respiratory distress occurs.",
        "sensitive": "May cause severe health effects even in healthy people; high hazard for compromised groups.",
    },
}

st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400..800&family=JetBrains+Mono:wght@400..700&display=swap');

html, body, [class*="css"], .stApp {{
    font-family: {FONT_FAMILY};
    background-color: {BG_MAIN} !important;
    color: {TEXT_PRIMARY} !important;
}}

#MainMenu, footer, header[data-testid="stHeader"] {{
    visibility: hidden;
    height: 0;
}}

.block-container {{
    padding-top: 1.2rem;
    padding-bottom: 3.5rem;
    max-width: 1340px;
}}

/* Sidebar styling for light theme */
[data-testid="stSidebar"] {{
    background-color: #FFFFFF !important;
    border-right: 1px solid {BORDER_COLOR};
}}

/* Metrics styling */
[data-testid="stMetric"] {{
    background: {BG_CARD};
    border: 1px solid {BORDER_COLOR};
    border-radius: 14px;
    padding: 16px 20px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05), 0 4px 12px rgba(0, 0, 0, 0.02);
}}

[data-testid="stMetricValue"] {{
    font-family: {MONO_FONT};
    font-size: 1.9rem !important;
    font-weight: 800;
    color: {TEXT_PRIMARY} !important;
}}

[data-testid="stMetricLabel"] {{
    font-size: 0.8rem !important;
    color: {TEXT_MUTED} !important;
    text-transform: uppercase;
    font-weight: 700;
    letter-spacing: 0.05em;
}}

/* Custom Advice Box for Light Theme */
.hero-advice-card {{
    background: {BG_CARD};
    border: 1px solid {BORDER_COLOR};
    border-left: 6px solid var(--category-c);
    border-radius: 16px;
    padding: 24px 28px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}}

.hero-advice-tag {{
    display: inline-block;
    padding: 4px 12px;
    border-radius: 9999px;
    font-size: 0.8rem;
    font-weight: 800;
    letter-spacing: 0.03em;
    color: var(--category-c);
    background: var(--category-bg);
    margin-bottom: 12px;
    border: 1px solid var(--category-border);
}}

.hero-advice-head {{
    font-size: 1.75rem;
    font-weight: 800;
    line-height: 1.25;
    margin: 0 0 10px 0;
    color: {TEXT_PRIMARY};
}}

.hero-advice-action {{
    font-size: 1rem;
    line-height: 1.55;
    color: {TEXT_SECONDARY};
    margin-bottom: 14px;
}}

.hero-advice-sensitive {{
    font-size: 0.88rem;
    line-height: 1.45;
    color: {TEXT_MUTED};
    padding-top: 12px;
    border-top: 1px solid #EDF2F7;
}}

/* Regional Basin Badges */
.basin-strip {{
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin: 16px 0 24px 0;
}}

.basin-badge {{
    background: {BG_CARD};
    border: 1px solid {BORDER_COLOR};
    border-radius: 12px;
    padding: 12px 18px;
    display: flex;
    align-items: center;
    gap: 12px;
    flex: 1 1 calc(20% - 12px);
    min-width: 160px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}}

.basin-badge-name {{
    font-size: 0.88rem;
    font-weight: 700;
    color: {TEXT_PRIMARY};
}}

.basin-badge-val {{
    font-family: {MONO_FONT};
    font-size: 1.35rem;
    font-weight: 800;
    margin-left: auto;
}}

/* Light Tab styling */
.stTabs [data-baseweb="tab-list"] {{
    gap: 6px;
    border-bottom: 2px solid #E2E8F0;
    padding-bottom: 2px;
}}

.stTabs [data-baseweb="tab"] {{
    font-weight: 700;
    font-size: 0.95rem;
    padding: 10px 20px;
    border-radius: 8px 8px 0 0;
    color: {TEXT_SECONDARY};
}}

.stTabs [aria-selected="true"] {{
    color: #0F172A !important;
    border-bottom: 2px solid #FF9900 !important;
}}

.notice-banner {{
    background: #FFFBEB;
    border: 1px solid #FDE68A;
    border-radius: 10px;
    padding: 12px 18px;
    color: #92400E;
    font-size: 0.9rem;
    margin-bottom: 18px;
    font-weight: 500;
}}

.insight-card {{
    background: {BG_CARD};
    border: 1px solid {BORDER_COLOR};
    border-radius: 14px;
    padding: 18px 22px;
    margin-bottom: 14px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03);
}}
</style>
""",
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Cached Data Loading & Spatial Coordinates
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def load_data() -> pd.DataFrame:
    """Load readings from SQLite database and compute CPCB rolling AQI."""
    raw = db.load_readings()
    if raw.empty:
        sample_csv = config.DATA_DIR / "sample_readings.csv"
        if sample_csv.exists():
            try:
                sdf = pd.read_csv(sample_csv)
                sdf["ts"] = pd.to_datetime(sdf["ts"], utc=True).dt.tz_convert(config.IST)
                for c in ["pm25", "pm10", "no2", "o3"]:
                    sdf[c] = pd.to_numeric(sdf[c], errors="coerce")
                raw = sdf
            except Exception:
                pass
    return analysis.prepare(raw)


@st.cache_data(ttl=3600)
def load_coordinates() -> pd.DataFrame:
    """Load monitoring station geographic coordinates for the map."""
    rows = [
        {"station_id": loc["station_id"], "lat": loc["lat"], "lon": loc["lon"], "name": loc["station"]}
        for loc in config.FALLBACK_LOCATIONS
    ]
    if config.STATIONS_PATH.exists():
        try:
            stations_data = json.loads(config.STATIONS_PATH.read_text(encoding="utf-8"))
            for s in stations_data:
                rows.append({
                    "station_id": str(s.get("id")),
                    "lat": s.get("lat"),
                    "lon": s.get("lon"),
                    "name": s.get("name"),
                    "distance_km": s.get("distance_km"),
                })
        except Exception:
            pass
    coord_df = pd.DataFrame(rows).drop_duplicates(subset=["station_id"], keep="last")
    return coord_df


# -----------------------------------------------------------------------------
# Light Theme Visualization Helpers
# -----------------------------------------------------------------------------
def rgba(hex_code: str, alpha: float) -> str:
    h = hex_code.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alpha})"


def style_figure(fig: go.Figure, height: int | None = None) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_FAMILY, color=TEXT_PRIMARY),
        margin=dict(l=16, r=16, t=44, b=16),
        height=height,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(255, 255, 255, 0.8)",
            font=dict(size=11, color=TEXT_SECONDARY),
        ),
        xaxis=dict(
            gridcolor="#E2E8F0",
            linecolor="#CBD5E1",
            tickfont=dict(family=FONT_FAMILY, color=TEXT_SECONDARY),
        ),
        yaxis=dict(
            gridcolor="#E2E8F0",
            linecolor="#CBD5E1",
            tickfont=dict(family=FONT_FAMILY, color=TEXT_SECONDARY),
        ),
    )
    return fig


def show_chart(fig: go.Figure, height: int | None = None) -> None:
    styled = style_figure(fig, height)
    st.plotly_chart(styled, width="stretch")


def cpcb_color_scale() -> list:
    scale, lo = [], 0
    for upper, _name, col in config.AQI_CATEGORIES:
        scale.append([lo / 500, col])
        scale.append([upper / 500, col])
        lo = upper
    return scale


def build_cpcb_gauge(value: float, category: str, color: str) -> go.Figure:
    """Build a distinctive, high-clarity CPCB semicircular gauge for Light Theme."""
    steps, lo = [], 0
    for upper, _name, col in config.AQI_CATEGORIES:
        steps.append({"range": [lo, upper], "color": rgba(col, 0.35)})
        lo = upper

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            domain={"x": [0, 1], "y": [0, 1]},
            number={
                "font": {"size": 68, "color": color, "family": MONO_FONT},
                "valueformat": ".0f",
            },
            gauge={
                "axis": {
                    "range": [0, 500],
                    "tickwidth": 1.5,
                    "tickcolor": "#94A3B8",
                    "tickvals": [0, 50, 100, 200, 300, 400, 500],
                    "ticktext": ["0", "50", "100", "200", "300", "400", "500"],
                    "tickfont": {"size": 12, "color": "#64748B", "family": MONO_FONT},
                },
                "bar": {"color": color, "thickness": 0.35},
                "bgcolor": "#F1F5F9",
                "borderwidth": 0,
                "steps": steps,
                "threshold": {
                    "line": {"color": color, "width": 4},
                    "thickness": 0.8,
                    "value": value,
                },
            },
        )
    )
    fig.update_layout(
        height=270,
        margin=dict(l=25, r=25, t=25, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_FAMILY),
    )
    return fig


# -----------------------------------------------------------------------------
# Data Ingestion & Safeguards
# -----------------------------------------------------------------------------
df_all = load_data()

if df_all.empty:
    st.error("### ⚠️ Database contains no readings yet")
    st.info(
        "Please execute the collection script to populate data/aqi.db: "
        "`python src/collect.py` or commit sample readings, then reload."
    )
    st.stop()

df_all["area"] = df_all["label"].apply(analysis.station_area)

# -----------------------------------------------------------------------------
# Sidebar Filters & Controls (Light Theme)
# -----------------------------------------------------------------------------
st.sidebar.markdown("## 🔍 Dashboard Filters")

# 1. Source Filter
available_sources = sorted(df_all["source"].unique())
selected_sources = st.sidebar.multiselect(
    "Data Source",
    options=available_sources,
    default=available_sources,
    help="openaq: Real ground monitoring stations. open-meteo: CAMS atmospheric model fallback.",
)
if not selected_sources:
    st.sidebar.warning("Select at least one data source.")
    st.stop()

# 2. Area Filter
available_areas = sorted(df_all.loc[df_all["source"].isin(selected_sources), "area"].unique())
selected_areas = st.sidebar.multiselect(
    "NCR Sub-Region",
    options=available_areas,
    default=available_areas,
    help="Filter monitoring stations by NCR sub-region.",
)

# 3. Station Selection
filtered_by_area = df_all[
    df_all["source"].isin(selected_sources)
    & (df_all["area"].isin(selected_areas) if selected_areas else True)
]
available_labels = sorted(filtered_by_area["label"].unique())
selected_labels = st.sidebar.multiselect(
    "Monitoring Stations",
    options=available_labels,
    default=available_labels,
)
if not selected_labels:
    st.sidebar.warning("Please select at least one station.")
    st.stop()

# 4. Date Range
min_date = df_all["ts"].min().date()
max_date = df_all["ts"].max().date()
date_selection = st.sidebar.date_input(
    "Date Range (IST)",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

if isinstance(date_selection, (tuple, list)):
    start_d = date_selection[0] if len(date_selection) > 0 else min_date
    end_d = date_selection[1] if len(date_selection) > 1 else start_d
else:
    start_d = end_d = date_selection if isinstance(date_selection, date) else min_date

ts_date = df_all["ts"].dt.date
df = df_all[
    df_all["source"].isin(selected_sources)
    & df_all["label"].isin(selected_labels)
    & (ts_date >= start_d)
    & (ts_date <= end_d)
].copy()

if df.empty:
    st.warning("No records match the active filter criteria. Please broaden your selection.")
    st.stop()

has_model_data = (df["source"] == "open-meteo").any()
if has_model_data:
    pct_model = (df["source"] == "open-meteo").mean() * 100
    st.markdown(
        f"""<div class="notice-banner">
        ⚠️ <strong>Model Estimate Warning:</strong> {pct_model:.1f}% of active records originate from
        <strong>Open-Meteo (Copernicus CAMS model)</strong> labeled as <em>(model)</em>, not calibrated ground monitoring stations.
        </div>""",
        unsafe_allow_html=True,
    )

valid_aqi_df = analysis.with_valid_aqi(df)
latest_stations = analysis.latest_by_station(df)
coords_df = load_coordinates()

# -----------------------------------------------------------------------------
# Header Bar (Light Theme)
# -----------------------------------------------------------------------------
last_recorded_ist = df_all["ts"].max().strftime("%d %b %Y, %H:%M IST")

col_head, col_badge = st.columns([2.5, 1.2])
with col_head:
    st.title("🌫️ Delhi-NCR Air Quality Tracker")
    st.markdown(
        f"<div style='color: {TEXT_MUTED}; font-size: 0.95rem; font-weight: 500;'>"
        "Continuous 24-Hour Rolling AQI on India's CPCB NAQI Standard · Hourly government monitoring stations"
        "</div>",
        unsafe_allow_html=True,
    )
with col_badge:
    st.markdown(
        f"""
        <div style="text-align: right; background: #FFFFFF; border: 1px solid {BORDER_COLOR}; border-radius: 12px; padding: 10px 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
          <div style="font-size: 0.75rem; text-transform: uppercase; color: {TEXT_MUTED}; font-weight: 700; letter-spacing: 0.05em;">Last Updated</div>
          <div style="font-family: {MONO_FONT}; font-size: 1.15rem; font-weight: 800; color: {TEXT_PRIMARY};">{last_recorded_ist}</div>
          <div style="font-size: 0.74rem; color: #10B981; font-weight: 600;">● Data is hourly (not live stream)</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Navigation Tabs
# -----------------------------------------------------------------------------
tab_hero, tab_map_rank, tab_patterns, tab_trends, tab_station, tab_compare, tab_forecast, tab_insights = st.tabs(
    [
        "Basin Overview",
        "Map & Rankings",
        "Heatmap & Diurnal",
        "Trend & Pollutants",
        "Station Deep-Dive",
        "Compare Stations",
        "24-Hour Forecast",
        "Insights & Data Export",
    ]
)

# =============================================================================
# TAB 1: BASIN OVERVIEW (Hero, Gauge, Advice, Basin Quick-Pulse)
# =============================================================================
with tab_hero:
    if latest_stations.empty:
        st.info("Insufficient valid 24-hour PM data to compute current station AQIs (minimum 16 hours required).")
    else:
        city_now = float(latest_stations["aqi"].mean())
        curr_cat = analysis.aqi_category(city_now) or "Moderate"
        curr_col = CATEGORY_COLORS[curr_cat]
        advice = ADVICE_MAP[curr_cat]

        col_gauge, col_advice = st.columns([1.1, 1.4], gap="medium")

        with col_gauge:
            st.markdown(
                f"""
                <div style="background: #FFFFFF; border: 1px solid {BORDER_COLOR}; border-radius: 16px; padding: 18px 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.04); text-align: center;">
                """,
                unsafe_allow_html=True,
            )
            st.plotly_chart(build_cpcb_gauge(city_now, curr_cat, curr_col), width="stretch")
            st.markdown(
                f"""
                <div style="text-align: center; margin-top: -12px;">
                    <span style="font-size: 0.88rem; color: {TEXT_MUTED}; font-weight: 500;">
                        Average of <strong>{len(latest_stations)}</strong> active monitoring stations in Delhi-NCR
                    </span>
                </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_advice:
            st.markdown(
                f"""
                <div class="hero-advice-card" style="--category-c: {curr_col}; --category-bg: {curr_col}15; --category-border: {curr_col}40;">
                    <div>
                        <div class="hero-advice-tag">{advice['tag']}</div>
                        <h2 class="hero-advice-head">{advice['head']}</h2>
                        <div class="hero-advice-action">{advice['action']}</div>
                    </div>
                    <div>
                        <div class="hero-advice-sensitive"><strong>Sensitive Groups:</strong> {advice['sensitive']}</div>
                        <div style="font-size: 0.72rem; color: {TEXT_MUTED}; margin-top: 8px;">
                            * Guidance formulated in the spirit of CPCB NAQI health statements. Not medical advice.
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        # Regional Basin Quick-Pulse Badges (Light Mode)
        st.markdown(f"<div style='font-weight: 700; color: {TEXT_PRIMARY}; font-size: 1rem; margin-bottom: 8px;'>📍 NCR Sub-Region Average Right Now</div>", unsafe_allow_html=True)
        area_groups = latest_stations.groupby("area")["aqi"].agg(["mean", "count"]).reset_index()
        area_cards_html = "<div class='basin-strip'>"
        for _, r in area_groups.iterrows():
            a_mean = r["mean"]
            a_cat = analysis.aqi_category(a_mean) or "Moderate"
            a_col = CATEGORY_COLORS[a_cat]
            area_cards_html += f"""
            <div class='basin-badge' style='border-left: 5px solid {a_col};'>
                <div>
                    <div class='basin-badge-name'>{r['area']}</div>
                    <div style='font-size: 0.75rem; color: {TEXT_MUTED}; font-weight: 500;'>{r['count']} station(s) · {a_cat}</div>
                </div>
                <div class='basin-badge-val' style='color: {a_col};'>{a_mean:.0f}</div>
            </div>
            """
        area_cards_html += "</div>"
        st.markdown(area_cards_html, unsafe_allow_html=True)

        worst_st = latest_stations.iloc[0]
        clean_st = latest_stations.iloc[-1]
        pct_poor = analysis.pct_poor_or_worse(df)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Most Polluted Station", worst_st["label"], f"AQI {worst_st['aqi']:.0f}")
        m2.metric("Cleanest Station", clean_st["label"], f"AQI {clean_st['aqi']:.0f}")
        m3.metric("Hours Poor or Worse", f"{pct_poor:.1f}%" if pct_poor is not None else "—")
        m4.metric("Active Monitors", f"{len(latest_stations)} / {df_all['station_id'].nunique()}")

# =============================================================================
# TAB 2: MAP & RANKINGS (Light Basemap)
# =============================================================================
with tab_map_rank:
    col_map, col_rank = st.columns([1.15, 1], gap="large")

    with col_map:
        st.markdown(f"<h3 style='color: {TEXT_PRIMARY}; font-size: 1.15rem; font-weight: 700;'>🗺️ Delhi-NCR Station Map</h3>", unsafe_allow_html=True)
        map_data = latest_stations.merge(coords_df, on="station_id", how="inner")

        if map_data.empty:
            st.info("Station coordinates not found in data/stations.json.")
        else:
            # Carto Positron provides the cleanest, crispest light basemap for navigation
            fig_map = px.scatter_map(
                map_data,
                lat="lat",
                lon="lon",
                color="category",
                color_discrete_map=CATEGORY_COLORS,
                category_orders={"category": ORDER},
                hover_name="label",
                hover_data={
                    "aqi": ":.0f",
                    "area": True,
                    "pm25_24h": ":.1f",
                    "pm10_24h": ":.1f",
                    "lat": False,
                    "lon": False,
                },
                size=[18] * len(map_data),
                size_max=18,
                zoom=9.2,
                center={"lat": config.DELHI_CENTER[0], "lon": config.DELHI_CENTER[1]},
                map_style="carto-positron",
            )
            fig_map.update_layout(
                margin=dict(l=0, r=0, t=10, b=0),
                paper_bgcolor="rgba(0,0,0,0)",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=0.01,
                    xanchor="center",
                    x=0.5,
                    bgcolor="rgba(255, 255, 255, 0.95)",
                    font=dict(size=11, family=FONT_FAMILY, color=TEXT_PRIMARY),
                ),
            )
            fig_map.update_layout(height=520)
            st.plotly_chart(fig_map, width="stretch")

    with col_rank:
        st.markdown(f"<h3 style='color: {TEXT_PRIMARY}; font-size: 1.15rem; font-weight: 700;'>📊 Station Rankings (Right Now)</h3>", unsafe_allow_html=True)
        if latest_stations.empty:
            st.info("No current station data.")
        else:
            fig_rank = px.bar(
                latest_stations,
                x="aqi",
                y="label",
                orientation="h",
                color="category",
                color_discrete_map=CATEGORY_COLORS,
                category_orders={"category": ORDER},
                labels={"aqi": "AQI", "label": ""},
                hover_data={"aqi": ":.0f", "category": True, "area": True},
            )
            fig_rank.update_yaxes(autorange="reversed", tickfont=dict(size=11, color=TEXT_PRIMARY))
            fig_rank.update_xaxes(range=[0, max(500, latest_stations["aqi"].max() + 25)])
            chart_h = max(480, 24 * len(latest_stations) + 80)
            show_chart(fig_rank, height=chart_h)

# =============================================================================
# TAB 3: HEATMAP & DIURNAL PATTERNS
# =============================================================================
with tab_patterns:
    if valid_aqi_df.empty:
        st.info("Need valid AQI records to visualize patterns.")
    else:
        st.markdown(f"<h3 style='color: {TEXT_PRIMARY}; font-size: 1.15rem; font-weight: 700;'>🔥 City AQI by Day & Hour (IST)</h3>", unsafe_allow_html=True)
        st.caption("Matrix showing hourly city-wide average AQI across all monitoring stations.")

        matrix_df = (
            valid_aqi_df.assign(date=valid_aqi_df["ts"].dt.date, hour=valid_aqi_df["ts"].dt.hour)
            .pivot_table(index="date", columns="hour", values="aqi", aggfunc="mean")
        )

        fig_heat = px.imshow(
            matrix_df,
            aspect="auto",
            zmin=0,
            zmax=500,
            color_continuous_scale=cpcb_color_scale(),
            labels={"x": "Hour of Day (IST)", "y": "Date", "color": "AQI"},
        )
        fig_heat.update_xaxes(dtick=1, tickformat="%02d:00")
        fig_heat.update_coloraxes(colorbar=dict(thickness=14, len=0.8, title="AQI"))
        show_chart(fig_heat, height=420)

        col_p1, col_p2 = st.columns(2, gap="medium")

        with col_p1:
            st.markdown(f"<h3 style='color: {TEXT_PRIMARY}; font-size: 1.1rem; font-weight: 700;'>🕒 Diurnal Profile (24-Hour Cycle)</h3>", unsafe_allow_html=True)
            hourly_prof = analysis.hourly_profile(df)
            if not hourly_prof.empty:
                peak_h = hourly_prof.idxmax()
                clean_h = hourly_prof.idxmin()
                fig_hour = px.bar(
                    x=hourly_prof.index,
                    y=hourly_prof.values,
                    labels={"x": "Hour of Day (00 to 23 IST)", "y": "Average AQI"},
                )
                fig_hour.update_traces(
                    marker_color=[
                        "#C00000" if h == peak_h else "#00B050" if h == clean_h else "#3B82F6"
                        for h in hourly_prof.index
                    ]
                )
                fig_hour.update_xaxes(dtick=2)
                show_chart(fig_hour, height=330)
                st.caption(
                    f"🔴 Peak pollution hour: **{peak_h:02d}:00 IST** (AQI {hourly_prof.max():.0f}) · "
                    f"🟢 Cleanest air hour: **{clean_h:02d}:00 IST** (AQI {hourly_prof.min():.0f})"
                )

        with col_p2:
            st.markdown(f"<h3 style='color: {TEXT_PRIMARY}; font-size: 1.1rem; font-weight: 700;'>📦 Hours in Each CPCB Category</h3>", unsafe_allow_html=True)
            dist = (
                valid_aqi_df["category"]
                .value_counts()
                .reindex(ORDER, fill_value=0)
                .rename_axis("category")
                .reset_index(name="hours")
            )
            fig_dist = px.bar(
                dist,
                x="category",
                y="hours",
                color="category",
                color_discrete_map=CATEGORY_COLORS,
                labels={"category": "", "hours": "Total Hours"},
            )
            show_chart(fig_dist, height=330)

# =============================================================================
# TAB 4: TREND OVER TIME & POLLUTANT VIEW
# =============================================================================
with tab_trends:
    st.markdown(f"<h3 style='color: {TEXT_PRIMARY}; font-size: 1.15rem; font-weight: 700;'>📈 Air Quality Trends Over Time</h3>", unsafe_allow_html=True)
    
    view_mode = st.radio(
        "Trend View",
        ["AQI Trend (City Average + Stations)", "Pollutant Concentrations (PM2.5, PM10, NO₂, O₃)"],
        horizontal=True,
    )

    if view_mode == "AQI Trend (City Average + Stations)":
        daily_st = analysis.daily_station_aqi(df)
        city_avg = analysis.daily_city_aqi(df)

        fig_trend = go.Figure()

        if not daily_st.empty:
            for station_name in daily_st["label"].unique():
                sdf = daily_st[daily_st["label"] == station_name]
                fig_trend.add_trace(
                    go.Scatter(
                        x=sdf["date"],
                        y=sdf["aqi"],
                        name=station_name,
                        mode="lines",
                        line=dict(width=1.5),
                        opacity=0.4,
                        hoverinfo="name+x+y",
                    )
                )

        if not city_avg.empty:
            fig_trend.add_trace(
                go.Scatter(
                    x=city_avg.index,
                    y=city_avg.values,
                    name="City Average",
                    mode="lines",
                    line=dict(color="#0F172A", width=3.5),
                )
            )

        fig_trend.update_layout(
            title="Daily Average AQI (Bold: City-Wide Basin Mean)",
            yaxis_title="AQI",
            xaxis_title="Date",
        )
        show_chart(fig_trend, height=440)

    else:
        st.caption("Raw hourly concentrations (µg/m³) across selected stations.")
        pollutant_choice = st.selectbox(
            "Select Pollutant",
            ["pm25", "pm10", "no2", "o3"],
            format_func=lambda x: {
                "pm25": "PM2.5 (Fine Particulate Matter, 24h standard: 60 µg/m³)",
                "pm10": "PM10 (Coarse Particulate Matter, 24h standard: 100 µg/m³)",
                "no2": "NO₂ (Nitrogen Dioxide, 24h standard: 80 µg/m³)",
                "o3": "O₃ (Ground Ozone, 8h standard: 100 µg/m³)",
            }[x],
        )

        p_name = pollutant_choice.upper()
        p_threshold = {"pm25": 60, "pm10": 100, "no2": 80, "o3": 100}.get(pollutant_choice, 60)
        p_color = {"pm25": "#EA580C", "pm10": "#0284C7", "no2": "#D97706", "o3": "#16A34A"}.get(
            pollutant_choice, "#EA580C"
        )

        city_p = df.groupby("ts")[pollutant_choice].mean().dropna()

        fig_p = go.Figure()
        fig_p.add_trace(
            go.Scatter(
                x=city_p.index,
                y=city_p.values,
                name=f"City Mean {p_name}",
                line=dict(color=p_color, width=2.5),
            )
        )
        fig_p.add_hline(
            y=p_threshold,
            line_dash="dash",
            line_color="#DC2626",
            annotation_text=f"CPCB Standard ({p_threshold} µg/m³)",
            annotation_position="top left",
        )
        fig_p.update_layout(
            title=f"Hourly Basin Average {p_name} Concentration (µg/m³)",
            yaxis_title=f"{p_name} (µg/m³)",
            xaxis_title="Date & Time (IST)",
        )
        show_chart(fig_p, height=420)

# =============================================================================
# TAB 5: STATION DEEP-DIVE
# =============================================================================
with tab_station:
    st.markdown(f"<h3 style='color: {TEXT_PRIMARY}; font-size: 1.15rem; font-weight: 700;'>🔬 Station Deep-Dive Analysis</h3>", unsafe_allow_html=True)
    if valid_aqi_df.empty:
        st.info("No valid station data available.")
    else:
        station_picker = st.selectbox("Select Station for Full Audit", sorted(valid_aqi_df["label"].unique()))
        st_valid = valid_aqi_df[valid_aqi_df["label"] == station_picker].sort_values("ts")
        st_raw = df[df["label"] == station_picker].sort_values("ts")

        if st_valid.empty:
            st.info("No calculated AQI values available for this station.")
        else:
            latest_row = st_valid.iloc[-1]
            worst_row = st_valid.loc[st_valid["aqi"].idxmax()]
            pct_st_poor = st_valid["category"].isin(config.POOR_OR_WORSE).mean() * 100

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Latest AQI", f"{latest_row['aqi']:.0f}", latest_row["category"])
            k2.metric("Period Mean AQI", f"{st_valid['aqi'].mean():.0f}")
            k3.metric("Peak Recorded Hour", f"{worst_row['aqi']:.0f}", worst_row["ts"].strftime("%d %b, %H:%M"))
            k4.metric("Hours Poor or Worse", f"{pct_st_poor:.1f}%")

            fig_audit = go.Figure()
            max_y = max(100, st_valid["aqi"].max() * 1.12)
            lo = 0
            for upper, cat_name, c_color in config.AQI_CATEGORIES:
                if lo < max_y:
                    fig_audit.add_hrect(
                        y0=lo,
                        y1=min(upper, max_y),
                        fillcolor=c_color,
                        opacity=0.14,
                        line_width=0,
                        annotation_text=cat_name,
                        annotation_position="top left",
                        annotation_font_color=TEXT_MUTED,
                    )
                lo = upper

            fig_audit.add_trace(
                go.Scatter(
                    x=st_valid["ts"],
                    y=st_valid["aqi"],
                    mode="lines",
                    name="AQI",
                    line=dict(color="#0F172A", width=2.5),
                )
            )
            fig_audit.update_layout(
                title=f"{station_picker} — Continuous AQI with CPCB Category Bands",
                yaxis=dict(range=[0, max_y], title="AQI"),
                xaxis_title="Date & Time (IST)",
            )
            show_chart(fig_audit, height=430)

            col_part, col_gases = st.columns(2, gap="medium")
            with col_part:
                fig_pm = go.Figure()
                fig_pm.add_trace(go.Scatter(x=st_raw["ts"], y=st_raw["pm25"], name="PM2.5", line=dict(color="#EA580C", width=1.5)))
                fig_pm.add_trace(go.Scatter(x=st_raw["ts"], y=st_raw["pm10"], name="PM10", line=dict(color="#0284C7", width=1.5)))
                fig_pm.update_layout(title="Particulate Concentrations (µg/m³)", yaxis_title="µg/m³")
                show_chart(fig_pm, height=310)

            with col_gases:
                fig_gas = go.Figure()
                fig_gas.add_trace(go.Scatter(x=st_raw["ts"], y=st_raw["no2"], name="NO₂", line=dict(color="#D97706", width=1.5)))
                fig_gas.add_trace(go.Scatter(x=st_raw["ts"], y=st_raw["o3"], name="O₃", line=dict(color="#16A34A", width=1.5)))
                fig_gas.update_layout(title="Gaseous Concentrations (µg/m³)", yaxis_title="µg/m³")
                show_chart(fig_gas, height=310)

# =============================================================================
# TAB 6: COMPARE STATIONS (2 to 4 Stations)
# =============================================================================
with tab_compare:
    st.markdown(f"<h3 style='color: {TEXT_PRIMARY}; font-size: 1.15rem; font-weight: 700;'>⚖️ Compare Stations Side-by-Side</h3>", unsafe_allow_html=True)
    st.caption("Select 2 to 4 monitoring stations to benchmark their air quality trajectories.")

    all_station_labels = sorted(valid_aqi_df["label"].unique())
    default_compare = all_station_labels[:2] if len(all_station_labels) >= 2 else all_station_labels

    compared_stations = st.multiselect(
        "Select 2 to 4 Stations to Compare",
        options=all_station_labels,
        default=default_compare,
        max_selections=4,
    )

    if len(compared_stations) < 2:
        st.info("Please pick at least 2 stations to enable side-by-side comparison.")
    else:
        cmp_cols = st.columns(len(compared_stations))
        for idx, s_name in enumerate(compared_stations):
            s_data = valid_aqi_df[valid_aqi_df["label"] == s_name]
            if not s_data.empty:
                s_latest = s_data.sort_values("ts").iloc[-1]
                s_mean = s_data["aqi"].mean()
                s_pct_poor = s_data["category"].isin(config.POOR_OR_WORSE).mean() * 100
                with cmp_cols[idx]:
                    st.markdown(
                        f"""
                        <div style="background: #FFFFFF; border: 1px solid {BORDER_COLOR}; border-radius: 12px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
                            <div style="font-weight: 800; font-size: 0.95rem; margin-bottom: 6px; color: {TEXT_PRIMARY};">{s_name}</div>
                            <div style="font-size: 0.82rem; color: {TEXT_MUTED};">Latest AQI: <strong style="color: {CATEGORY_COLORS.get(s_latest['category'], '#000')}; font-family: {MONO_FONT};">{s_latest['aqi']:.0f} ({s_latest['category']})</strong></div>
                            <div style="font-size: 0.82rem; color: {TEXT_MUTED};">Mean AQI: <strong style="font-family: {MONO_FONT}; color: {TEXT_PRIMARY};">{s_mean:.0f}</strong></div>
                            <div style="font-size: 0.82rem; color: {TEXT_MUTED};">Poor or Worse: <strong style="font-family: {MONO_FONT}; color: #EA580C;">{s_pct_poor:.1f}%</strong></div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        fig_cmp = go.Figure()
        palette = ["#2563EB", "#D97706", "#7C3AED", "#059669"]
        for i, s_name in enumerate(compared_stations):
            s_data = valid_aqi_df[valid_aqi_df["label"] == s_name].sort_values("ts")
            fig_cmp.add_trace(
                go.Scatter(
                    x=s_data["ts"],
                    y=s_data["aqi"],
                    name=s_name,
                    mode="lines",
                    line=dict(color=palette[i % len(palette)], width=2.4),
                )
            )

        fig_cmp.update_layout(
            title="Side-by-Side AQI Timeline",
            yaxis_title="AQI",
            xaxis_title="Date & Time (IST)",
        )
        show_chart(fig_cmp, height=440)

# =============================================================================
# TAB 7: 24-HOUR FORECAST
# =============================================================================
with tab_forecast:
    st.markdown(f"<h3 style='color: {TEXT_PRIMARY}; font-size: 1.15rem; font-weight: 700;'>🔮 24-Hour Statistical Air Quality Projection</h3>", unsafe_allow_html=True)

    city_series = forecast.city_hourly(df)
    fc_df = forecast.forecast_24h(city_series)

    if fc_df is None or len(city_series) < 72:
        st.info("⚠️ Requires at least 72 hours of continuous historical city AQI data to compute the projection.")
    else:
        history_window = city_series.iloc[-72:]

        fig_fc = go.Figure()

        fig_fc.add_trace(
            go.Scatter(
                x=list(fc_df["ts"]) + list(fc_df["ts"])[::-1],
                y=list(fc_df["hi"]) + list(fc_df["lo"])[::-1],
                fill="toself",
                fillcolor="rgba(14, 165, 233, 0.12)",
                line=dict(width=0),
                name="Uncertainty Corridor (~80%)",
                hoverinfo="skip",
            )
        )

        fig_fc.add_trace(
            go.Scatter(
                x=history_window.index,
                y=history_window.values,
                name="Observed History",
                line=dict(color="#0F172A", width=2.5),
            )
        )

        fig_fc.add_trace(
            go.Scatter(
                x=fc_df["ts"],
                y=fc_df["aqi"],
                name="Statistical Baseline",
                line=dict(color="#0284C7", width=2.5, dash="dash"),
            )
        )

        fig_fc.update_layout(
            title="City AQI: Observed (Last 72h) & Projected Next 24 Hours (IST)",
            yaxis_title="AQI",
            xaxis_title="Time (IST)",
        )
        show_chart(fig_fc, height=430)

        fc_peak = fc_df.loc[fc_df["aqi"].idxmax()]
        fc_avg = fc_df["aqi"].mean()
        delta_now = fc_avg - city_series.iloc[-1]

        f1, f2, f3 = st.columns(3)
        f1.metric("Expected 24h Average", f"{fc_avg:.0f}", analysis.aqi_category(fc_avg))
        f2.metric("Expected Peak AQI", f"{fc_peak['aqi']:.0f}", fc_peak["ts"].strftime("%a %H:%M IST"))
        f3.metric("Projected Trend vs Now", f"{delta_now:+.0f} pts")

        st.markdown(
            f"""
            <div style="background: #F1F5F9; border: 1px solid {BORDER_COLOR}; border-radius: 10px; padding: 14px 18px; margin-top: 14px; font-size: 0.85rem; color: {TEXT_MUTED};">
                ℹ️ <strong>Methodology Note:</strong> This is an honest statistical baseline combining current persistence
                (decaying with a 12-hour half-life) and the empirical 14-day diurnal hour-of-day profile.
                It does not model meteorology, wind velocity, stubble burning fires, or thermal inversions. Treat as an ungrounded baseline.
            </div>
            """,
            unsafe_allow_html=True,
        )

# =============================================================================
# TAB 8: INSIGHTS & DATA EXPORT
# =============================================================================
with tab_insights:
    st.markdown(f"<h3 style='color: {TEXT_PRIMARY}; font-size: 1.15rem; font-weight: 700;'>💡 Analytical Insights & Statistical Tests</h3>", unsafe_allow_html=True)

    def render_card(title: str, text: str | None) -> None:
        content = text if text else "Not enough data yet."
        st.markdown(
            f"""
            <div class="insight-card">
                <div style="font-weight: 800; font-size: 1.05rem; color: {TEXT_PRIMARY}; margin-bottom: 6px;">{title}</div>
                <div style="color: {TEXT_SECONDARY}; font-size: 0.94rem; line-height: 1.55;">{content}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    hrs = analysis.peak_and_cleanest_hour(df)
    render_card(
        "Diurnal Extremes (Peak vs Cleanest Hour)",
        None
        if hrs is None
        else f"Air quality is on average most severe around <strong>{hrs['peak_hour']:02d}:00 IST</strong> (Mean AQI {hrs['peak_aqi']:.0f}), "
        f"and reaches its cleanest level around <strong>{hrs['clean_hour']:02d}:00 IST</strong> (Mean AQI {hrs['clean_aqi']:.0f}).",
    )

    extremes = analysis.most_least_polluted(df)
    render_card(
        "Station Extremes (Highest vs Lowest Average AQI)",
        None
        if extremes is None
        else f"Highest sustained pollution: <strong>{extremes['most']}</strong> (Mean AQI {extremes['most_aqi']:.0f})<br/>"
        f"Lowest sustained pollution: <strong>{extremes['least']}</strong> (Mean AQI {extremes['least_aqi']:.0f})",
    )

    diwali_res = analysis.diwali_comparison(df_all[df_all["label"].isin(selected_labels)])
    render_card(
        f"Diwali Impact Analysis ({config.DIWALI_DATE:%d %b %Y}: 7 Days Before vs After)",
        None
        if diwali_res is None
        else f"City AQI shifted from <strong>{diwali_res['before']:.0f}</strong> to <strong>{diwali_res['after']:.0f}</strong> "
        f"({diwali_res['change_pct']:+.1f}%), evaluating {diwali_res['days_before']} days before and {diwali_res['days_after']} days after.",
    )

    ww_res = analysis.weekday_weekend_test(df)
    render_card(
        "Weekday vs Weekend Effect (Welch's t-test)",
        None
        if ww_res is None
        else f"Weekday Mean: <strong>{ww_res['weekday_mean']:.0f}</strong> vs Weekend Mean: <strong>{ww_res['weekend_mean']:.0f}</strong> "
        f"({ww_res['n_weekday']} weekdays vs {ww_res['n_weekend']} weekend days). {ww_res['text']}",
    )

    corr_pm_no2 = analysis.pm25_no2_correlation(df)
    render_card(
        "PM2.5 vs NO₂ Source Coupling",
        None if corr_pm_no2 is None else corr_pm_no2["text"],
    )

    corr_mat = analysis.correlation_matrix(df)
    if corr_mat is not None:
        st.markdown(f"<h5 style='color: {TEXT_PRIMARY}; font-weight: 700; margin-top: 14px;'>🔬 Pollutant Correlation Matrix (Hourly)</h5>", unsafe_allow_html=True)
        fig_cm = px.imshow(
            corr_mat,
            text_auto=".2f",
            zmin=-1,
            zmax=1,
            color_continuous_scale="RdBu_r",
            labels={"color": "Pearson r"},
        )
        show_chart(fig_cm, height=360)

    st.markdown("---")
    st.markdown(f"<h3 style='color: {TEXT_PRIMARY}; font-size: 1.15rem; font-weight: 700;'>💾 Download & Inspect Filtered Dataset</h3>", unsafe_allow_html=True)

    cols_export = [
        "label",
        "area",
        "ts",
        "pm25",
        "pm10",
        "no2",
        "o3",
        "pm25_24h",
        "pm10_24h",
        "aqi",
        "category",
        "source",
    ]
    export_df = df[[c for c in cols_export if c in df.columns]].sort_values("ts", ascending=False)

    csv_payload = export_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Filtered Data as CSV",
        data=csv_payload,
        file_name="delhi_ncr_aqi_filtered.csv",
        mime="text/csv",
    )

    st.dataframe(export_df.head(250), width="stretch", hide_index=True)

# -----------------------------------------------------------------------------
# Footer
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown(
    f"""
    <div style="font-size: 0.82rem; color: {TEXT_MUTED}; line-height: 1.6; text-align: center;">
        <strong>CPCB National Air Quality Index (NAQI 2014)</strong>: 24-hour rolling averages of PM2.5 and PM10 with ≥16 valid hours.
        AQI is the maximum sub-index capped at 500.<br/>
        Primary Data: OpenAQ v3 API. Model Fallback: Copernicus Atmosphere Monitoring Service (CAMS) via Open-Meteo.
    </div>
    """,
    unsafe_allow_html=True,
)
