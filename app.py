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
st.set_page_config(page_title="Türkiye Satış Haritası", layout="wide")
st.title("🗺️ Türkiye – Bölge & İl Bazlı Kutu Adetleri")

# =============================================================================
# ŞEHİR EŞLEŞTİRME (MASTER)
# =============================================================================
FIX_CITY_MAP = {
    "AGRI": "AĞRI",
    "BARTÄ±N": "BARTIN",
    "BINGÃ¶L": "BİNGÖL",
    "DÃ¼ZCE": "DÜZCE",
    "ELAZIG": "ELAZIĞ",
    "ESKISEHIR": "ESKİŞEHİR",
    "GÃ¼MÃ¼SHANE": "GÜMÜŞHANE",
    "HAKKARI": "HAKKARİ",
    "ISTANBUL": "İSTANBUL",
    "IZMIR": "İZMİR",
    "IÄ\x9fDIR": "IĞDIR",
    "KARABÃ¼K": "KARABÜK",
    "KINKKALE": "KIRIKKALE",
    "KIRSEHIR": "KIRŞEHİR",
    "KÃ¼TAHYA": "KÜTAHYA",
    "MUGLA": "MUĞLA",
    "MUS": "MUŞ",
    "NEVSEHIR": "NEVŞEHİR",
    "NIGDE": "NİĞDE",
    "SANLIURFA": "ŞANLIURFA",
    "SIRNAK": "ŞIRNAK",
    "TEKIRDAG": "TEKİRDAĞ",
    "USAK": "UŞAK",
    "ZINGULDAK": "ZONGULDAK",
    "Ã\x87ANAKKALE": "ÇANAKKALE",
    "Ã\x87ANKIRI": "ÇANKIRI",
    "Ã\x87ORUM": "ÇORUM",
    "K. MARAS": "KAHRAMANMARAŞ"
}

# =============================================================================
# NORMALIZATION
# =============================================================================
def normalize_city(name):
    if pd.isna(name):
        return None

    name = str(name).upper().strip()

    tr_map = {
        "İ": "I", "I": "I",
        "Ğ": "G", "Ü": "U",
        "Ş": "S", "Ö": "O",
        "Ç": "C", "Â": "A"
    }

    for k, v in tr_map.items():
        name = name.replace(k, v)

    return name

# =============================================================================
# DATA LOAD
# =============================================================================
@st.cache_data
def load_excel(file=None):
    if file is not None:
        return pd.read_excel(file)
    return pd.read_excel("Data.xlsx")

@st.cache_resource
def load_geo():
    gdf = gpd.read_file("turkey.geojson")
    gdf["raw_name"] = gdf["name"].str.upper()
    gdf["fixed_name"] = gdf["raw_name"].replace(FIX_CITY_MAP)
    gdf["CITY_KEY"] = gdf["fixed_name"].apply(normalize_city)
    return gdf

# =============================================================================
# DATA PREP (CACHE YOK – HATA OLMASIN)
# =============================================================================
def prepare_data(df, gdf):

    df = df.copy()
    gdf = gdf.copy()

    df["Şehir_fix"] = df["Şehir"].str.upper().replace(FIX_CITY_MAP)
    df["CITY_KEY"] = df["Şehir_fix"].apply(normalize_city)

    df["Bölge"] = df["Bölge"].str.upper()
    df["Ticaret Müdürü"] = df["Ticaret Müdürü"].str.upper()
    df["Kutu Adet"] = pd.to_numeric(df["Kutu Adet"], errors="coerce").fillna(0)

    merged = gdf.merge(
        df,
        on="CITY_KEY",
        how="left"
    )

    merged["Şehir"] = merged["fixed_name"]
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
# FIGURE
# =============================================================================
def create_figure(gdf, manager):

    if manager != "TÜMÜ":
        gdf = gdf[gdf["Ticaret Müdürü"] == manager]

    fig = go.Figure()

    fig.add_choropleth(
        geojson=json.loads(gdf.to_json()),
        locations=gdf.index,
        z=gdf["Kutu Adet"],
        colorscale="YlGnBu",
        marker_line_color="black",
        marker_line_width=0.5,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Bölge: %{customdata[1]}<br>"
            "Kutu Adet: %{customdata[2]:,}"
            "<extra></extra>"
        ),
        customdata=gdf[["Şehir", "Bölge", "Kutu Adet"]],
        showscale=False
    )

    lons, lats = [], []
    for geom in gdf.geometry.boundary:
        lo, la = lines_to_lonlat(geom)
        lons += lo
        lats += la

    fig.add_scattergeo(
        lon=lons,
        lat=lats,
        mode="lines",
        line=dict(color="rgba(70,70,70,0.5)", width=0.6),
        hoverinfo="skip"
    )

    fig.update_layout(
        geo=dict(
            projection=dict(type="mercator"),
            center=dict(lat=39, lon=35),
            lonaxis=dict(range=[25, 45]),
            lataxis=dict(range=[35, 43]),
            visible=False
        ),
        height=750,
        margin=dict(l=0, r=0, t=40, b=0)
    )

    return fig

# =============================================================================
# APP FLOW
# =============================================================================
st.sidebar.header("📂 Excel Yükle")
uploaded = st.sidebar.file_uploader("Excel Dosyası", ["xlsx", "xls"])

df = load_excel(uploaded)
geo = load_geo()

merged, bolge_df = prepare_data(df, geo)

st.sidebar.header("🔍 Filtre")
managers = ["TÜMÜ"] + sorted(merged["Ticaret Müdürü"].dropna().unique())
selected_manager = st.sidebar.selectbox("Ticaret Müdürü", managers)

fig = create_figure(merged, selected_manager)
st.plotly_chart(fig, use_container_width=True)

st.subheader("📊 Bölge Bazlı Toplamlar")
st.dataframe(bolge_df, use_container_width=True, hide_index=True)
