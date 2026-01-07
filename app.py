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
# ŞEHİR EŞLEŞTİRME
# =============================================================================
FIX_CITY_MAP = {
    "AGRI": "AĞRI","BARTÄ±N": "BARTIN","BINGÃ¶L": "BİNGÖL","DÃ¼ZCE": "DÜZCE",
    "ELAZIG": "ELAZIĞ","ESKISEHIR": "ESKİŞEHİR","GÃ¼MÃ¼SHANE": "GÜMÜŞHANE",
    "HAKKARI": "HAKKARİ","ISTANBUL": "İSTANBUL","IZMIR": "İZMİR","IÄ\x9fDIR": "IĞDIR",
    "KARABÃ¼K": "KARABÜK","KINKKALE": "KIRIKKALE","KIRSEHIR": "KIRŞEHİR",
    "KÃ¼TAHYA": "KÜTAHYA","MUGLA": "MUĞLA","MUS": "MUŞ","NEVSEHIR": "NEVŞEHİR",
    "NIGDE": "NİĞDE","SANLIURFA": "ŞANLIURFA","SIRNAK": "ŞIRNAK",
    "TEKIRDAG": "TEKİRDAĞ","USAK": "UŞAK","ZINGULDAK": "ZONGULDAK",
    "Ã\x87ANAKKALE": "ÇANAKKALE","Ã\x87ANKIRI": "ÇANKIRI","Ã\x87ORUM": "ÇORUM",
    "K. MARAS": "KAHRAMANMARAŞ"
}

# =============================================================================
# NORMALIZATION
# =============================================================================
def normalize_city(name):
    if pd.isna(name): return None
    name = str(name).upper().strip()
    for k,v in {"İ":"I","Ğ":"G","Ü":"U","Ş":"S","Ö":"O","Ç":"C","Â":"A"}.items():
        name = name.replace(k,v)
    return name

# =============================================================================
# LOAD
# =============================================================================
@st.cache_data
def load_excel(file=None):
    return pd.read_excel(file) if file else pd.read_excel("Data.xlsx")

@st.cache_resource
def load_geo():
    gdf = gpd.read_file("turkey.geojson")
    gdf["fixed_name"] = gdf["name"].str.upper().replace(FIX_CITY_MAP)
    gdf["CITY_KEY"] = gdf["fixed_name"].apply(normalize_city)
    return gdf

# =============================================================================
# PREP
# =============================================================================
def prepare_data(df, gdf):
    df = df.copy()
    gdf = gdf.copy()

    df["CITY_KEY"] = df["Şehir"].str.upper().replace(FIX_CITY_MAP).apply(normalize_city)
    df["Kutu Adet"] = pd.to_numeric(df["Kutu Adet"], errors="coerce").fillna(0)
    df["Bölge"] = df["Bölge"].str.upper()
    df["Ticaret Müdürü"] = df["Ticaret Müdürü"].str.upper()

    merged = gdf.merge(df, on="CITY_KEY", how="left")
    merged["Şehir"] = merged["fixed_name"]
    merged["Kutu Adet"] = merged["Kutu Adet"].fillna(0)
    merged["Bölge"] = merged["Bölge"].fillna("DİĞER")
    merged["Ticaret Müdürü"] = merged["Ticaret Müdürü"].fillna("YOK")

    return merged

# =============================================================================
# GEOMETRY
# =============================================================================
def lines_to_lonlat(geom):
    lons, lats = [], []
    for g in getattr(geom, "geoms", [geom]):
        xs, ys = g.xy
        lons += list(xs) + [None]
        lats += list(ys) + [None]
    return lons, lats

# =============================================================================
# MAP
# =============================================================================
def create_figure(gdf, manager):

    if manager != "TÜMÜ":
        gdf = gdf[gdf["Ticaret Müdürü"] == manager]

    # 🔹 Bölge kodları (renk için)
    region_codes = {r:i for i,r in enumerate(gdf["Bölge"].unique())}
    gdf["REGION_CODE"] = gdf["Bölge"].map(region_codes)

    fig = go.Figure()

    # CHOROPLETH – BÖLGE RENKLERİ
    fig.add_choropleth(
        geojson=json.loads(gdf.to_json()),
        locations=gdf.index,
        z=gdf["REGION_CODE"],
        colorscale="Set3",
        marker_line_color="black",
        marker_line_width=0.6,
        customdata=list(zip(gdf["Şehir"], gdf["Bölge"], gdf["Kutu Adet"])),
        hovertemplate="<b>%{customdata[0]}</b><br>Bölge: %{customdata[1]}<br>Kutu: %{customdata[2]:,}<extra></extra>",
        showscale=False
    )

    # BORDER
    lons, lats = [], []
    for geom in gdf.geometry.boundary:
        lo, la = lines_to_lonlat(geom)
        lons += lo; lats += la

    fig.add_scattergeo(
        lon=lons, lat=lats, mode="lines",
        line=dict(color="rgba(50,50,50,0.6)", width=0.7),
        hoverinfo="skip"
    )

    # 🔹 BÖLGE LABEL + TOPLAM ADET
    region_labels = (
        gdf.dissolve(by="Bölge", aggfunc={"Kutu Adet":"sum"})
        .reset_index()
    )
    centroids = region_labels.geometry.centroid

    fig.add_scattergeo(
        lon=centroids.x,
        lat=centroids.y,
        text=region_labels["Bölge"] + "<br>" + region_labels["Kutu Adet"].astype(int).astype(str),
        mode="text",
        textfont=dict(size=12, color="black"),
        hoverinfo="skip"
    )

    fig.update_layout(
        geo=dict(
            projection_type="mercator",
            center=dict(lat=39, lon=35),
            lonaxis_range=[25,45],
            lataxis_range=[35,43],
            visible=False
        ),
        height=750,
        margin=dict(l=0,r=0,t=40,b=0)
    )

    return fig

# =============================================================================
# APP
# =============================================================================
uploaded = st.sidebar.file_uploader("Excel Yükle", ["xlsx","xls"])
df = load_excel(uploaded)
geo = load_geo()
merged = prepare_data(df, geo)

manager = st.sidebar.selectbox(
    "Ticaret Müdürü",
    ["TÜMÜ"] + sorted(merged["Ticaret Müdürü"].unique())
)

st.plotly_chart(create_figure(merged, manager), use_container_width=True)
