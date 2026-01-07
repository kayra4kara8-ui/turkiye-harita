import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import warnings

warnings.filterwarnings("ignore")

# --------------------------------------------------
# SAYFA
# --------------------------------------------------
st.set_page_config(page_title="Türkiye İl Bazlı Harita", layout="wide")
st.title("🇹🇷 Türkiye – İl & Bölge Bazlı Kutu Adetleri")

# --------------------------------------------------
# EXCEL
# --------------------------------------------------
uploaded_file = st.file_uploader("📂 Excel yükle", type=["xlsx"])
if uploaded_file is None:
    st.stop()

df = pd.read_excel(uploaded_file)

# --------------------------------------------------
# TÜRKÇE NORMALİZASYON (KRİTİK)
# --------------------------------------------------
def normalize_city(x):
    if pd.isna(x):
        return x
    return (
        str(x).upper()
        .replace("İ", "I")
        .replace("Ş", "S")
        .replace("Ğ", "G")
        .replace("Ü", "U")
        .replace("Ö", "O")
        .replace("Ç", "C")
    )

df["CITY_CLEAN"] = df["Şehir"].apply(normalize_city)

# --------------------------------------------------
# HARİTA (GEOJSON)
# --------------------------------------------------
@st.cache_data
def load_map():
    gdf = gpd.read_file("data/tr_provinces.geojson")
    gdf.columns = gdf.columns.str.lower()

    # il adı hangi kolonda olursa olsun yakala
    for col in ["name", "province", "il", "il_adi"]:
        if col in gdf.columns:
            gdf["CITY_RAW"] = gdf[col]
            break
    else:
        st.error("GeoJSON içinde il adı bulunamadı")
        st.stop()

    gdf["CITY_CLEAN"] = gdf["CITY_RAW"].apply(normalize_city)
    return gdf

turkey_map = load_map()

# --------------------------------------------------
# MERGE
# --------------------------------------------------
merged = turkey_map.merge(
    df,
    on="CITY_CLEAN",
    how="left"
)

merged["Kutu Adet"] = merged["Kutu Adet"].fillna(0)

# --------------------------------------------------
# HARİTA (İL BAZLI)
# --------------------------------------------------
fig = px.choropleth(
    merged,
    geojson=merged.__geo_interface__,
    locations=merged.index,
    color="Kutu Adet",
    hover_name="Şehir",
    hover_data=["Bölge", "Kutu Adet"],
    color_continuous_scale="Blues"
)

fig.update_geos(fitbounds="locations", visible=False)
fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))

st.plotly_chart(fig, use_container_width=True)
