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
with open("data/tr_provinces.geojson", encoding="utf-8") as f:
    geojson_data = json.load(f)

# GeoJSON'dan il adlarını çek
features = geojson_data["features"]

city_records = []
for feat in features:
    props = feat["properties"]
    name = props.get("name") or props.get("NAME") or props.ge
