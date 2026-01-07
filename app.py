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
    "AGRI": "AĞRI", "BARTÄ±N": "BARTIN", "BINGÃ¶L": "BİNGÖL",
    "DÃ¼ZCE": "DÜZCE", "ELAZIG": "ELAZIĞ", "ESKISEHIR": "ESKİŞEHİR",
    "GÃ¼MÃ¼SHANE": "GÜMÜŞHANE", "HAKKARI": "HAKKARİ",
    "ISTANBUL": "İSTANBUL", "IZMIR": "İZMİR", "IÄ\x9fDIR": "IĞDIR",
    "KARABÃ¼K": "KARABÜK", "KINKKALE": "KIRIKKALE",
    "KIRSEHIR": "KIRŞEHİR", "KÃ¼TAHYA": "KÜTAHYA",
    "MUGLA": "MUĞLA", "MUS": "MUŞ", "NEVSEHIR": "NEVŞEHİR",
    "NIGDE": "NİĞDE", "SANLIURFA": "ŞANLIURFA",
    "SIRNAK": "ŞIRNAK", "TEKIRDAG": "TEKİRDAĞ",
    "USAK": "UŞAK", "ZINGULDAK": "ZONGULDAK",
    "Ã\x87ANAKKALE": "ÇANAKKALE", "Ã\x87ANKIRI": "ÇANKIRI",
    "Ã\x87ORUM": "ÇORUM", "K. MARAS": "KAHRAMANMARAŞ"
}

# =============================================================================
# BÖLGE RENKLERİ
# =============================================================================
REGION_COLORS = {
    "MARMARA": "#1f77b4",
    "EGE": "#2ca02c",
    "AKDENIZ": "#ff7f0e",
    "IC ANADOLU": "#8c564b",
    "KARADENIZ": "#17becf",
    "DOGU ANADOLU": "#d62728",
    "GUNEYDOGU ANADOLU": "#9467bd",
    "DİĞER": "#cccccc"
}

# =============================================================================
# NORMALIZE
# =============================================================================
def normalize_city(name):
    if pd.isna(name):
        return None
    name = str(name).upper().strip()
    for k, v in {"İ":"I","Ğ":"G","Ü":"U","Ş":"S","Ö":"O","Ç":"C","Â":"A"}.items():
        name = name.replace(k, v)
    return name

# =============================================================================
# LOAD DATA
# =============================================================================
@st.cache_data
def load_excel(file=None):
    return pd.read_excel(file) if file else pd.read_excel("Data.xlsx")

@st.cache_resource
def load_geo():
    gdf = gpd.read_file("turkey.geojson")
    gdf["Şehir"] = gdf["name"].str.upper().replace(FIX_CITY_MAP)
    gdf["CITY_KEY"] = gdf["Şehir"].apply(normalize_city)
    return gdf

# =============================================================================
# PREP DATA
# =============================================================================
def prepare_data(df, gdf):
    df = df.copy()
    df["Şehir"] = df["Şehir"].str.upper().replace(FIX_CITY_MAP)
    df["CITY_KEY"] = df["Şehir"].apply(normalize_city)
    df["Bölge"] = df["Bölge"].str.upper()
    df["Ticaret Müdürü"] = df["Ticaret Müdürü"].str.upper()
    df["Kutu Adet"] = pd.to_numeric(df["Kutu Adet"], errors="coerce").fillna(0)

    merged = gdf.merge(df, on="CITY_KEY", how="left")
    merged["Kutu Adet"] = merged["Kutu Adet"].fillna(0)
    merged["Bölge"] = merged["Bölge"].fillna("DİĞER")

    bolge_df = merged.groupby("Bölge", as_index=False)["Kutu Adet"].sum()
    return merged, bolge_df

# =============================================================================
# GEOMETRY
# =============================================================================
def lines_to_lonlat(geom):
    lons, lats = [], []
    if geom is None:
        return lons, lats
    if isinstance(geom, (LineString, MultiLineString)):
        for g in getattr(geom, "geoms", [geom]):
            xs, ys = g.xy
            lons += list(xs) + [None]
            lats += list(ys) + [None]
    return lons, lats

# =============================================================================
# FIGURE
# =============================================================================
def create_figure(gdf, manager):
    if manager != "TÜMÜ":
        gdf = gdf[gdf["Ticaret Müdürü"] == manager]

    gdf["color"] = gdf["Bölge"].map(REGION_COLORS).fillna("#cccccc")

    fig = go.Figure(go.Choropleth(
        geojson=json.loads(gdf.to_json()),
        locations=gdf.index,
        z=gdf.index,
        marker=dict(line=dict(color="black", width=0.4)),
        colorscale=[[0,c] for c in gdf["color"]],
        customdata=gdf[["Şehir","Bölge","Kutu Adet"]],
        hovertemplate="<b>%{customdata[0]}</b><br>Bölge: %{customdata[1]}<br>Kutu: %{customdata[2]:,}<extra></extra>",
        showscale=False
    ))

    # Bölge label
    region_geo = gdf.dissolve(by="Bölge", aggfunc={"Kutu Adet":"sum"}).to_crs(3857)
    region_geo["centroid"] = region_geo.geometry.centroid
    region_geo = region_geo.to_crs(4326)

    fig.add_scattergeo(
        lon=region_geo.centroid.x,
        lat=region_geo.centroid.y,
        text=[f"<b>{b}</b><br>{int(k):,}" for b,k in zip(region_geo.index,region_geo["Kutu Adet"])],
        mode="text",
        textfont=dict(size=13,color="black"),
        hoverinfo="skip"
    )

    fig.update_layout(
        geo=dict(
            projection_type="mercator",
            center=dict(lat=39,lon=35),
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

merged, bolge_df = prepare_data(df, geo)

manager = st.sidebar.selectbox(
    "Ticaret Müdürü",
    ["TÜMÜ"] + sorted(merged["Ticaret Müdürü"].dropna().unique())
)

st.plotly_chart(create_figure(merged, manager), use_container_width=True)

st.subheader("📊 Bölge Toplamları")
st.dataframe(bolge_df, use_container_width=True, hide_index=True)
