import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import warnings

warnings.filterwarnings("ignore")

# --------------------------------------------------
# SAYFA AYARI
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
    "📂 Excel dosyasını yükleyin (xlsx)",
    type=["xlsx"]
)

if uploaded_file is None:
    st.warning("Excel dosyası yüklenmeden harita çalışmaz.")
    st.stop()

df = pd.read_excel(uploaded_file)
df["Şehir"] = df["Şehir"].str.upper()

# --------------------------------------------------
# HARİTA OKU (GEOJSON)
# --------------------------------------------------
@st.cache_data
def load_map():
    gdf = gpd.read_file("data/tr.geojson")
    gdf.columns = gdf.columns.str.lower()

    if "name" not in gdf.columns:
        st.error("GeoJSON içinde 'name' kolonu bulunamadı")
        st.stop()

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
# BÖLGE TOPLAMI
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

st.plotly_chart(fig, use_container_width=True)
