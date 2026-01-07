import streamlit as st
import geopandas as gpd
import pandas as pd
import plotly.graph_objects as go
import json
import unicodedata
from shapely.geometry import LineString, MultiLineString

# =============================================================================
# PAGE
# =============================================================================
st.set_page_config(page_title="Türkiye Satış Haritası", layout="wide")
st.title("🗺️ Türkiye – Bölge & Şehir Bazlı Kutu Adetleri")

# =============================================================================
# COLORS
# =============================================================================
REGION_COLORS = {
    "MARMARA": "#1f4fd8",
    "KARADENİZ": "#2e8b57",
    "İÇ ANADOLU": "#8b6b4a",
    "GÜNEYDOĞU ANADOLU": "#5c3a21"
}

# =============================================================================
# NORMALIZE
# =============================================================================
def normalize_city(s):
    if pd.isna(s):
        return None
    s = str(s).upper().strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = (
        s.replace("I", "İ")
         .replace("Ğ", "G")
         .replace("Ü", "U")
         .replace("Ş", "S")
         .replace("Ö", "O")
         .replace("Ç", "C")
    )
    return s

# =============================================================================
# LOAD
# =============================================================================
@st.cache_data
def load_excel(file):
    return pd.read_excel(file)

@st.cache_resource
def load_geo():
    return gpd.read_file("turkey.geojson")

# =============================================================================
# PREPARE
# =============================================================================
@st.cache_data
def prepare(df, gdf):
    df = df.copy()
    gdf = gdf.copy()

    df["CITY_KEY"] = df["Şehir"].apply(normalize_city)
    df["Bölge"] = df["Bölge"].str.upper()
    df["Kutu Adet"] = pd.to_numeric(df["Kutu Adet"], errors="coerce").fillna(0)

    gdf["CITY_KEY"] = gdf["name"].apply(normalize_city)

    city_total = (
        df.groupby(["CITY_KEY", "Şehir", "Bölge"], as_index=False)
        ["Kutu Adet"].sum()
    )

    merged = gdf.merge(city_total, on="CITY_KEY", how="left")

    merged["Bölge"] = merged["Bölge"].fillna("BİLİNMİYOR")
    merged["Kutu Adet"] = merged["Kutu Adet"].fillna(0)

    return merged

# =============================================================================
# GEOM
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
# FIGURE
# =============================================================================
def create_fig(gdf):
    fig = go.Figure()

    # Borders
    lons, lats = [], []
    for g in gdf.geometry.boundary:
        lo, la = lines_to_lonlat(g)
        lons += lo
        lats += la

    fig.add_scattergeo(
        lon=lons,
        lat=lats,
        mode="lines",
        line=dict(color="rgba(80,80,80,0.5)", width=0.8),
        hoverinfo="skip"
    )

    # REGION
    region_df = (
        gdf[gdf["Bölge"] != "BİLİNMİYOR"]
        .dissolve(by="Bölge", aggfunc={"Kutu Adet": "sum"})
        .reset_index()
    )

    fig.add_trace(
        go.Choropleth(
            geojson=json.loads(region_df.to_json()),
            locations=region_df["Bölge"],
            featureidkey="properties.Bölge",
            z=region_df["Bölge"].map(lambda x: 1),
            colorscale=[
                [0, REGION_COLORS[r]] for r in region_df["Bölge"]
            ],
            showscale=False,
            hovertemplate="<b>%{location}</b><br>Toplam: %{customdata:,}<extra></extra>",
            customdata=region_df["Kutu Adet"]
        )
    )

    # CITY POINTS
    cp = gdf.to_crs(3857)
    cp["centroid"] = cp.geometry.centroid
    cp = cp.to_crs(gdf.crs)

    fig.add_scattergeo(
        lon=cp.centroid.x,
        lat=cp.centroid.y,
        mode="markers",
        marker=dict(size=6, color="black"),
        text=[
            f"<b>{r['Şehir']}</b><br>Kutu Adet: {int(r['Kutu Adet']):,}"
            for _, r in cp.iterrows()
        ],
        hovertemplate="%{text}<extra></extra>"
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
# APP
# =============================================================================
uploaded = st.sidebar.file_uploader("Excel Yükle", type=["xlsx", "xls"])
if uploaded is None:
    st.stop()

df = load_excel(uploaded)
gdf = load_geo()
merged = prepare(df, gdf)

fig = create_fig(merged)
st.plotly_chart(fig, use_container_width=True)
