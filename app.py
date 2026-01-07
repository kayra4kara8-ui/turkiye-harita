import streamlit as st
import geopandas as gpd
import pandas as pd
import plotly.graph_objects as go
import json
import warnings

warnings.filterwarnings("ignore")

# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(page_title="Türkiye Bölge Haritası", layout="wide")
st.title("🗺️ Türkiye - Bölge & Şehir Bazlı Kutu Adetleri")

# =============================================================================
# LOAD DATA
# =============================================================================
@st.cache_data
def load_excel(uploaded_file=None):
    if uploaded_file is not None:
        return pd.read_excel(uploaded_file)
    return pd.read_excel("Data.xlsx")


@st.cache_resource
def load_map():
    gdf = gpd.read_file("turkey.geojson")
    gdf["name"] = gdf["name"].str.upper().str.strip()
    return gdf


# =============================================================================
# PREPARE DATA
# =============================================================================
@st.cache_data
def prepare_data(df, turkey_map):

    df = df.copy()
    gdf = turkey_map.copy()

    # Normalize
    df["Şehir"] = df["Şehir"].str.upper().str.strip()
    df["Bölge"] = df["Bölge"].str.upper().str.strip()
    df["Ticaret Müdürü"] = df["Ticaret Müdürü"].str.upper().str.strip()
    df["Kutu Adet"] = pd.to_numeric(df["Kutu Adet"], errors="coerce").fillna(0)

    # Şehir bazlı aggregation
    city_df = (
        df.groupby(["Şehir", "Bölge", "Ticaret Müdürü"], as_index=False)["Kutu Adet"]
        .sum()
    )

    # Merge
    merged = gdf.merge(
        city_df,
        left_on="name",
        right_on="Şehir",
        how="left"
    )

    merged["Kutu Adet"] = merged["Kutu Adet"].fillna(0)
    merged["Bölge"] = merged["Bölge"].fillna("BİLİNMİYOR")

    return merged


# =============================================================================
# COLORS
# =============================================================================
REGION_COLORS = {
    "MARMARA": "#1f77b4",
    "KARADENİZ": "#2ca02c",
    "İÇ ANADOLU": "#8B5A2B",
    "GÜNEYDOĞU ANADOLU": "#5C4033",
    "EGE": "#17becf",
    "AKDENİZ": "#98df8a",
    "DOĞU ANADOLU": "#7f7f7f",
    "BİLİNMİYOR": "#d3d3d3",
}

# =============================================================================
# FIGURE
# =============================================================================
def create_figure(gdf, selected_manager):

    fig = go.Figure()

    if selected_manager != "TÜMÜ":
        gdf = gdf[gdf["Ticaret Müdürü"] == selected_manager]

    # ---------------- CITY LAYER ----------------
    geojson = json.loads(gdf.to_json())

    fig.add_choropleth(
        geojson=geojson,
        locations=gdf.index,
        z=gdf["Kutu Adet"],
        colorscale="YlOrRd",
        marker_line_color="black",
        marker_line_width=0.5,
        hovertemplate=
        "<b>%{customdata[0]}</b><br>"
        "Bölge: %{customdata[1]}<br>"
        "Kutu Adet: %{z:,}<extra></extra>",
        customdata=gdf[["name", "Bölge"]].values,
        showscale=False
    )

    # ---------------- REGION LABELS ----------------
    region_df = (
        gdf.groupby("Bölge", as_index=False)["Kutu Adet"]
        .sum()
    )

    region_geo = gdf.dissolve(by="Bölge", aggfunc="sum").reset_index()
    region_geo = region_geo.to_crs(3857)
    region_geo["centroid"] = region_geo.geometry.centroid
    region_geo = region_geo.to_crs(4326)

    fig.add_scattergeo(
        lon=region_geo.centroid.x,
        lat=region_geo.centroid.y,
        mode="text",
        text=[
            f"<b>{row['Bölge']}</b><br>{int(row['Kutu Adet']):,}"
            for _, row in region_geo.iterrows()
        ],
        textfont=dict(color="black", size=12),
        hoverinfo="skip",
        showlegend=False
    )

    # ---------------- LAYOUT ----------------
    fig.update_layout(
        geo=dict(
            scope="europe",
            center=dict(lat=39, lon=35),
            projection_scale=4.8,
            showland=False,
            showcountries=False,
            showlakes=False,
            bgcolor="rgba(0,0,0,0)"
        ),
        height=750,
        margin=dict(l=0, r=0, t=40, b=0)
    )

    return fig


# =============================================================================
# APP
# =============================================================================
st.sidebar.header("📂 Excel Yükle")
uploaded_file = st.sidebar.file_uploader("Excel Dosyası", type=["xlsx", "xls"])

df = load_excel(uploaded_file)
turkey_map = load_map()
merged = prepare_data(df, turkey_map)

st.sidebar.header("🔍 Filtre")
managers = ["TÜMÜ"] + sorted(merged["Ticaret Müdürü"].dropna().unique().tolist())
selected_manager = st.sidebar.selectbox("Ticaret Müdürü", managers)

fig = create_figure(merged, selected_manager)
st.plotly_chart(fig, use_container_width=True)

st.subheader("📋 Bölge Bazlı Toplamlar")
st.dataframe(
    merged.groupby("Bölge", as_index=False)["Kutu Adet"].sum(),
    use_container_width=True,
    hide_index=True
)
