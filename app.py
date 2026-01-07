import streamlit as st
import geopandas as gpd
import pandas as pd
import plotly.graph_objects as go
import json
from shapely.geometry import LineString, MultiLineString
import warnings

warnings.filterwarnings("ignore")

# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(page_title="Türkiye Bölge Haritası", layout="wide")
st.title("🗺️ Türkiye - Bölge Bazlı Kutu Adetleri")

# =============================================================================
# SABİT BÖLGE RENKLERİ
# =============================================================================
REGION_COLORS = {
    "MARMARA": "#2F6FD6",
    "KARADENİZ": "#2E8B57",
    "İÇ ANADOLU": "#8B6B4A",
    "GÜNEYDOĞU ANADOLU": "#5C4033",
    "EGE": "#6CA6CD",
    "AKDENİZ": "#CD853F",
    "DOĞU ANADOLU": "#556B2F"
}

# Şehir isim düzeltmeleri
CITY_FIX = {
    "ISTANBUL": "İSTANBUL",
    "IZMIR": "İZMİR",
    "SANLIURFA": "ŞANLIURFA",
    "USAK": "UŞAK",
    "MUS": "MUŞ",
    "IGDIR": "IĞDIR",
    "CANAKKALE": "ÇANAKKALE",
    "CANKIRI": "ÇANKIRI",
    "CORUM": "ÇORUM",
    "KIRSEHIR": "KIRŞEHİR",
    "NEVSEHIR": "NEVŞEHİR"
}

# =============================================================================
# DATA LOADING
# =============================================================================
@st.cache_data
def load_excel(uploaded_file=None):
    if uploaded_file is not None:
        return pd.read_excel(uploaded_file)
    return pd.read_excel("Data.xlsx")


@st.cache_resource
def load_turkey_map():
    return gpd.read_file("turkey.geojson")

# =============================================================================
# DATA PREPARATION
# =============================================================================
@st.cache_data
def prepare_data(df, turkey_map):
    df = df.copy()
    gdf = turkey_map.copy()

    # Normalize
    df["Şehir"] = df["Şehir"].str.upper().replace(CITY_FIX)
    df["Bölge"] = df["Bölge"].str.upper()
    df["Ticaret Müdürü"] = df["Ticaret Müdürü"].str.upper()

    gdf["name"] = gdf["name"].str.upper().replace(CITY_FIX)

    df["Kutu Adet"] = pd.to_numeric(df["Kutu Adet"], errors="coerce").fillna(0)

    merged = gdf.merge(
        df,
        left_on="name",
        right_on="Şehir",
        how="left"
    )

    merged["Kutu Adet"] = merged["Kutu Adet"].fillna(0)

    bolge_df = (
        merged.dropna(subset=["Bölge"])
        .groupby("Bölge", as_index=False)["Kutu Adet"]
        .sum()
        .sort_values("Kutu Adet", ascending=False)
    )

    return merged, bolge_df

# =============================================================================
# GEOMETRY
# =============================================================================
def lines_to_lonlat(geom):
    lons, lats = [], []
    if geom is None:
        return lons, lats

    if isinstance(geom, LineString):
        xs, ys = geom.xy
        lons += list(xs) + [None]
        lats += list(ys) + [None]

    elif isinstance(geom, MultiLineString):
        for line in geom.geoms:
            xs, ys = line.xy
            lons += list(xs) + [None]
            lats += list(ys) + [None]

    return lons, lats

# =============================================================================
# MAP BLOCK
# =============================================================================
def create_map_block(gdf):
    traces = []
    gdf = gdf.dropna(subset=["Bölge"])

    region_df = gdf.dissolve(by="Bölge", aggfunc={"Kutu Adet": "sum"}).reset_index()
    region_df["color"] = region_df["Bölge"].map(REGION_COLORS)

    geojson = json.loads(region_df.to_json())

    traces.append(
        go.Choropleth(
            geojson=geojson,
            locations=region_df["Bölge"],
            featureidkey="properties.Bölge",
            z=[1] * len(region_df),
            colorscale=[[0, c], [1, c]] if False else None,
            marker=dict(line=dict(color="black", width=0.6)),
            showscale=False,
            hovertemplate="<b>%{location}</b><br>Toplam: %{customdata:,}<extra></extra>",
            customdata=region_df["Kutu Adet"]
        )
    )

    # Bölge yazıları
    rp = region_df.to_crs(3857)
    rp["centroid"] = rp.geometry.centroid
    rp = rp.to_crs(region_df.crs)

    traces.append(
        go.Scattergeo(
            lon=rp.centroid.x,
            lat=rp.centroid.y,
            text=[
                f"{r['Bölge']}<br>{int(r['Kutu Adet']):,}"
                for _, r in rp.iterrows()
            ],
            mode="text",
            textfont=dict(color="black", size=13),
            hoverinfo="skip"
        )
    )

    return traces

# =============================================================================
# FIGURE
# =============================================================================
def create_figure(gdf, selected_manager):
    fig = go.Figure()

    if selected_manager != "TÜMÜ":
        gdf = gdf[gdf["Ticaret Müdürü"] == selected_manager]

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
        line=dict(color="rgba(80,80,80,0.4)", width=0.5),
        hoverinfo="skip"
    )

    for t in create_map_block(gdf):
        fig.add_trace(t)

    fig.update_layout(
        geo=dict(
            scope="europe",
            center=dict(lat=39, lon=35),
            projection_scale=4.6,
            visible=False
        ),
        height=720,
        margin=dict(l=0, r=0, t=40, b=0)
    )

    return fig

# =============================================================================
# APP FLOW
# =============================================================================
uploaded_file = st.sidebar.file_uploader("Excel Dosyası", type=["xlsx", "xls"])

df = load_excel(uploaded_file)
turkey_map = load_turkey_map()

merged_region, bolge_df = prepare_data(df, turkey_map)

managers = ["TÜMÜ"] + sorted(merged_region["Ticaret Müdürü"].dropna().unique())
selected_manager = st.sidebar.selectbox("Ticaret Müdürü", managers)

fig = create_figure(merged_region, selected_manager)
st.plotly_chart(fig, use_container_width=True)

st.subheader("📋 Bölge Bazlı Detaylar")
st.dataframe(bolge_df, use_container_width=True, hide_index=True)
