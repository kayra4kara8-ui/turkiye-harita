import streamlit as st
import geopandas as gpd
import pandas as pd
import plotly.graph_objects as go
import json
import unicodedata
from shapely.geometry import LineString, MultiLineString

# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(page_title="Türkiye Satış Haritası", layout="wide")
st.title("🗺️ Türkiye – Bölge & Şehir Bazlı Kutu Adetleri")

# =============================================================================
# CONSTANTS
# =============================================================================
REGION_COLORS = {
    "MARMARA": "#2F6FD6",
    "İÇ ANADOLU": "#8B6B4A",
    "BATI ANADOLU": "#2BB0A6",
    "KUZEY ANADOLU": "#2E8B57",
    "GÜNEY DOĞU ANADOLU": "#A05A2C"
}

# =============================================================================
# CITY NORMALIZATION (KRİTİK)
# =============================================================================
def normalize_city(s):
    if pd.isna(s):
        return None
    s = str(s).upper().strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("I", "İ")
    return s

# =============================================================================
# DATA LOADING
# =============================================================================
@st.cache_data
def load_excel(uploaded_file=None):
    if uploaded_file is not None:
        return pd.read_excel(uploaded_file)
    return pd.read_excel("Data.xlsx")

@st.cache_resource
def load_geojson():
    return gpd.read_file("turkey.geojson")

# =============================================================================
# DATA PREPARATION
# =============================================================================
@st.cache_data
def prepare_data(df, _gdf):
    df = df.copy()
    gdf = _gdf.copy()

    df["CITY_KEY"] = df["Şehir"].apply(normalize_city)
    df["Bölge"] = df["Bölge"].str.upper()
    df["Kutu Adet"] = pd.to_numeric(df["Kutu Adet"], errors="coerce").fillna(0)

    gdf["CITY_KEY"] = gdf["name"].apply(normalize_city)

    merged = gdf.merge(
        df,
        on="CITY_KEY",
        how="left"
    )

    merged["Kutu Adet"] = merged["Kutu Adet"].fillna(0)

    return merged

# =============================================================================
# GEOMETRY HELPERS
# =============================================================================
def lines_to_lonlat(geom):
    lons, lats = [], []
    if isinstance(geom, LineString):
        xs, ys = geom.xy
        lons += list(xs) + [None]
        lats += list(ys) + [None]
    elif isinstance(geom, MultiLineString):
        for g in geom.geoms:
            xs, ys = g.xy
            lons += list(xs) + [None]
            lats += list(ys) + [None]
    return lons, lats

# =============================================================================
# MAP CREATION
# =============================================================================
def create_figure(gdf, selected_manager):
    fig = go.Figure()

    # İl sınırları
    lons, lats = [], []
    for geom in gdf.geometry.boundary:
        lo, la = lines_to_lonlat(geom)
        lons += lo
        lats += la

    fig.add_scattergeo(
        lon=lons,
        lat=lats,
        mode="lines",
        line=dict(color="rgba(80,80,80,0.5)", width=0.8),
        hoverinfo="skip",
        showlegend=False
    )

    # Müdür filtresi
    if selected_manager != "Tümü":
        gdf = gdf[gdf["Ticaret Müdürü"] == selected_manager]

    # Bölge bazlı dissolve
    region_df = (
        gdf.dropna(subset=["Bölge"])
        .dissolve(by="Bölge", aggfunc={"Kutu Adet": "sum"})
        .reset_index()
    )

    fig.add_trace(
        go.Choropleth(
            geojson=json.loads(region_df.to_json()),
            locations=region_df["Bölge"],
            featureidkey="properties.Bölge",
            z=region_df["Kutu Adet"],
            colorscale="Blues",
            showscale=False,
            hovertemplate="<b>%{location}</b><br>Kutu Adet: %{z:,}<extra></extra>"
        )
    )

    # Şehir centroid + hover / tıklama bilgisi
    city_points = gdf.to_crs(3857)
    city_points["centroid"] = city_points.geometry.centroid
    city_points = city_points.to_crs(gdf.crs)

    fig.add_scattergeo(
        lon=city_points.centroid.x,
        lat=city_points.centroid.y,
        mode="markers",
        marker=dict(size=6, color="black"),
        text=[
            f"""
            <b>{r['Şehir']}</b><br>
            Bölge: {r['Bölge']}<br>
            Müdür: {r['Ticaret Müdürü']}<br>
            Kutu Adet: {int(r['Kutu Adet']):,}
            """
            for _, r in city_points.iterrows()
        ],
        hovertemplate="%{text}<extra></extra>",
        showlegend=False
    )

    fig.update_layout(
        geo=dict(
            scope="europe",
            center=dict(lat=39, lon=35),
            projection_scale=4.5,
            visible=False
        ),
        height=750,
        margin=dict(l=0, r=0, t=60, b=0)
    )

    return fig

# =============================================================================
# APP FLOW
# =============================================================================
st.sidebar.header("📂 Dosya Yükleme")
uploaded_file = st.sidebar.file_uploader("Excel Dosyası", type=["xlsx", "xls"])

df = load_excel(uploaded_file)
gdf = load_geojson()

merged = prepare_data(df, gdf)

st.sidebar.header("🔍 Filtre")
managers = ["Tümü"] + sorted(merged["Ticaret Müdürü"].dropna().unique())
selected_manager = st.sidebar.selectbox("Ticaret Müdürü", managers)

fig = create_figure(merged, selected_manager)
st.plotly_chart(fig, use_container_width=True)
