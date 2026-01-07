import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
from shapely.geometry import LineString, MultiLineString
import warnings
import os

warnings.filterwarnings("ignore")

# --------------------------------------------------
# SAYFA AYAR
# --------------------------------------------------
st.set_page_config(
    page_title="Türkiye Bölge Bazlı Kutu Adetleri",
    layout="wide",
    initial_sidebar_state="collapsed"
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
st.sidebar.header("📂 Dosya Yükleme")
uploaded_file = st.sidebar.file_uploader(
    "Excel dosyasını yükleyin (Data.xlsx)",
    type=["xlsx", "xls"]
)

if uploaded_file is None:
    st.info("👈 Lütfen sol taraftan Excel dosyasını yükleyin.")
    st.stop()

try:
    df = pd.read_excel(uploaded_file)
    
    # Gerekli sütunları kontrol et
    required_columns = ["Şehir", "Bölge", "Kutu Adet", "Ticaret Müdürü"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        st.error(f"❌ Excel dosyasında şu sütunlar eksik: {', '.join(missing_columns)}")
        st.stop()
    
    df["Şehir"] = df["Şehir"].str.upper().str.strip()
    
except Exception as e:
    st.error(f"❌ Excel dosyası okunurken hata oluştu: {str(e)}")
    st.stop()

# --------------------------------------------------
# HARİTA OKU (SHP)
# --------------------------------------------------
@st.cache_data
def load_map():
    try:
        shp_dir = "data/tr_shp"
        
        if not os.path.exists(shp_dir):
            st.error(f"❌ Shapefile klasörü bulunamadı: {shp_dir}")
            st.stop()
        
        shp_files = [f for f in os.listdir(shp_dir) if f.lower().endswith(".shp")]
        
        if not shp_files:
            st.error("❌ Shapefile (.shp) bulunamadı!")
            st.stop()
        
        shp_path = os.path.join(shp_dir, shp_files[0])
        gdf = gpd.read_file(shp_path)
        
        # Sütun isimlerini küçük harfe çevir
        gdf.columns = gdf.columns.str.lower()
        
        # 'name' sütununun varlığını kontrol et
        if 'name' not in gdf.columns:
            st.error(f"❌ Shapefile'da 'name' sütunu bulunamadı. Mevcut sütunlar: {', '.join(gdf.columns)}")
            st.stop()
        
        gdf["name"] = gdf["name"].str.upper().str.strip()
        
        return gdf
    
    except Exception as e:
        st.error(f"❌ Harita yüklenirken hata oluştu: {str(e)}")
        st.stop()

turkey_map = load_map()

# --------------------------------------------------
# ŞEHİR ADI TEMİZLEME
# --------------------------------------------------
fix_city_map = {
    "AGRI": "AĞRI",
    "BARTIN": "BARTIN",
    "BINGOL": "BİNGÖL",
    "DUZCE": "DÜZCE",
    "ELAZIG": "ELAZIĞ",
    "ESKISEHIR": "ESKİŞEHİR",
    "GUMUSHANE": "GÜMÜŞHANE",
    "HAKKARI": "HAKKARİ",
    "ISTANBUL": "İSTANBUL",
    "IZMIR": "İZMİR",
    "IGDIR": "IĞDIR",
    "K. MARAS": "KAHRAMANMARAŞ",
    "KARABUK": "KARABÜK",
    "KIRIKKALE": "KIRIKKALE",
    "KIRSEHIR": "KIRŞEHİR",
    "KUTAHYA": "KÜTAHYA",
    "MUGLA": "MUĞLA",
    "MUS": "MUŞ",
    "NEVSEHIR": "NEVŞEHİR",
    "NIGDE": "NİĞDE",
    "SANLIURFA": "ŞANLIURFA",
    "SIRNAK": "ŞIRNAK",
    "TEKIRDAG": "TEKİRDAĞ",
    "USAK": "UŞAK",
    "ZONGULDAK": "ZONGULDAK",
    "CANAKKALE": "ÇANAKKALE",
    "CANKIRI": "ÇANKIRI",
    "CORUM": "ÇORUM"
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

# Eşleşmeyen şehirleri kontrol et
unmatched_cities = set(df["Şehir"]) - set(merged[merged["Kutu Adet"] > 0]["Şehir"])
if unmatched_cities:
    with st.sidebar.expander("⚠️ Eşleşmeyen Şehirler"):
        st.warning(f"Aşağıdaki şehirler haritada bulunamadı:")
        for city in sorted(unmatched_cities):
            st.write(f"- {city}")

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
selected_manager = st.sidebar.selectbox("🎯 Ticaret Müdürü Seçin", managers)

if selected_manager != "Tümü":
    merged_view = merged[merged["Ticaret Müdürü"] == selected_manager].copy()
    region_view = merged_view.groupby("Bölge", as_index=False)["Kutu Adet"].sum()
    region_map_view = (
        merged_view[["Bölge", "geometry"]]
        .dissolve(by="Bölge")
        .reset_index()
        .merge(region_view, on="Bölge", how="left")
    )
else:
    merged_view = merged.copy()
    region_map_view = region_map.copy()

# --------------------------------------------------
# CHOROPLETH
# --------------------------------------------------
fig = go.Figure()

# Bölge haritası
choropleth = px.choropleth(
    region_map_view,
    geojson=region_map_view.__geo_interface__,
    locations="Bölge",
    featureidkey="properties.Bölge",
    color="Bölge",
    color_discrete_map=REGION_COLORS,
    hover_name="Bölge",
    hover_data={"Kutu Adet": ":,"}
)

fig.add_trace(choropleth.data[0])

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
pts = merged_view.to_crs(epsg=3857)
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
        "Bölge: " + pts["Bölge"].fillna("Bilinmiyor") + "<br>"
        "Ticaret Müdürü: " + pts["Ticaret Müdürü"].fillna("Bilinmiyor") + "<br>"
        "Kutu Adet: " + pts["Kutu Adet"].astype(int).map(lambda x: f"{x:,}")
    ),
    showlegend=False
)

# --------------------------------------------------
# BÖLGE LABEL
# --------------------------------------------------
region_proj = region_map_view.to_crs(epsg=3857)
region_proj["centroid"] = region_proj.geometry.centroid
region_proj = region_proj.to_crs(region_map_view.crs)

fig.add_scattergeo(
    lon=region_proj.centroid.x,
    lat=region_proj.centroid.y,
    text=region_proj.apply(
        lambda r: f"<b>{r['Bölge']}</b><br>{int(r['Kutu Adet']):,}",
        axis=1
    ),
    mode="text",
    textfont=dict(size=13, color="black", family="Arial Black"),
    showlegend=False
)

# Layout
fig.update_geos(fitbounds="locations", visible=False)
fig.update_layout(
    margin=dict(l=0, r=0, t=40, b=0),
    showlegend=False,
    height=700
)

st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# İSTATİSTİKLER
# --------------------------------------------------
st.sidebar.header("📊 İstatistikler")

if selected_manager != "Tümü":
    total_boxes = merged_view["Kutu Adet"].sum()
    st.sidebar.metric("Toplam Kutu", f"{int(total_boxes):,}")
    
    city_count = len(merged_view[merged_view["Kutu Adet"] > 0])
    st.sidebar.metric("Şehir Sayısı", city_count)
else:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📦 Bölge Bazında Toplam")
        region_stats = region_sum.sort_values("Kutu Adet", ascending=False)
        for _, row in region_stats.iterrows():
            st.metric(row["Bölge"], f"{int(row['Kutu Adet']):,}")
    
    with col2:
        st.subheader("👥 Ticaret Müdürü Bazında Toplam")
        manager_stats = df.groupby("Ticaret Müdürü")["Kutu Adet"].sum().sort_values(ascending=False)
        for manager, total in manager_stats.items():
            st.metric(manager, f"{int(total):,}")
