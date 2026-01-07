import streamlit as st
import geopandas as gpd
import pandas as pd
import plotly.express as px
import unicodedata

# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(page_title="Türkiye Satış Haritası", layout="wide")
st.title("🗺️ Türkiye – Şehir & Bölge Bazlı Kutu Adetleri")

# =============================================================================
# TEXT NORMALIZATION (KRİTİK)
# =============================================================================
def normalize_tr(text):
    if pd.isna(text):
        return None
    text = str(text).upper().strip()
    replacements = {
        "İ": "I", "İ": "I", "Ş": "S", "Ğ": "G",
        "Ü": "U", "Ö": "O", "Ç": "C"
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text

# =============================================================================
# LOAD DATA
# =============================================================================
@st.cache_data
def load_excel():
    df = pd.read_excel("Data.xlsx")
    df["SEHIR_NORM"] = df["Şehir"].apply(normalize_tr)
    df["BOLGE"] = df["Bölge"].str.upper()
    df["Kutu Adet"] = pd.to_numeric(df["Kutu Adet"], errors="coerce").fillna(0)
    return df

@st.cache_resource
def load_map():
    gdf = gpd.read_file("turkey.geojson")
    gdf["SEHIR_NORM"] = gdf["name"].apply(normalize_tr)
    return gdf

df = load_excel()
gdf = load_map()

# =============================================================================
# MERGE
# =============================================================================
merged = gdf.merge(
    df,
    on="SEHIR_NORM",
    how="left"
)

merged["Kutu Adet"] = merged["Kutu Adet"].fillna(0)
merged["BOLGE"] = merged["BOLGE"].fillna("DİĞER")

# =============================================================================
# REGION COLORS
# =============================================================================
region_colors = {
    "MARMARA": "#1f77b4",
    "KARADENIZ": "#2ca02c",
    "IC ANADOLU": "#8c564b",
    "GUNEYDOGU ANADOLU": "#4b3621",
    "DOGU ANADOLU": "#7f7f7f",
    "EGE": "#98df8a",
    "AKDENIZ": "#17becf",
    "DIGER": "#cccccc"
}

merged["RENK"] = merged["BOLGE"].map(region_colors).fillna("#cccccc")

# =============================================================================
# MAP
# =============================================================================
fig = px.choropleth(
    merged,
    geojson=merged.geometry,
    locations=merged.index,
    color="BOLGE",
    color_discrete_map=region_colors,
    hover_name="Şehir",
    hover_data={
        "BOLGE": True,
        "Kutu Adet": True
    }
)

fig.update_geos(
    fitbounds="locations",
    visible=False
)

fig.update_layout(
    height=700,
    margin=dict(l=0, r=0, t=30, b=0)
)

st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# TABLE
# =============================================================================
st.subheader("📊 Bölge Bazlı Toplamlar")
st.dataframe(
    df.groupby("Bölge", as_index=False)["Kutu Adet"].sum(),
    use_container_width=True
)
