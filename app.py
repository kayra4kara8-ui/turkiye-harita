import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.graph_objects as go
from shapely.geometry import LineString, MultiLineString
import requests
import warnings

warnings.filterwarnings("ignore")

# --------------------------------------------------
# SAYFA AYAR
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
# TÜRKİYE HARİTASINI YÜKLE
# --------------------------------------------------
@st.cache_data
def load_turkey_map():
    """GitHub'dan direkt GeoJSON yükle"""
    url = "https://raw.githubusercontent.com/alpers/Turkey-Maps-GeoJSON/master/tr-cities-utf8.json"
    
    try:
        with st.spinner("🗺️ Türkiye haritası yükleniyor..."):
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # GeoJSON'ı GeoPandas ile oku
            import json
            geojson_data = json.loads(response.text)
            gdf = gpd.GeoDataFrame.from_features(geojson_data["features"])
            
            # Sütun isimlerini düzenle
            if 'properties' in gdf.columns:
                gdf = pd.concat([gdf.drop(['properties'], axis=1), 
                                gdf['properties'].apply(pd.Series)], axis=1)
            
            # Şehir ismi sütununu bul ve temizle
            name_cols = ['name', 'NAME', 'city', 'il']
            for col in name_cols:
                if col in gdf.columns:
                    gdf["name"] = gdf[col].str.upper().str.strip()
                    break
            
            return gdf
    
    except Exception as e:
        st.error(f"❌ Harita yüklenemedi: {str(e)}")
        st.info("""
        💡 Alternatif çözüm: 
        1. https://github.com/alpers/Turkey-Maps-GeoJSON adresinden
        2. tr-cities-utf8.json dosyasını indirin
        3. Aşağıdan yükleyin
        """)
        
        uploaded_map = st.file_uploader("🗺️ GeoJSON/Shapefile Yükle", type=["geojson", "json"])
        if uploaded_map:
            gdf = gpd.read_file(uploaded_map)
            if 'properties' in gdf.columns:
                gdf = pd.concat([gdf.drop(['properties'], axis=1), 
                                gdf['properties'].apply(pd.Series)], axis=1)
            
            name_cols = ['name', 'NAME', 'city', 'il']
            for col in name_cols:
                if col in gdf.columns:
                    gdf["name"] = gdf[col].str.upper().str.strip()
                    break
            return gdf
        else:
            st.stop()

turkey_map = load_turkey_map()
st.success(f"✅ Harita yüklendi ({len(turkey_map)} il)")

# --------------------------------------------------
# EXCEL YÜKLEME
# --------------------------------------------------
st.sidebar.header("📂 Veri Yükleme")
uploaded_file = st.sidebar.file_uploader(
    "Excel dosyasını yükleyin",
    type=["xlsx", "xls"]
)

if uploaded_file is None:
    st.info("👈 Lütfen sol taraftan Excel dosyasını yükleyin.")
    st.stop()

try:
    df = pd.read_excel(uploaded_file)
    required_cols = ["Şehir", "Bölge", "Kutu Adet", "Ticaret Müdürü"]
    missing = [c for c in required_cols if c not in df.columns]
    
    if missing:
        st.error(f"❌ Eksik sütunlar: {', '.join(missing)}")
        st.stop()
    
    df["Şehir"] = df["Şehir"].str.upper().str.strip()
    st.sidebar.success(f"✅ Veri yüklendi ({len(df)} kayıt)")

except Exception as e:
    st.error(f"❌ Excel hatası: {str(e)}")
    st.stop()

# --------------------------------------------------
# ŞEHİR ADI EŞLEŞTİRME
# --------------------------------------------------
fix_map = {
    "ISTANBUL": "İSTANBUL", "IZMIR": "İZMİR", "SANLIURFA": "ŞANLIURFA",
    "USAK": "UŞAK", "ELAZIG": "ELAZIĞ", "MUGLA": "MUĞLA",
    "KIRSEHIR": "KIRŞEHİR", "NEVSEHIR": "NEVŞEHİR", "NIGDE": "NİĞDE",
    "TEKIRDAG": "TEKİRDAĞ", "SIRNAK": "ŞIRNAK", "KIRIKKALE": "KIRIKKALE",
    "K. MARAS": "KAHRAMANMARAŞ", "KINKKALE": "KIRIKKALE"
}

turkey_map["CITY_CLEAN"] = turkey_map["name"].replace(fix_map).str.upper()

# --------------------------------------------------
# MERGE
# --------------------------------------------------
merged = turkey_map.merge(df, left_on="CITY_CLEAN", right_on="Şehir", how="left")
merged["Kutu Adet"] = merged["Kutu Adet"].fillna(0)

# Eşleşmeyen şehirler
unmatched = set(df["Şehir"]) - set(merged[merged["Kutu Adet"] > 0]["Şehir"])
if unmatched:
    with st.sidebar.expander("⚠️ Eşleşmeyen Şehirler"):
        for city in sorted(unmatched):
            st.write(f"- {city}")

# --------------------------------------------------
# BÖLGE TOPLAMLARI
# --------------------------------------------------
region_sum = merged.groupby("Bölge", as_index=False)["Kutu Adet"].sum()
region_map = (
    merged[["Bölge", "geometry"]]
    .dissolve(by="Bölge")
    .reset_index()
    .merge(region_sum, on="Bölge", how="left")
)

# --------------------------------------------------
# TİCARET MÜDÜRÜ SEÇİMİ
# --------------------------------------------------
managers = ["Tümü"] + sorted(df["Ticaret Müdürü"].dropna().unique())
selected = st.sidebar.selectbox("🎯 Ticaret Müdürü", managers)

if selected != "Tümü":
    merged_view = merged[merged["Ticaret Müdürü"] == selected].copy()
    region_view_sum = merged_view.groupby("Bölge", as_index=False)["Kutu Adet"].sum()
    region_view = (
        merged_view[["Bölge", "geometry"]]
        .dissolve(by="Bölge")
        .reset_index()
        .merge(region_view_sum, on="Bölge", how="left")
    )
else:
    merged_view = merged.copy()
    region_view = region_map.copy()

# --------------------------------------------------
# HARİTA ÇİZİMİ
# --------------------------------------------------
fig = go.Figure()

# Bölge renklendirme
for _, region in region_view.iterrows():
    if pd.isna(region["Bölge"]):
        continue
    
    geom = region["geometry"]
    if geom.geom_type == "Polygon":
        polys = [geom]
    else:
        polys = list(geom.geoms)
    
    for poly in polys:
        lons, lats = poly.exterior.xy
        fig.add_scattergeo(
            lon=list(lons),
            lat=list(lats),
            fill="toself",
            fillcolor=REGION_COLORS.get(region["Bölge"], "#CCCCCC"),
            line=dict(color="rgba(60,60,60,0.4)", width=1),
            hoverinfo="text",
            text=f"<b>{region['Bölge']}</b><br>Kutu Adet: {int(region['Kutu Adet']):,}",
            showlegend=False
        )

# Şehir sınırları
def lines_to_coords(geom):
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
    lo, la = lines_to_coords(geom)
    all_lons += lo
    all_lats += la

fig.add_scattergeo(
    lon=all_lons,
    lat=all_lats,
    mode="lines",
    line=dict(width=0.5, color="rgba(60,60,60,0.5)"),
    hoverinfo="skip",
    showlegend=False
)

# Şehir hover
pts = merged_view.to_crs(epsg=3857)
pts["centroid"] = pts.geometry.centroid
pts = pts.to_crs(merged_view.crs)

fig.add_scattergeo(
    lon=pts.centroid.x,
    lat=pts.centroid.y,
    mode="markers",
    marker=dict(size=5, color="rgba(0,0,0,0)"),
    hoverinfo="text",
    text=(
        "<b>" + pts["CITY_CLEAN"] + "</b><br>"
        "Bölge: " + pts["Bölge"].fillna("?") + "<br>"
        "Ticaret Müdürü: " + pts["Ticaret Müdürü"].fillna("Bilinmiyor") + "<br>"
        "Kutu Adet: " + pts["Kutu Adet"].astype(int).map(lambda x: f"{x:,}")
    ),
    showlegend=False
)

# Layout
fig.update_geos(
    fitbounds="locations",
    visible=False,
    projection_type="mercator"
)

fig.update_layout(
    margin=dict(l=0, r=0, t=40, b=0),
    height=700,
    showlegend=False
)

st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# İSTATİSTİKLER
# --------------------------------------------------
st.sidebar.header("📊 İstatistikler")

if selected != "Tümü":
    total = merged_view["Kutu Adet"].sum()
    st.sidebar.metric("Toplam Kutu", f"{int(total):,}")
    cities = len(merged_view[merged_view["Kutu Adet"] > 0])
    st.sidebar.metric("Şehir Sayısı", cities)
else:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📦 Bölge Bazında")
        for _, row in region_sum.sort_values("Kutu Adet", ascending=False).iterrows():
            if pd.notna(row["Bölge"]):
                st.metric(row["Bölge"], f"{int(row['Kutu Adet']):,}")
    
    with col2:
        st.subheader("👥 Ticaret Müdürü Bazında")
        mgr_stats = df.groupby("Ticaret Müdürü")["Kutu Adet"].sum().sort_values(ascending=False)
        for mgr, total in mgr_stats.items():
            st.metric(mgr, f"{int(total):,}")
