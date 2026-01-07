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
def prepare_data(df, _turkey_map):
    df = df.copy()
    turkey_map = _turkey_map.copy()

    # Normalize text
    df["Şehir"] = df["Şehir"].str.upper()
    df["Bölge"] = df["Bölge"].str.upper()
    df["Ticaret Müdürü"] = df["Ticaret Müdürü"].str.upper()
    turkey_map["name"] = turkey_map["name"].str.upper()

    # Numeric
    df["Kutu Adet"] = pd.to_numeric(df["Kutu Adet"], errors="coerce").fillna(0)

    # Merge city -> geometry
    merged = turkey_map.merge(
        df,
        left_on="name",
        right_on="Şehir",
        how="left"
    )

    merged["Kutu Adet"] = merged["Kutu Adet"].fillna(0)

    bolge_df = (
        df.groupby("Bölge", as_index=False)["Kutu Adet"]
        .sum()
        .sort_values("Kutu Adet", ascending=False)
    )

    return merged, bolge_df


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

    if gdf.empty or "Bölge" not in gdf.columns:
        return traces

    # Bölge bazlı tek geometri
    region_df = (
        gdf
        .dissolve(by="Bölge", aggfunc={"Kutu Adet": "sum"})
        .reset_index()
    )

    geojson = json.loads(region_df.to_json())

    # Choropleth
    traces.append(
        go.Choropleth(
            geojson=geojson,
            locations=region_df["Bölge"],
            featureidkey="properties.Bölge",
            z=region_df["Kutu Adet"],
            colorscale="YlOrRd",
            showscale=True,
            marker_line_color="white",
            marker_line_width=0.8,
            hovertemplate="<b>%{location}</b><br>Kutu Adet: %{z:,}<extra></extra>"
        )
    )

    # Labels
    rp = region_df.to_crs(3857)
    rp["centroid"] = rp.geometry.centroid
    rp = rp.to_crs(region_df.crs)

    traces.append(
        go.Scattergeo(
            lon=rp.centroid.x,
            lat=rp.centroid.y,
            mode="text",
            text=[
                f"<b>{r['Bölge']}</b><br>{int(r['Kutu Adet']):,}"
                for _, r in rp.iterrows()
            ],
            hoverinfo="skip",
            showlegend=False
        )
    )

    return traces


# =============================================================================
# FIGURE
# =============================================================================
def create_figure(gdf, selected_manager):
    fig = go.Figure()

    # 🔴 ÖNCE FİLTRE
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
        line=dict(color="rgba(120,120,120,0.5)", width=0.6),
        hoverinfo="skip",
        showlegend=False
    )

    # Bölge haritası
    for trace in create_map_block(gdf):
        fig.add_trace(trace)

    fig.update_layout(
        geo=dict(
            scope="europe",
            center=dict(lat=39, lon=35),
            projection_scale=4.7,
            visible=False
        ),
        height=700,
        margin=dict(l=0, r=0, t=40, b=0)
    )

    return fig


# =============================================================================
# APP FLOW
# =============================================================================
st.sidebar.header("📂 Dosya Yükleme")
uploaded_file = st.sidebar.file_uploader("Excel Dosyası", type=["xlsx", "xls"])

df = load_excel(uploaded_file)
turkey_map = load_turkey_map()

merged_region, bolge_df = prepare_data(df, turkey_map)

st.sidebar.header("🔍 Filtre")
managers = ["TÜMÜ"] + sorted(
    merged_region["Ticaret Müdürü"].dropna().unique().tolist()
)
selected_manager = st.sidebar.selectbox("Ticaret Müdürü", managers)

fig = create_figure(merged_region, selected_manager)
st.plotly_chart(fig, use_container_width=True)

st.subheader("📋 Bölge Bazlı Detaylar")
st.dataframe(bolge_df, use_container_width=True, hide_index=True)
