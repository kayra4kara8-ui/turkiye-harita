import streamlit as st
import geopandas as gpd
import pandas as pd
import plotly.graph_objects as go
import json
from shapely.geometry import LineString, MultiLineString
import warnings

warnings.filterwarnings("ignore")

# Sayfa ayarları
st.set_page_config(page_title="Türkiye Bölge Haritası", layout="wide")

st.title("🗺️ Türkiye - Bölge Bazlı Kutu Adetleri")

# Bölge renkleri
region_colors = {
    "KUZEY ANADOLU": "#2E8B57",
    "MARMARA": "#2F6FD6",
    "İÇ ANADOLU": "#8B6B4A",
    "BATI ANADOLU": "#2BB0A6",
    "GÜNEY DOĞU ANADOLU": "#A05A2C"
}

@st.cache_data
def load_data(uploaded_excel=None):
    """Veri ve harita dosyalarını yükle"""
    # Excel dosyasını yükle
    if uploaded_excel is not None:
        df = pd.read_excel(uploaded_excel)
    else:
        # Yerel dosyadan yükle (varsa)
        try:
            df = pd.read_excel("Data.xlsx")
        except FileNotFoundError:
            return None, None
    
    # GeoJSON'ı yükle
    try:
        turkey_map = gpd.read_file("turkey.geojson")
    except FileNotFoundError:
        st.error("❌ turkey.geojson dosyası bulunamadı! Lütfen GeoJSON dosyasını proje klasörüne ekleyin.")
        return None, None
    
    return df, turkey_map

@st.cache_data
def prepare_data(df, _turkey_map):
    """Veriyi hazırla ve birleştir"""
    
    # Şehir isimlerini büyük harfe çevir
    df["Şehir"] = df["Şehir"].str.upper()
    turkey_map["name"] = turkey_map["name"].str.upper()
    
    # Şehir ismi düzeltmeleri
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
        "KINKKALE": "KIRIKKALE",
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
        "ZINGULDAK": "ZONGULDAK",
        "CANAKKALE": "ÇANAKKALE",
        "CANKIRI": "ÇANKIRI",
        "CORUM": "ÇORUM"
    }
    
    turkey_map["CITY_CLEAN"] = turkey_map["name"].replace(fix_city_map).str.upper()
    
    # Şehir-bölge eşleştirmesi
    sehir_bolge = df[["Şehir", "Bölge"]].drop_duplicates()
    
    # Harita ile veriyi birleştir
    turkey_map = turkey_map.merge(
        sehir_bolge,
        left_on="CITY_CLEAN",
        right_on="Şehir",
        how="left"
    )
    
    # Şehir bazlı toplam verileri ekle
    merged_region = turkey_map.merge(
        df[['Şehir', 'Bölge', 'Ticaret Müdürü', 'Kutu Adet']].drop_duplicates(),
        left_on='CITY_CLEAN',
        right_on='Şehir',
        how='left',
        suffixes=('_map', '_df')
    )
    
    # Sütun temizliği
    if 'Bölge_map' in merged_region.columns:
        merged_region = merged_region.drop(columns=['Bölge_map'])
    merged_region = merged_region.rename(columns={'Bölge_df': 'Bölge'})
    
    merged_region['Kutu Adet'] = merged_region['Kutu Adet'].fillna(0)
    
    # Bölge bazlı toplam
    bolge_df = df.groupby("Bölge", as_index=False)["Kutu Adet"].sum()
    
    return merged_region, bolge_df

def lines_to_lonlat(geom):
    """Geometri sınırlarını lon/lat listelerine çevir"""
    lons, lats = [], []
    
    if isinstance(geom, LineString):
        xs, ys = geom.xy
        lons += list(xs) + [None]
        lats += list(ys) + [None]
    elif isinstance(geom, MultiLineString):
        for line in geom.geoms:
            xs, ys = line.xy
            lons += list(xs) + [None]
            lats += list(ys) + [None]
    
    return lons, lats

def create_map_block(df, region_colors):
    """Harita bloğu oluştur"""
    traces = []
    
    # Bölge bazlı toplam
    region_df = df.dissolve(by="Bölge", aggfunc="sum").reset_index()
    
    # GeoJSON oluştur
    geojson = json.loads(region_df.to_json())
    
    # Choropleth trace
    choropleth_trace = go.Choropleth(
        geojson=geojson,
        locations=region_df["Bölge"],
        featureidkey="properties.Bölge",
        z=[region_colors.get(b, "#E0E0E0") for b in region_df["Bölge"]],
        colorscale=[[0, region_colors.get(b, "#E0E0E0")] for b in region_df["Bölge"]],
        showscale=False,
        hovertemplate="<b>%{location}</b><br>Kutu Adet: %{customdata:,}<extra></extra>",
        customdata=region_df["Kutu Adet"]
    )
    traces.append(choropleth_trace)
    
    # Bölge etiketleri
    rp = region_df.to_crs(3857)
    rp["centroid"] = rp.geometry.centroid
    rp = rp.to_crs(region_df.crs)
    
    label_trace = go.Scattergeo(
        lon=rp.centroid.x,
        lat=rp.centroid.y,
        text=[f"<b>{r['Bölge']}</b><br>{int(r['Kutu Adet']):,}" for _, r in rp.iterrows()],
        mode="text",
        textfont=dict(size=13, color="black", family="Arial Black"),
        showlegend=False,
        hoverinfo="skip"
    )
    traces.append(label_trace)
    
    # Şehir hover noktaları
    cp = df.to_crs(3857)
    cp["centroid"] = cp.geometry.centroid
    cp = cp.to_crs(df.crs)
    
    hover_trace = go.Scattergeo(
        lon=cp.centroid.x,
        lat=cp.centroid.y,
        mode="markers",
        marker=dict(size=6, color="rgba(0,0,0,0)"),
        hovertemplate="<b>%{text}</b><extra></extra>",
        text=[f"{r['CITY_CLEAN']}<br>Bölge: {r['Bölge']}<br>Kutu Adet: {int(r['Kutu Adet']):,}" 
              for _, r in cp.iterrows()],
        showlegend=False
    )
    traces.append(hover_trace)
    
    return traces

def create_figure(merged_region, selected_manager):
    """Plotly figürünü oluştur"""
    fig = go.Figure()
    
    # Şehir sınırları (her zaman görünür)
    lons, lats = [], []
    for geom in merged_region.geometry.boundary:
        lo, la = lines_to_lonlat(geom)
        lons += lo
        lats += la
    
    fig.add_scattergeo(
        lon=lons,
        lat=lats,
        mode="lines",
        line=dict(color="rgba(90,90,90,0.6)", width=0.8),
        hoverinfo="skip",
        showlegend=False
    )
    
    # Seçili müdüre göre veriyi filtrele
    if selected_manager == "Tümü":
        df_filtered = merged_region
        title = "Türkiye — Bölge Bazlı Kutu Adetleri (Tümü)"
    else:
        df_filtered = merged_region[merged_region["Ticaret Müdürü"] == selected_manager]
        title = f"Türkiye — {selected_manager} | Bölge Bazlı Kutu Adetleri"
    
    # Harita bloğunu ekle
    traces = create_map_block(df_filtered, region_colors)
    for trace in traces:
        fig.add_trace(trace)
    
    # Layout ayarları
    fig.update_layout(
        title=title,
        geo=dict(
            scope='europe',
            center=dict(lat=39, lon=35),
            projection_scale=4.5,
            visible=False
        ),
        margin=dict(r=0, l=0, t=60, b=0),
        height=700
    )
    
    return fig

# Ana uygulama
try:
    # Sidebar - Dosya yükleme
    st.sidebar.header("📂 Dosya Yükleme")
    uploaded_file = st.sidebar.file_uploader(
        "Excel Dosyası Yükle (Data.xlsx)", 
        type=['xlsx', 'xls'],
        help="Şehir, Bölge, Ticaret Müdürü ve Kutu Adet sütunlarını içeren Excel dosyası"
    )
    
    # Veriyi yükle
    if uploaded_file is not None:
        df, turkey_map = load_data(uploaded_file)
    else:
        # Yerel dosyayı dene
        df, turkey_map = load_data()
        if df is None:
            st.warning("⚠️ Lütfen Excel dosyanızı yükleyin veya Data.xlsx dosyasını proje klasörüne ekleyin")
            st.info("""
            📋 Excel dosyanız şu sütunları içermelidir:
            - **Şehir**: Şehir adı
            - **Bölge**: Bölge adı  
            - **Ticaret Müdürü**: Müdür adı
            - **Kutu Adet**: Sayısal değer
            """)
            st.stop()
    
    if turkey_map is None:
        st.stop()
    
    merged_region, bolge_df = prepare_data(df, turkey_map)
    
    # Sidebar - Müdür seçimi
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filtreler")
    managers = ["Tümü"] + sorted(merged_region["Ticaret Müdürü"].dropna().unique().tolist())
    selected_manager = st.sidebar.selectbox("Ticaret Müdürü", managers)
    
    # Haritayı oluştur ve göster
    fig = create_figure(merged_region, selected_manager)
    st.plotly_chart(fig, use_container_width=True)
    
    # İstatistikler
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 İstatistikler")
    
    if selected_manager == "Tümü":
        total = merged_region["Kutu Adet"].sum()
        st.sidebar.metric("Toplam Kutu Adet", f"{int(total):,}")
    else:
        df_manager = merged_region[merged_region["Ticaret Müdürü"] == selected_manager]
        total = df_manager["Kutu Adet"].sum()
        st.sidebar.metric(f"{selected_manager} Toplam", f"{int(total):,}")
    
    # Bölge bazlı tablo
    st.subheader("📋 Bölge Bazlı Detaylar")
    
    if selected_manager == "Tümü":
        display_df = bolge_df.copy()
    else:
        df_manager = merged_region[merged_region["Ticaret Müdürü"] == selected_manager]
        display_df = df_manager.groupby("Bölge", as_index=False)["Kutu Adet"].sum()
    
    display_df = display_df.sort_values("Kutu Adet", ascending=False)
    display_df["Kutu Adet"] = display_df["Kutu Adet"].apply(lambda x: f"{int(x):,}")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)

except FileNotFoundError as e:
    st.error(f"""
    ❌ Dosya bulunamadı: {e}
    
    **Gerekli dosyalar:**
    - ✅ turkey.geojson (proje klasöründe olmalı)
    - ✅ Data.xlsx (sidebar'dan yüklenebilir veya proje klasöründe olabilir)
    """)
    st.info("""
    💡 **Nasıl hazırlanır?**
    
    1️⃣ **turkey.geojson oluşturmak için:**
    - GeoJSON oluşturma scriptini Colab'da çalıştırın
    - Veya indirme scriptini kullanın
    
    2️⃣ **Data.xlsx için:**
    - Sidebar'dan "Excel Dosyası Yükle" butonunu kullanın
    - Veya dosyayı proje klasörüne kopyalayın
    """)
except Exception as e:
    st.error(f"Hata oluştu: {str(e)}")
    st.exception(e)

