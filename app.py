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
# CONSTANTS
# =============================================================================
REGION_COLORS = {
    "KUZEY ANADOLU": "#2E8B57",
    "MARMARA": "#2F6FD6",
    "İÇ ANADOLU": "#8B6B4A",
    "BATI ANADOLU": "#2BB0A6",
    "GÜNEY DOĞU ANADOLU": "#A05A2C"
}

CITY_FIX_MAP = {
    "AGRI": "AĞRI",
    "BINGOL": "BİNGÖL",
    "DUZCE": "DÜZCE",
    "ELAZIG": "ELAZIĞ",
    "ESKISEHIR": "ESKİŞEHİR",
    "GUMUSHANE": "GÜMÜŞHANE",
    "HAKKARI": "HAKKARİ",
    "ISTANBUL": "İSTANBUL",
    "IZMIR": "İZMİR",
    "IGDIR": "IĞDIR",
    "KARABUK": "KARABÜK",
    "KIRSEHIR": "KIRŞEHİR",
    "KUTAHYA": "KÜTAHYA",
    "MUGLA": "MUĞLA",
    "MUS": "MUŞ",
    "NEVSEHIR": "NEVŞEHİR",
    "NIGDE": "NİĞDE",
    "SANLIURFA": "ŞANLIURFA",
    "SIRNAK": "ŞIRNAK",
    "TEKIRDAG": "TEKİRDAĞ",
    "USAK": "UŞAK",
    "ZINGULDAK": "ZONGULDAK",
    "CANAKKALE": "ÇANAKKALE",
    "CANKIRI": "ÇANKIRI",
    "CORUM": "ÇORUM"
}

# =============================================================================
# DATA LOADING
# =============================================================================
@st.cache_data
def load_excel(uploaded_file=None):
    if uploaded_file is not None:
        return pd.read_excel(uploaded_file)
    try:
        return pd.read_excel("Data.xlsx")
    except FileNotFoundError:
        return None


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

    # Text normalize
    df["Şehir"] = df["Şehir"].str.upper()
    df["Bölge"] = df["Bölge"].str.upper()
    turkey_map["name"] = turkey_map["name"].str.upper()

    # Fix city names
    turkey_map["CITY_CLEAN"] = turkey_map["name"].replace(CITY_FIX_MAP)

    # Numeric safety
    df["Kutu Adet"] = pd.to_numeric(df["Kutu Adet"], errors="coerce").fillna(0)

    # Merge region info
    city_region = df[["Şehir", "Bölge"]].drop_duplicates()

    turkey_map = turkey_map.merge(
        city_region,
        left_on="CITY_CLEAN",
        right_on="Şehir",
        how="left"
    )

    # Merge full data
    merged = turkey_map.merge(
        df[["Şehir", "Bölge", "Ticaret Müdürü", "Kutu Adet"]],
        left_on="CITY_CLEAN",
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

    gdf = gdf.copy()

    if "Bölge" not in gdf.columns:
        return traces

    gdf = gdf.dropna(subset=["Bölge"])
    if gdf.empty:
        return traces

    region_df = (
        gdf.dissolve(by="Bölge", aggfunc={"Kutu Adet": "sum"})
        .reset_index()
    )

    geojson = json.loads(region_df.to_json())

    traces.append(
        go.Choropleth(
            geojson=geojson,
            locations=region_df["Bölge"],
            featureidkey="properties.Bölge",
            z=region_df["Kutu Adet"],
            colorscale="Viridis",
            showscale=False,
            hovertemplate="<b>%{location}</b><br>Kutu Adet: %{z:,}<extra></extra>"
        )
    )

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

    # City borders
    lons, lats = [], []
    for geom in gdf.geometry.boundary:
        lo, la = lines_to_lonlat(geom)
        lons += lo
        lats += la

    fig.add_scattergeo(
        lon=lons,
        lat=lats,
        mode="lines",
        line=dict(color="rgba(90,90,90,0.5)", width=0.8),
        hoverinfo="skip",
        showlegend=False
    )

    # Filter
    if selected_manager != "Tümü":
        gdf = gdf[gdf["Ticaret Müdürü"] == selected_manager]

    traces = create_map_block(gdf)
    for t in traces:
        fig.add_trace(t)

    fig.update_layout(
        geo=dict(
            scope="europe",
            center=dict(lat=39, lon=35),
            projection_scale=4.5,
            visible=False
        ),
        height=700,
        margin=dict(l=0, r=0, t=60, b=0),
        title="Türkiye - Bölge Bazlı Kutu Adetleri"
    )

    return fig


# =============================================================================
# APP FLOW
# =============================================================================
st.sidebar.header("📂 Dosya Yükleme")
uploaded_file = st.sidebar.file_uploader("Excel Dosyası", type=["xlsx", "xls"])

df = load_excel(uploaded_file)
if df is None:
    st.warning("⚠️ Excel dosyası bulunamadı.")
    st.stop()

try:
    turkey_map = load_turkey_map()
except Exception:
    st.error("❌ turkey.geojson bulunamadı.")
    st.stop()

merged_region, bolge_df = prepare_data(df, turkey_map)

st.sidebar.header("🔍 Filtre")
managers = ["Tümü"] + sorted(
    merged_region["Ticaret Müdürü"].dropna().unique().tolist()
)
selected_manager = st.sidebar.selectbox("Ticaret Müdürü", managers)

fig = create_figure(merged_region, selected_manager)
st.plotly_chart(fig, use_container_width=True)

st.subheader("📋 Bölge Bazlı Detaylar")
st.dataframe(bolge_df, use_container_width=True, hide_index=True)
