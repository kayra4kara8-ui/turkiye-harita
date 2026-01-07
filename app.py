import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.graph_objects as go

# -------------------------------------------------
# SAYFA AYARLARI
# -------------------------------------------------
st.set_page_config(
    page_title="Türkiye Satış Haritası",
    layout="wide"
)

st.title("📍 Türkiye Bölge Bazlı Satış Haritası")

# -------------------------------------------------
# YARDIMCI FONKSİYONLAR
# -------------------------------------------------
@st.cache_data
def load_geojson():
    gdf = gpd.read_file("turkiye_il.geojson")
    gdf["name"] = gdf["name"].str.upper()
    return gdf

@st.cache_data
def load_excel(file):
    df = pd.read_excel(file)
    df.columns = df.columns.str.upper()
    df["IL"] = df["IL"].str.upper()
    df["BOLGE"] = df["BOLGE"].str.upper()
    df["TICARET_MUDURU"] = df["TICARET_MUDURU"].str.upper()
    return df

def prepare_data(df, geo):
    merged = geo.merge(
        df,
        left_on="name",
        right_on="IL",
        how="left"
    )

    merged["KUTU_ADET"] = merged["KUTU_ADET"].fillna(0)
    return merged

def create_map(gdf):
    fig = go.Figure()

    fig.add_trace(
        go.Choropleth(
            geojson=gdf.__geo_interface__,
            locations=gdf.index,
            z=gdf["KUTU_ADET"],
            colorscale="YlOrRd",
            marker_line_width=0.5,
            marker_line_color="white",
            colorbar_title="Kutu Adet",
            hovertemplate=
                "<b>%{customdata[0]}</b><br>" +
                "Bölge: %{customdata[1]}<br>" +
                "Kutu: %{z:,.0f}<extra></extra>",
            customdata=gdf[["name", "BOLGE"]]
        )
    )

    fig.update_geos(
        fitbounds="locations",
        visible=False
    )

    fig.update_layout(
        height=650,
        margin=dict(l=0, r=0, t=0, b=0)
    )

    return fig

# -------------------------------------------------
# SIDEBAR
# -------------------------------------------------
st.sidebar.header("📂 Dosya Yükleme")

file = st.sidebar.file_uploader(
    "Excel Dosyası",
    type=["xlsx", "xls"]
)

if not file:
    st.warning("Lütfen Excel dosyası yükleyin")
    st.stop()

df = load_excel(file)
geo = load_geojson()

st.sidebar.header("🎯 Filtre")

mudur_list = ["TÜMÜ"] + sorted(df["TICARET_MUDURU"].unique())
selected_mudur = st.sidebar.selectbox(
    "Ticaret Müdürü",
    mudur_list
)

# -------------------------------------------------
# FİLTRELEME
# -------------------------------------------------
if selected_mudur != "TÜMÜ":
    df = df[df["TICARET_MUDURU"] == selected_mudur]

merged = prepare_data(df, geo)

# -------------------------------------------------
# HARİTA
# -------------------------------------------------
st.subheader("🗺️ Türkiye Haritası")

fig = create_map(merged)
st.plotly_chart(fig, use_container_width=True)

# -------------------------------------------------
# TABLO
# -------------------------------------------------
st.subheader("📊 Bölge Bazlı Detaylar")

bolge_df = (
    df.groupby("BOLGE", as_index=False)["KUTU_ADET"]
    .sum()
    .sort_values("KUTU_ADET", ascending=False)
)

st.dataframe(
    bolge_df,
    use_container_width=True
)
