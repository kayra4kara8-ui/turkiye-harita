import streamlit as st
import geopandas as gpd
import pandas as pd
import plotly.graph_objects as go
import json
from shapely.geometry import LineString, MultiLineString
import warnings

warnings.filterwarnings("ignore")

# =============================================================================
# TÜRKÇE KARAKTER NORMALİZASYONU (KRİTİK)
# =============================================================================
def tr_upper(text):
    if pd.isna(text):
        return text
    text = str(text)
    return (
        text.replace("i", "İ")
            .replace("ı", "I")
            .upper()
            .replace("Ğ", "G")
            .replace("Ş", "S")
            .replace("Ü", "U")
            .replace("Ö", "O")
            .replace("Ç", "C")
    )

# =============================================================================
# BÖLGE RENKLERİ
# =============================================================================
REGION_COLORS = {
    "MARMARA": "#1f77b4",              # Mavi
    "KARADENIZ": "#2ca02c",             # Yeşil
    "EGE": "#17becf",
    "AKDENIZ": "#ff7f0e",
    "IC ANADOLU": "#8c564b",            # Kahverengi
    "DOGU ANADOLU": "#a0522d",
    "GUNEYDOGU ANADOLU": "#5a2d0c"      # Koyu kahve
}

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
def prepare_data(df, turkey_map):

    df = df.copy()
    turkey_map = turkey_map.copy()

    # 🔴 TÜRKÇE NORMALİZASYON
    df["Şehir"] = df["Şehir"].apply(tr_upper)
    df["Bölge"] = df["Bölge"].apply(tr_upper)
    df["Ticaret Müdürü"] = df["Ticaret Müdürü"].apply(tr_upper)

    turkey_map["name"] = turkey_map["name"].apply(tr_upper)

    # Numeric
    df["Kutu Adet"] = pd.to_numeric(df["Kutu Adet"], errors="coerce").fillna(0)

    # Merge (ŞEHİR ↔ GEOJSON)
    merged = turkey_map.merge(
        df,
        left_on="name",
        right_on="Şehir",
        how="left"
    )

    merged["Kutu Adet"] = merged["Kutu Adet"].fillna(0)
    merged["Bölge"] = merged["Bölge"].fillna("DİĞER")

    bolge_df = (
        merged.groupby("Bölge", as_index=False)["Kutu Adet"]
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

    region_df = gdf.dissolve(by="Bölge", aggfunc={"Kutu Adet": "sum"}).reset_index()
    region_df["color"] = region_df["Bölge"].map(REGION_COLORS).fillna("#cccccc")

    geojson = json.loads(region_df.to_json())

    # Bölge renkleri
    for _, r in region_df.iterrows():
        traces.append(
            go.Choropleth(
                geojson=geojson,
                locations=[r["Bölge"]],
                z=[1],
                featureidkey="properties.Bölge",
                colorscale=[[0, r["color"]], [1, r["color"]]],
                showscale=False,
                marker_line_color="black",
                marker_line_width=1,
                hovertemplate=f"<b>{r['Bölge']}</b><br>Kutu Adet: {int(r['Kutu Adet']):,}<extra></extra>"
            )
        )

    # LABELS
    rp = region_df.to_crs(3857)
    rp["centroid"] = rp.geometry.centroid
    rp = rp.to_crs(region_df.crs)

    traces.append(
        go.Scattergeo(
            lon=rp.centroid.x,
            lat=rp.centroid.y,
            mode="text",
            text=[f"<b>{r['Bölge']}</b><br>{int(r['Kutu Adet']):,}" for _, r in rp.iterrows()],
            textfont=dict(color="black", size=12),
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

    # 🔴 FİLTRE
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
        line=dict(color="rgba(120,120,120,0.6)", width=0.6),
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
        height=720,
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

