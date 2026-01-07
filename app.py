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
st.title("🗺️ Türkiye - İl & Bölge Bazlı Kutu Adetleri")

# =============================================================================
# TÜRKÇE KARAKTER NORMALİZASYONU
# =============================================================================
def tr_upper(text):
    if pd.isna(text):
        return text
    text = str(text).strip()
    return (
        text.replace("i", "İ")
            .replace("ı", "I")
            .upper()
            .replace("Ğ", "G")
            .replace("Ş", "S")
            .replace("Ü", "U")
            .replace("Ö", "O")
            .replace("Ç", "C")
    )

# =============================================================================
# CITY FIX MAP (ENCODING HATALARI)
# =============================================================================
FIX_CITY_MAP = {
    "AGRI": "AĞRI",
    "BARTÄ±N": "BARTIN",
    "BINGÃ¶L": "BİNGÖL",
    "DÃ¼ZCE": "DÜZCE",
    "ELAZIG": "ELAZIĞ",
    "ESKISEHIR": "ESKİŞEHİR",
    "GÃ¼MÃ¼SHANE": "GÜMÜŞHANE",
    "ISTANBUL": "İSTANBUL",
    "IZMIR": "İZMİR",
    "IÄ\x9fDIR": "IĞDIR",
    "KARABÃ¼K": "KARABÜK",
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
    "Ã\x87ORUM": "ÇORUM"
}

# =============================================================================
# DATA LOADING
# =============================================================================
@st.cache_data
def load_excel(uploaded_file=None):
    if uploaded_file is not None:
        return pd.read_excel(uploaded_file)
    return pd.read_excel("Data.xlsx")

@st.cache_resource
def load_turkey_map():
    gdf = gpd.read_file("turkey.geojson")
    gdf["name"] = gdf["name"].apply(tr_upper)
    gdf["name"] = gdf["name"].replace(FIX_CITY_MAP)
    return gdf

# =============================================================================
# DATA PREPARATION
# =============================================================================
@st.cache_data
def prepare_data(df, turkey_map):

    df = df.copy()
    gdf = turkey_map.copy()

    df["Şehir"] = df["Şehir"].apply(tr_upper).replace(FIX_CITY_MAP)
    df["Bölge"] = df["Bölge"].apply(tr_upper)
    df["Ticaret Müdürü"] = df["Ticaret Müdürü"].apply(tr_upper)
    df["Kutu Adet"] = pd.to_numeric(df["Kutu Adet"], errors="coerce").fillna(0)

    merged = gdf.merge(
        df,
        left_on="name",
        right_on="Şehir",
        how="left"
    )

    merged["Kutu Adet"] = merged["Kutu Adet"].fillna(0)
    merged["Bölge"] = merged["Bölge"].fillna("DİĞER")
    merged["Şehir"] = merged["name"]

    bolge_df = (
        merged.groupby("Bölge", as_index=False)["Kutu Adet"]
        .sum()
        .sort_values("Kutu Adet", ascending=False)
    )

    return merged, bolge_df

# =============================================================================
# FIGURE
# =============================================================================
def create_figure(gdf, selected_manager):

    if selected_manager != "TÜMÜ":
        gdf = gdf[gdf["Ticaret Müdürü"] == selected_manager]

    fig = go.Figure()

    # =======================
    # IL BAZLI CHOROPLETH
    # =======================
    fig.add_choropleth(
        geojson=json.loads(gdf.to_json()),
        locations=gdf.index,
        z=gdf["Kutu Adet"],
        colorscale="YlOrRd",
        marker_line_color="black",
        marker_line_width=0.6,
        showscale=True,
        hovertemplate=
            "<b>%{customdata[0]}</b><br>"
            "Bölge: %{customdata[1]}<br>"
            "Kutu Adet: %{customdata[2]:,}"
            "<extra></extra>",
        customdata=gdf[["Şehir", "Bölge", "Kutu Adet"]]
    )

    # =======================
    # IL SINIRLARI
    # =======================
    lons, lats = [], []
    for geom in gdf.geometry.boundary:
        if isinstance(geom, LineString):
            xs, ys = geom.xy
            lons += list(xs) + [None]
            lats += list(ys) + [None]
        elif isinstance(geom, MultiLineString):
            for line in geom.geoms:
                xs, ys = line.xy
                lons += list(xs) + [None]
                lats += list(ys) + [None]

    fig.add_scattergeo(
        lon=lons,
        lat=lats,
        mode="lines",
        line=dict(color="rgba(90,90,90,0.6)", width=0.7),
        hoverinfo="skip",
        showlegend=False
    )

    fig.update_layout(
        geo=dict(
            scope="europe",
            center=dict(lat=39, lon=35),
            projection_scale=4.7,
            visible=False
        ),
        height=720,
        margin=dict(l=0, r=0, t=40, b=0)
    )

    return fig

# =============================================================================
# APP FLOW
# =============================================================================
st.sidebar.header("📂 Excel Yükle")
uploaded_file = st.sidebar.file_uploader("Excel Dosyası", ["xlsx", "xls"])

df = load_excel(uploaded_file)
turkey_map = load_turkey_map()

merged, bolge_df = prepare_data(df, turkey_map)

st.sidebar.header("🔍 Filtre")
managers = ["TÜMÜ"] + sorted(merged["Ticaret Müdürü"].dropna().unique())
selected_manager = st.sidebar.selectbox("Ticaret Müdürü", managers)

fig = create_figure(merged, selected_manager)
st.plotly_chart(fig, use_container_width=True)

st.subheader("📊 Bölge Bazlı Toplamlar")
st.dataframe(bolge_df, use_container_width=True, hide_index=True)
