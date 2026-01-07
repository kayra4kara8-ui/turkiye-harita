import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
from shapely.geometry import LineString, MultiLineString
import warnings
import os

warnings.filterwarnings("ignore")

# --------------------------------------------------
# SAYFA AYAR
# --------------------------------------------------
st.set_page_config(
    page_title="Türkiye Bölge Bazlı Kutu Adetleri",
    layout="wide"
)

st.title("🇹🇷 Türkiye – Bölge Bazlı Kutu Adetleri")

# --------------------------------------------------
# RENKLER
# --------------------------------------------------
REGION_COLORS = {
    "KUZEY ANADOLU": "#2E8B57",
    "MARMARA": "#2F6FD6",
    "İÇ ANADOLU": "#8B6B4A",
    "BATI ANADOLU": "#2BB0A6",
    "GÜNEY DOĞU ANADOLU": "#A05A2C"
}

# --------------------------------------------------
# EXCEL YÜKLEME
# --------------------------------------------------
uploaded_file = st.file_uploader(
    "📂 Excel dosyasını yükleyin (Data.xlsx)",
    type=["xlsx"]
)

if uploaded_file is None:
    st.warning("Excel dosyası yüklenmeden harita çalışmaz.")
    st.stop()

df = pd.read_excel(uploaded_file)

df["Şehir"] = df["Şehir"].str.upper()

# --------------------------------------------------
# HARİTA OKU (SHP AUTO-DETECT)
# --------------------------------------------------
@st.cache_data
def load_map():
    shp_dir = "data/tr_shp"
    shp_files = [f for f in os.listdir(shp_dir) if f.lower().endswith(".shp")]

    if not shp_files:
        st.error("Shapefile (.shp) bulunamadı!")
        st.stop()

    shp_path = os.path.join(shp_dir, shp_files[0])

    gdf = gpd.read_file(shp_path)
    gdf.columns = gdf.columns.str.lower()
    gdf["name"] = gdf["name"].str.upper()

    return gdf

turkey_map = load_map()

# --------------------------------------------------
# ŞEHİR ADI TEMİZLEME
# --------------------------------------------------
fix_city_map = {
    "ISTANBUL": "İSTANBUL",
    "IZMIR": "İZMİR",
    "SANLIURFA": "ŞANLIURFA",
    "USAK": "UŞAK",
    "ELAZIG": "ELAZIĞ",
    "MUGLA": "MUĞLA",
    "KIRSEHIR": "KIRŞEHİR",
    "NEVSEHIR": "NEVŞEHİR",
    "NIGDE": "NİĞDE",
    "TEKIRDAG": "TEKİRDAĞ"
}

turkey_map["CITY_CLEAN"] = (
    turkey_map["name"]
    .replace(fix_city_map)
    .str.upper()
)

# --------------------------------------------------
# MERGE
# --------------------------------------------------
merged = turkey_map.merge(
    df,
    left_on="CITY_CLEAN",
    right_on="Şehir",
    how="left"
)

merged["Kutu Adet"] = merged["Kutu Adet"].fillna(0)

# --------------------------------------------------
# BÖLGE TOPLAMLARI
# --------------------------------------------------
region_sum = (
    merged.groupby("Bölge", as_index=False)["Kutu Adet"]
    .sum()
)

region_map = (
    merged[["Bölge", "geometry"]]
    .dissolve(by="Bölge")
    .reset_index()
    .merge(region_sum, on="Bölge", how="left")
)

# --------------------------------------------------
# DROPDOWN
# --------------------------------------------------
managers = ["Tümü"] + sorted(df["Ticaret Müdürü"].dropna().unique())
selected_manager = st.selectbox("Ticaret Müdürü", managers)

if selected_manager != "Tümü":
    merged_view = merged[merged["Ticaret Müdürü"] == selected_manager]
else:
    merged_view = merged

# --------------------------------------------------
# CHOROPLETH
# --------------------------------------------------
fig = px.choropleth(
    region_map,
    geojson=region_map.__geo_interface__,
    locations="Bölge",
    featureidkey="properties.Bölge",
    color="Bölge",
    color_discrete_map=REGION_COLORS,
    hover_name="Bölge",
    hover_data={"Kutu Adet": ":,"}
)

fig.update_geos(fitbounds="locations", visible=False)
fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))

# --------------------------------------------------
# ŞEHİR SINIRLARI
# --------------------------------------------------
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

all_lons, all_lats = [], []
for geom in merged_view.geometry.boundary:
    lo, la = lines_to_lonlat(geom)
    all_lons += lo
    all_lats += la

fig.add_scattergeo(
    lon=all_lons,
    lat=all_lats,
    mode="lines",
    line=dict(width=0.6, color="rgba(60,60,60,0.6)"),
    hoverinfo="skip",
    showlegend=False
)

# --------------------------------------------------
# ŞEHİR HOVER
# --------------------------------------------------
pts = merged_view.to_crs(3857)
pts["centroid"] = pts.geometry.centroid
pts = pts.to_crs(merged_view.crs)

fig.add_scattergeo(
    lon=pts.centroid.x,
    lat=pts.centroid.y,
    mode="markers",
    marker=dict(size=6, color="rgba(0,0,0,0)"),
    hoverinfo="text",
    text=(
        "<b>" + pts["CITY_CLEAN"] + "</b><br>"
        "Bölge: " + pts["Bölge"] + "<br>"
        "Ticaret Müdürü: " + pts["Ticaret Müdürü"].fillna("Bilinmiyor") + "<br>"
        "Kutu Adet: " + pts["Kutu Adet"].astype(int).map(lambda x: f"{x:,}")
    ),
    showlegend=False
)

st.plotly_chart(fig, use_container_width=True)



