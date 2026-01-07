import streamlit as st
import geopandas as gpd
import pandas as pd
import plotly.graph_objects as go
import json
import warnings

warnings.filterwarnings("ignore")

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
# BOZUK ŞEHİR DÜZELTMELERİ (KRİTİK)
# =============================================================================
fix_city_map = {
    "AGRI": "AGRI",
    "BARTÄ±N": "BARTIN",
    "BINGÃ¶L": "BINGOL",
    "DÃ¼ZCE": "DUZCE",
    "ELAZIG": "ELAZIG",
    "ESKISEHIR": "ESKISEHIR",
    "GÃ¼MÃ¼SHANE": "GUMUSHANE",
    "HAKKARI": "HAKKARI",
    "ISTANBUL": "ISTANBUL",
    "IZMIR": "IZMIR",
    "IÄ\x9fDIR": "IGDIR",
    "K. MARAS": "KAHRAMANMARAS",
    "KARABÃ¼K": "KARABUK",
    "KINKKALE": "KIRIKKALE",
    "KIRSEHIR": "KIRSEHIR",
    "KÃ¼TAHYA": "KUTAHYA",
    "MUGLA": "MUGLA",
    "MUS": "MUS",
    "NEVSEHIR": "NEVSEHIR",
    "NIGDE": "NIGDE",
    "SANLIURFA": "SANLIURFA",
    "SIRNAK": "SIRNAK",
    "TEKIRDAG": "TEKIRDAG",
    "USAK": "USAK",
    "ZINGULDAK": "ZONGULDAK",
    "Ã\x87ANAKKALE": "CANAKKALE",
    "Ã\x87ANKIRI": "CANKIRI",
    "Ã\x87ORUM": "CORUM"
}

# =============================================================================
# BÖLGE RENKLERİ
# =============================================================================
REGION_COLORS = {
    "MARMARA": "#1f77b4",              # Mavi
    "KARADENIZ": "#2ca02c",             # Yeşil
    "EGE": "#6baed6",
    "AKDENIZ": "#ff9f1c",
    "IC ANADOLU": "#8c564b",            # Kahverengi
    "DOGU ANADOLU": "#a0522d",
    "GUNEYDOGU ANADOLU": "#4b2e13",     # Koyu kahve
    "DIGER": "#cccccc"
}

# =============================================================================
# PAGE
# =============================================================================
st.set_page_config(page_title="Türkiye Satış Haritası", layout="wide")
st.title("🗺️ Türkiye Bölge & İl Bazlı Kutu Adetleri")

# =============================================================================
# LOAD DATA
# =============================================================================
@st.cache_data
def load_excel(file=None):
    if file:
        return pd.read_excel(file)
    return pd.read_excel("Data.xlsx")

@st.cache_resource
def load_geo():
    gdf = gpd.read_file("turkey.geojson")
    gdf["name"] = gdf["name"].apply(tr_upper)
    return gdf

# =============================================================================
# PREPARE DATA
# =============================================================================
def prepare_data(df, gdf):

    df = df.copy()
    gdf = gdf.copy()

    # Normalize
    df["Şehir"] = df["Şehir"].apply(tr_upper)
    df["Şehir"] = df["Şehir"].replace(fix_city_map)

    df["Bölge"] = df["Bölge"].apply(tr_upper)
    df["Ticaret Müdürü"] = df["Ticaret Müdürü"].apply(tr_upper)

    df["Kutu Adet"] = pd.to_numeric(df["Kutu Adet"], errors="coerce").fillna(0)

    # Merge
    merged = gdf.merge(
        df,
        left_on="name",
        right_on="Şehir",
        how="left"
    )

    merged["Kutu Adet"] = merged["Kutu Adet"].fillna(0)
    merged["Bölge"] = merged["Bölge"].fillna("DIGER")

    bolge_df = (
        merged.groupby("Bölge", as_index=False)["Kutu Adet"]
        .sum()
        .sort_values("Kutu Adet", ascending=False)
    )

    return merged, bolge_df

# =============================================================================
# FIGURE
# =============================================================================
def create_figure(gdf, manager):

    if manager != "TÜMÜ":
        gdf = gdf[gdf["Ticaret Müdürü"] == manager]

    fig = go.Figure()

    # İl bazlı harita
    fig.add_choropleth(
        geojson=json.loads(gdf.to_json()),
        locations=gdf.index,
        z=gdf["Kutu Adet"],
        colorscale="Greys",
        marker_line_color="black",
        marker_line_width=0.4,
        customdata=gdf[["name", "Bölge", "Kutu Adet"]],
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Bölge: %{customdata[1]}<br>"
            "Kutu Adet: %{customdata[2]:,}"
            "<extra></extra>"
        ),
        showscale=False
    )

    # Bölge alanları (renkli)
    region_df = gdf.dissolve(by="Bölge", aggfunc={"Kutu Adet": "sum"}).reset_index()
    region_df["color"] = region_df["Bölge"].map(REGION_COLORS).fillna("#cccccc")

    for _, r in region_df.iterrows():
        fig.add_choropleth(
            geojson=json.loads(region_df.to_json()),
            locations=[r["Bölge"]],
            z=[1],
            featureidkey="properties.Bölge",
            colorscale=[[0, r["color"]], [1, r["color"]]],
            showscale=False,
            marker_line_width=1,
            hovertemplate=f"<b>{r['Bölge']}</b><br>Toplam: {int(r['Kutu Adet']):,}<extra></extra>"
        )

    # Bölge label
    rp = region_df.to_crs(3857)
    rp["centroid"] = rp.geometry.centroid
    rp = rp.to_crs(4326)

    fig.add_scattergeo(
        lon=rp.centroid.x,
        lat=rp.centroid.y,
        mode="text",
        text=[f"<b>{r['Bölge']}</b><br>{int(r['Kutu Adet']):,}" for _, r in rp.iterrows()],
        textfont=dict(color="black", size=13),
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
        height=750,
        margin=dict(l=0, r=0, t=30, b=0)
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
