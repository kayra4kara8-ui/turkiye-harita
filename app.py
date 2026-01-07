import streamlit as st
import pandas as pd
import plotly.express as px
import json

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
# TÜRKÇE NORMALİZASYON
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
# GEOJSON (DÜZ JSON)
# --------------------------------------------------
with open("data/tr.geojson", encoding="utf-8") as f:
    geojson_data = json.load(f)

# GeoJSON'dan il adlarını çek
features = geojson_data["features"]

city_records = []
for feat in features:
    props = feat["properties"]
    name = props.get("name") or props.get("NAME") or props.get("province")
    city_records.append({
        "CITY_CLEAN": normalize_city(name),
        "geometry": feat["geometry"]
    })

geo_df = pd.DataFrame(city_records)

# --------------------------------------------------
# MERGE
# --------------------------------------------------
merged = geo_df.merge(df, on="CITY_CLEAN", how="left")
merged["Kutu Adet"] = merged["Kutu Adet"].fillna(0)

# --------------------------------------------------
# CHOROPLETH
# --------------------------------------------------
fig = px.choropleth(
    merged,
    geojson=geojson_data,
    locations=merged.index,
    color="Kutu Adet",
    hover_name="Şehir",
    hover_data={
        "Bölge": True,
        "Kutu Adet": ":,"
    },
    color_continuous_scale="Blues"
)

fig.update_geos(fitbounds="locations", visible=False)
fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))

st.plotly_chart(fig, use_container_width=True)
