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
st.title("🗺️ Türkiye – Bölge & İl Bazlı Performans Analizi")

# =============================================================================
# BÖLGE RENKLERİ (COĞRAFİ & MODERN)
# =============================================================================
REGION_COLORS = {
    "MARMARA": "#0EA5E9",              # Sky Blue - Deniz ve boğazlar
    "BATI ANADOLU": "#14B8A6",         # Turkuaz-yeşil arası
    "EGE": "#FCD34D",                  # BAL SARI (Batı Anadolu ile aynı)
    "İÇ ANADOLU": "#F59E0B",           # Amber - Kuru bozkır
    "GÜNEY DOĞU ANADOLU": "#E07A5F",   # Terracotta 
    "KUZEY ANADOLU": "#059669",        # Emerald - Yemyeşil ormanlar
    "KARADENİZ": "#059669",            # Emerald (Kuzey Anadolu ile aynı)
    "AKDENİZ": "#8B5CF6",              # Violet - Akdeniz
    "DOĞU ANADOLU": "#7C3AED",         # Purple - Yüksek dağlar
    "DİĞER": "#64748B"                 # Slate Gray
}

# =============================================================================
# ŞEHİR EŞLEŞTİRME (MASTER)
# =============================================================================
FIX_CITY_MAP = {
    "AGRI": "AĞRI",
    "BARTÄ±N": "BARTIN",
    "BINGÃ¶L": "BİNGÖL",
    "DÃ¼ZCE": "DÜZCE",
    "ELAZIG": "ELAZIĞ",
    "ESKISEHIR": "ESKİŞEHİR",
    "GÃ¼MÃ¼SHANE": "GÜMÜŞHANE",
    "HAKKARI": "HAKKARİ",
    "ISTANBUL": "İSTANBUL",
    "IZMIR": "İZMİR",
    "IÄ\x9fDIR": "IĞDIR",
    "KARABÃ¼K": "KARABÜK",
    "KINKKALE": "KIRIKKALE",
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
    "Ã\x87ORUM": "ÇORUM",
    "K. MARAS": "KAHRAMANMARAŞ"
}

# =============================================================================
# NORMALIZATION
# =============================================================================
def normalize_city(name):
    if pd.isna(name):
        return None

    name = str(name).upper().strip()

    tr_map = {
        "İ": "I", "Ğ": "G", "Ü": "U",
        "Ş": "S", "Ö": "O",
        "Ç": "C", "Â": "A"
    }

    for k, v in tr_map.items():
        name = name.replace(k, v)

    return name

# =============================================================================
# DATA LOAD
# =============================================================================
@st.cache_data
def load_excel(file=None):
    if file is not None:
        return pd.read_excel(file)
    # Eğer dosya yüklenmemişse boş DataFrame döndür
    return pd.DataFrame(columns=["Şehir", "Bölge", "Ticaret Müdürü", "Kutu Adet", "Toplam Adet"])

@st.cache_resource
def load_geo():
    gdf = gpd.read_file("turkey.geojson")
    gdf["raw_name"] = gdf["name"].str.upper()
    gdf["fixed_name"] = gdf["raw_name"].replace(FIX_CITY_MAP)
    gdf["CITY_KEY"] = gdf["fixed_name"].apply(normalize_city)
    return gdf

# =============================================================================
# DATA PREP
# =============================================================================
def prepare_data(df, gdf):

    df = df.copy()
    gdf = gdf.copy()

    df["Şehir_fix"] = df["Şehir"].str.upper().replace(FIX_CITY_MAP)
    df["CITY_KEY"] = df["Şehir_fix"].apply(normalize_city)

    df["Bölge"] = df["Bölge"].str.upper()
    df["Ticaret Müdürü"] = df["Ticaret Müdürü"].str.upper()
    
    # PF Kutu Adet (bizim satışlarımız)
    df["PF Kutu"] = pd.to_numeric(df["Kutu Adet"], errors="coerce").fillna(0)
    
    # Toplam Adet kolonunu farklı isimlerde ara
    toplam_col = None
    possible_names = ["Toplam Adet", "TOPLAM ADET", "Toplam", "TOPLAM", "Total", "Market Total"]
    
    for col_name in possible_names:
        if col_name in df.columns:
            toplam_col = col_name
            break
    
    if toplam_col:
        df["Toplam Kutu"] = pd.to_numeric(df[toplam_col], errors="coerce").fillna(0)
    else:
        # Eğer Toplam Adet kolonu yoksa, PF Kutu'nun 3 katı olarak varsayalım (örnek)
        df["Toplam Kutu"] = df["PF Kutu"] * 3
        st.sidebar.warning("⚠️ 'Toplam Adet' kolonu bulunamadı, varsayılan değerler kullanılıyor.")

    # Toplamları hesapla
    pf_toplam_kutu = df["PF Kutu"].sum()
    toplam_kutu = df["Toplam Kutu"].sum()

    merged = gdf.merge(df, on="CITY_KEY", how="left")

    # GARANTİ KOLONLAR
    merged["Şehir"] = merged["fixed_name"]
    merged["PF Kutu"] = merged["PF Kutu"].fillna(0)
    merged["Toplam Kutu"] = merged["Toplam Kutu"].fillna(0)
    merged["Bölge"] = merged["Bölge"].fillna("DİĞER")
    merged["Ticaret Müdürü"] = merged["Ticaret Müdürü"].fillna("YOK")

    # Şehir bazında yüzde hesapla
    merged["PF Pay %"] = (merged["PF Kutu"] / pf_toplam_kutu * 100).round(2) if pf_toplam_kutu > 0 else 0
    merged["Pazar Payı %"] = (merged["PF Kutu"] / merged["Toplam Kutu"] * 100).round(2)
    merged["Pazar Payı %"] = merged["Pazar Payı %"].replace([float('inf'), -float('inf')], 0).fillna(0)

    # Bölge bazlı toplam ve yüzde hesapla
    bolge_df = (
        merged.groupby("Bölge", as_index=False)
        .agg({"PF Kutu": "sum", "Toplam Kutu": "sum"})
        .sort_values("PF Kutu", ascending=False)
    )
    
    bolge_df["PF Pay %"] = (bolge_df["PF Kutu"] / pf_toplam_kutu * 100).round(2) if pf_toplam_kutu > 0 else 0
    bolge_df["Pazar Payı %"] = (bolge_df["PF Kutu"] / bolge_df["Toplam Kutu"] * 100).round(2)
    bolge_df["Pazar Payı %"] = bolge_df["Pazar Payı %"].replace([float('inf'), -float('inf')], 0).fillna(0)

    return merged, bolge_df, pf_toplam_kutu, toplam_kutu

# =============================================================================
# GEOMETRY HELPERS
# =============================================================================
def lines_to_lonlat(geom):
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

def get_region_center(gdf_region):
    """Bölgenin merkez koordinatlarını hesapla"""
    centroid = gdf_region.geometry.unary_union.centroid
    return centroid.x, centroid.y

# =============================================================================
# FIGURE
# =============================================================================
def create_figure(gdf, manager, view_mode, pf_toplam_kutu):

    gdf = gdf.copy()

    if manager != "TÜMÜ":
        gdf = gdf[gdf["Ticaret Müdürü"] == manager]

    fig = go.Figure()

    # Her bölge için ayrı trace
    for region in gdf["Bölge"].unique():
        region_gdf = gdf[gdf["Bölge"] == region]
        color = REGION_COLORS.get(region, "#CCCCCC")
        
        fig.add_choropleth(
            geojson=json.loads(region_gdf.to_json()),
            locations=region_gdf.index,
            z=[1] * len(region_gdf),  # Sabit değer, renk için
            colorscale=[[0, color], [1, color]],
            marker_line_color="white",
            marker_line_width=1.5,
            showscale=False,
            customdata=list(
                zip(
                    region_gdf["Şehir"],
                    region_gdf["Bölge"],
                    region_gdf["PF Kutu"]
                )
            ),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Bölge: %{customdata[1]}<br>"
                "PF Kutu: %{customdata[2]:,.0f}"
                "<extra></extra>"
            ),
            name=region
        )

    # Sınır çizgileri
    lons, lats = [], []
    for geom in gdf.geometry.boundary:
        lo, la = lines_to_lonlat(geom)
        lons += lo
        lats += la

    fig.add_scattergeo(
        lon=lons,
        lat=lats,
        mode="lines",
        line=dict(color="rgba(255,255,255,0.8)", width=1),
        hoverinfo="skip",
        showlegend=False
    )

    # Etiket görünümü seçimine göre
    if view_mode == "Bölge Görünümü":
        # Bölge etiketleri - YÜZDE İLE
        label_lons, label_lats, label_texts = [], [], []
        
        for region in gdf["Bölge"].unique():
            region_gdf = gdf[gdf["Bölge"] == region]
            total = region_gdf["PF Kutu"].sum()
            
            if total > 0:  # Sadece veri olan bölgeleri göster
                percent = (total / pf_toplam_kutu * 100) if pf_toplam_kutu > 0 else 0
                lon, lat = get_region_center(region_gdf)
                label_lons.append(lon)
                label_lats.append(lat)
                label_texts.append(f"<b>{region}</b><br>{total:,.0f}<br>%{percent:.1f}")

        fig.add_scattergeo(
            lon=label_lons,
            lat=label_lats,
            mode="text",
            text=label_texts,
            textfont=dict(size=11, color="black", family="Arial Black"),
            hoverinfo="skip",
            showlegend=False
        )
    
    else:  # Şehir Görünümü - YÜZDE İLE
        # Şehir etiketleri
        city_lons, city_lats, city_texts = [], [], []
        
        for idx, row in gdf.iterrows():
            if row["PF Kutu"] > 0:
                percent = (row["PF Kutu"] / pf_toplam_kutu * 100) if pf_toplam_kutu > 0 else 0
                centroid = row.geometry.centroid
                city_lons.append(centroid.x)
                city_lats.append(centroid.y)
                city_texts.append(f"<b>{row['Şehir']}</b><br>{row['PF Kutu']:,.0f}<br>%{percent:.1f}")
        
        fig.add_scattergeo(
            lon=city_lons,
            lat=city_lats,
            mode="text",
            text=city_texts,
            textfont=dict(size=9, color="black", family="Arial"),
            hoverinfo="skip",
            showlegend=False
        )

    fig.update_layout(
        geo=dict(
            projection=dict(type="mercator"),
            center=dict(lat=39, lon=35),
            lonaxis=dict(range=[25, 45]),
            lataxis=dict(range=[35, 43]),
            visible=False,
            bgcolor="rgba(240,240,240,0.3)"
        ),
        height=750,
        margin=dict(l=0, r=0, t=40, b=0),
        paper_bgcolor="white"
    )

    return fig

# =============================================================================
# APP FLOW
# =============================================================================
st.sidebar.header("📂 Excel Dosyaları Yükle")

# Çoklu dosya yükleme
uploaded_files = st.sidebar.file_uploader(
    "Excel Dosyalarını Seçin (Birden fazla seçebilirsiniz)", 
    ["xlsx", "xls"],
    accept_multiple_files=True
)

df = None
geo = load_geo()

if not uploaded_files:
    st.warning("⚠️ Lütfen sol taraftan bir veya daha fazla Excel dosyası yükleyin!")
    st.info("📋 Excel dosyası şu kolonları içermelidir: **Şehir**, **Bölge**, **Ticaret Müdürü**, **Kutu Adet**, **Toplam Adet**")
    st.stop()

# Birden fazla dosya varsa seçim ekle
if len(uploaded_files) > 1:
    file_names = [f.name for f in uploaded_files]
    selected_file_name = st.sidebar.selectbox("📊 Analiz Edilecek Dosyayı Seçin", file_names)
    selected_file = next(f for f in uploaded_files if f.name == selected_file_name)
    df = load_excel(selected_file)
    st.sidebar.success(f"✅ Seçili: {selected_file_name}")
else:
    df = load_excel(uploaded_files[0])
    st.sidebar.success(f"✅ Yüklendi: {uploaded_files[0].name}")

merged, bolge_df, pf_toplam_kutu, toplam_kutu = prepare_data(df, geo)

st.sidebar.header("🔍 Filtre")

# Görünüm modu
view_mode = st.sidebar.radio(
    "Görünüm Modu",
    ["Bölge Görünümü", "Şehir Görünümü"],
    index=0
)

# Ticaret Müdürü filtresi (haritayı etkiler)
managers = ["TÜMÜ"] + sorted(merged["Ticaret Müdürü"].unique())
selected_manager = st.sidebar.selectbox("Ticaret Müdürü", managers)

st.sidebar.markdown("---")
st.sidebar.header("🔍 Gelişmiş Filtreler")

# Bölge filtresi
bolge_list = ["TÜMÜ"] + sorted([b for b in merged["Bölge"].unique() if b != "DİĞER"])
selected_bolge = st.sidebar.selectbox("Bölge Seçin", bolge_list)

# Yatırım stratejisi filtresi
strateji_list = ["Tümü", "🚀 Agresif", "⚡ Hızlandırılmış", "🛡️ Koruma", "👁️ İzleme"]
selected_strateji = st.sidebar.selectbox("Yatırım Stratejisi", strateji_list)

# Renk legend'ı
st.sidebar.header("🎨 Bölge Renkleri")
for region, color in REGION_COLORS.items():
    if region in merged["Bölge"].values:
        st.sidebar.markdown(f"<span style='color:{color}'>⬤</span> {region}", unsafe_allow_html=True)

# FİLTRELEME MANTIĞI (Haritadan ÖNCE)
# Seçilen müdüre göre veriyi filtrele
if selected_manager != "TÜMÜ":
    filtered_data = merged[merged["Ticaret Müdürü"] == selected_manager]
else:
    filtered_data = merged.copy()

# Bölge filtresini uygula
if selected_bolge != "TÜMÜ":
    filtered_data = filtered_data[filtered_data["Bölge"] == selected_bolge]

# Haritayı filtered_data ile çiz
fig = create_figure(filtered_data, selected_manager, view_mode, pf_toplam_kutu)
st.plotly_chart(fig, use_container_width=True)

filtered_pf = filtered_data["PF Kutu"].sum()
filtered_toplam = filtered_data["Toplam Kutu"].sum()
filtered_aktif_sehir = (filtered_data["PF Kutu"] > 0).sum()

# Genel İstatistikler
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📦 PF Toplam Kutu", f"{filtered_pf:,.0f}")
with col2:
    st.metric("🏪 Toplam Kutu", f"{filtered_toplam:,.0f}")
with col3:
    genel_pazar_payi = (filtered_pf / filtered_toplam * 100) if filtered_toplam > 0 else 0
    st.metric("📊 Genel Pazar Payı", f"%{genel_pazar_payi:.1f}")
with col4:
    st.metric("🏙️ Aktif Şehir", f"{filtered_aktif_sehir}")

# Bölge ve şehir tablolarını hazırla (filtered_data kullan)
display_merged = filtered_data
display_bolge = (
    display_merged.groupby("Bölge", as_index=False)
    .agg({"PF Kutu": "sum", "Toplam Kutu": "sum"})
    .sort_values("PF Kutu", ascending=False)
)
display_bolge["PF Pay %"] = (display_bolge["PF Kutu"] / filtered_pf * 100).round(2) if filtered_pf > 0 else 0
display_bolge["Pazar Payı %"] = (display_bolge["PF Kutu"] / display_bolge["Toplam Kutu"] * 100).round(2)
display_bolge["Pazar Payı %"] = display_bolge["Pazar Payı %"].replace([float('inf'), -float('inf')], 0).fillna(0)

# Yatırım Stratejisi Hesaplama
def calculate_investment_strategy(df):
    """
    Quantile bazlı yatırım stratejisi belirleme
    - Agresif: Yüksek PF Kutu + Düşük Pazar Payı (büyüme potansiyeli yüksek)
    - Hızlandırılmış: Orta PF Kutu + Orta Pazar Payı (momentum var)
    - Koruma: Yüksek PF Kutu + Yüksek Pazar Payı (mevcut pozisyonu koru)
    - İzleme: Düşük PF Kutu + Düşük/Yüksek Pazar Payı (düşük öncelik)
    """
    df = df.copy()
    df = df[df["PF Kutu"] > 0]  # Sadece aktif şehirler
    
    if len(df) == 0:
        return df
    
    # PF Kutu segmentasyonu
    try:
        df["PF Segment"] = pd.qcut(df["PF Kutu"], q=4, labels=["Çok Düşük", "Düşük", "Orta", "Yüksek"], duplicates='drop')
    except:
        df["PF Segment"] = "Orta"
    
    # Toplam Kutu segmentasyonu
    try:
        df["Toplam Segment"] = pd.qcut(df["Toplam Kutu"], q=4, labels=["Çok Düşük", "Düşük", "Orta", "Yüksek"], duplicates='drop')
    except:
        df["Toplam Segment"] = "Orta"
    
    # Pazar payı segmentasyonu
    try:
        df["Pazar_Quantile"] = pd.qcut(df["Pazar Payı %"], q=3, labels=["Düşük", "Orta", "Yüksek"], duplicates='drop')
    except:
        df["Pazar_Quantile"] = "Orta"
    
    # Strateji belirleme kuralları (PF Segment ve Pazar Payı bazlı)
    def assign_strategy(row):
        pf_seg = str(row["PF Segment"])
        pazar_q = str(row["Pazar_Quantile"])
        
        # Agresif: Yüksek/Orta hacim + Düşük pazar payı = Büyüme potansiyeli
        if pf_seg in ["Yüksek", "Orta"] and pazar_q == "Düşük":
            return "🚀 Agresif"
        # Hızlandırılmış: Orta-yüksek hacim + Orta pazar payı
        elif pf_seg in ["Orta", "Yüksek"] and pazar_q == "Orta":
            return "⚡ Hızlandırılmış"
        # Koruma: Yüksek hacim + Yüksek pazar payı = Lider pozisyon
        elif pf_seg == "Yüksek" and pazar_q == "Yüksek":
            return "🛡️ Koruma"
        # İzleme: Düşük öncelikli
        else:
            return "👁️ İzleme"
    
    df["Yatırım Stratejisi"] = df.apply(assign_strategy, axis=1)
    
    return df

# Yatırım stratejisi ile şehir analizi
investment_df = calculate_investment_strategy(display_merged)

# Strateji filtresini uygula
investment_df_original = investment_df.copy()  # Grafikler için orijinali sakla
if selected_strateji != "Tümü" and len(investment_df) > 0:
    investment_df = investment_df[investment_df["Yatırım Stratejisi"] == selected_strateji]

st.subheader("📊 Bölge Bazlı Performans")
bolge_display = display_bolge[display_bolge["PF Kutu"] > 0].copy()
bolge_display = bolge_display[["Bölge", "PF Kutu", "Toplam Kutu", "PF Pay %", "Pazar Payı %"]]

# Sayıları formatlayarak string'e çevir
bolge_display["PF Kutu Formatli"] = bolge_display["PF Kutu"].apply(lambda x: f"{x:,.0f}")
bolge_display["Toplam Kutu Formatli"] = bolge_display["Toplam Kutu"].apply(lambda x: f"{x:,.0f}")

# Gösterilecek kolonları seç
display_cols = bolge_display[["Bölge", "PF Kutu Formatli", "Toplam Kutu Formatli", "PF Pay %", "Pazar Payı %"]].copy()
display_cols.columns = ["Bölge", "PF Kutu", "Toplam Kutu", "PF Pay %", "Pazar Payı %"]

st.dataframe(
    display_cols, 
    use_container_width=True, 
    hide_index=True
)

st.subheader("🎯 Yatırım Stratejisi Analizi")
if len(investment_df) > 0:
    # Strateji dağılımı
    strategy_counts = investment_df["Yatırım Stratejisi"].value_counts()
    col_a, col_b, col_c, col_d = st.columns(4)
    
    with col_a:
        agresif_count = strategy_counts.get("🚀 Agresif", 0)
        st.metric("🚀 Agresif", f"{agresif_count} şehir")
    with col_b:
        hizlandirilmis_count = strategy_counts.get("⚡ Hızlandırılmış", 0)
        st.metric("⚡ Hızlandırılmış", f"{hizlandirilmis_count} şehir")
    with col_c:
        koruma_count = strategy_counts.get("🛡️ Koruma", 0)
        st.metric("🛡️ Koruma", f"{koruma_count} şehir")
    with col_d:
        izleme_count = strategy_counts.get("👁️ İzleme", 0)
        st.metric("👁️ İzleme", f"{izleme_count} şehir")
    
    st.caption("""
    **Strateji Açıklamaları:**
    - 🚀 **Agresif**: Yüksek hacim + Düşük pazar payı → Büyüme potansiyeli yüksek, agresif yatırım gerekli
    - ⚡ **Hızlandırılmış**: Orta-yüksek hacim + Orta pazar payı → Momentum var, hızlandırılmış yatırım
    - 🛡️ **Koruma**: Yüksek hacim + Yüksek pazar payı → Lider pozisyon, mevcut payı koru
    - 👁️ **İzleme**: Düşük öncelikli bölgeler
    """)

st.subheader("🏙️ Şehir Bazlı Detay Analiz")
# Şehir bazında tabloyu hazırla
if len(investment_df) > 0:
    city_df = investment_df[["Şehir", "Bölge", "PF Kutu", "PF Segment", "Toplam Kutu", "Toplam Segment", "PF Pay %", "Pazar Payı %", "Yatırım Stratejisi", "Ticaret Müdürü"]].copy()
else:
    city_df = display_merged[display_merged["PF Kutu"] > 0][["Şehir", "Bölge", "PF Kutu", "Toplam Kutu", "PF Pay %", "Pazar Payı %", "Ticaret Müdürü"]].copy()
    city_df["PF Segment"] = "Orta"
    city_df["Toplam Segment"] = "Orta"
    city_df["Yatırım Stratejisi"] = "👁️ İzleme"

city_df = city_df.sort_values("PF Kutu", ascending=False).reset_index(drop=True)

# Sayıları formatlayarak string'e çevir
city_df["PF Kutu Formatli"] = city_df["PF Kutu"].apply(lambda x: f"{x:,.0f}")
city_df["Toplam Kutu Formatli"] = city_df["Toplam Kutu"].apply(lambda x: f"{x:,.0f}")

# Index'i 1'den başlat
city_df.index = city_df.index + 1

# Gösterilecek kolonları yeniden düzenle
if len(investment_df) > 0:
    display_city = city_df[["Şehir", "Bölge", "PF Kutu Formatli", "PF Segment", "Toplam Kutu Formatli", "Toplam Segment", "PF Pay %", "Pazar Payı %", "Yatırım Stratejisi", "Ticaret Müdürü"]].copy()
    display_city.columns = ["Şehir", "Bölge", "PF Kutu", "PF Segment", "Toplam Kutu", "Toplam Segment", "PF Pay %", "Pazar Payı %", "Yatırım Stratejisi", "Ticaret Müdürü"]
else:
    display_city = city_df[["Şehir", "Bölge", "PF Kutu Formatli", "Toplam Kutu Formatli", "PF Pay %", "Pazar Payı %", "Yatırım Stratejisi", "Ticaret Müdürü"]].copy()
    display_city.columns = ["Şehir", "Bölge", "PF Kutu", "Toplam Kutu", "PF Pay %", "Pazar Payı %", "Yatırım Stratejisi", "Ticaret Müdürü"]

st.caption("🏆 Şehirler PF Kutu performansına göre sıralanmıştır | Segmentler veriyi 4 dilime böler (Çok Düşük, Düşük, Orta, Yüksek)")
st.dataframe(
    display_city,
    use_container_width=True,
    hide_index=False
)

# =============================================================================
# GÖRSELLEŞTİRMELER
# =============================================================================
import plotly.express as px

st.markdown("---")
st.subheader("📊 Görsel Analizler")

if len(investment_df_original) > 0:
    col_viz1, col_viz2 = st.columns(2)
    
    with col_viz1:
        st.markdown("#### 🏆 Top 10 Şehirler (PF Kutu)")
        top10 = investment_df_original.nlargest(10, "PF Kutu")[["Şehir", "PF Kutu"]]
        fig_bar = px.bar(
            top10, 
            x="PF Kutu", 
            y="Şehir",
            orientation='h',
            color="PF Kutu",
            color_continuous_scale="Blues"
        )
        fig_bar.update_layout(height=400, showlegend=False, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)
    
    with col_viz2:
        st.markdown("#### 🎯 Yatırım Stratejisi Dağılımı")
        strateji_counts = investment_df_original["Yatırım Stratejisi"].value_counts().reset_index()
        strateji_counts.columns = ["Strateji", "Şehir Sayısı"]
        fig_pie = px.pie(
            strateji_counts,
            values="Şehir Sayısı",
            names="Strateji",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_pie.update_layout(height=400)
        st.plotly_chart(fig_pie, use_container_width=True)
    
    # Bölge bazlı performans grafiği
    st.markdown("#### 📍 Bölge Bazlı PF Kutu Dağılımı")
    bolge_viz = display_bolge[display_bolge["PF Kutu"] > 0].copy()
    
    # Her bölgeye özel renk ata
    bolge_viz["Renk"] = bolge_viz["Bölge"].map(REGION_COLORS)
    
    fig_bolge = px.bar(
        bolge_viz,
        x="Bölge",
        y="PF Kutu",
        color="Bölge",
        color_discrete_map=REGION_COLORS,
        text="PF Kutu"
    )
    fig_bolge.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
    fig_bolge.update_layout(height=400, xaxis_tickangle=-45, showlegend=False)
    st.plotly_chart(fig_bolge, use_container_width=True)

# =============================================================================
# EXPORT ÖZELLİKLERİ
# =============================================================================
st.markdown("---")
st.subheader("📥 Raporları İndir")

col_exp1, col_exp2 = st.columns(2)

with col_exp1:
    if len(investment_df) > 0:
        # Yatırım Stratejisi Raporu Excel Export
        export_df = investment_df[["Şehir", "Bölge", "PF Kutu", "Toplam Kutu", "PF Pay %", "Pazar Payı %", "Yatırım Stratejisi", "PF Segment", "Toplam Segment", "Ticaret Müdürü"]].copy()
        export_df = export_df.sort_values("PF Kutu", ascending=False)
        
        # Excel'e çevir - openpyxl engine kullan
        from io import BytesIO
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            export_df.to_excel(writer, sheet_name='Yatırım Stratejisi', index=False)
            bolge_display.to_excel(writer, sheet_name='Bölge Analizi', index=False)
        
        st.download_button(
            label="📊 Yatırım Stratejisi Raporu (Excel)",
            data=output.getvalue(),
            file_name="yatirim_stratejisi_raporu.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

with col_exp2:
    st.info("💡 PDF export özelliği yakında eklenecek!")


# =============================================================================
# PROFESYONEL GÖRSELLEŞTİRMELER - YENİ EKLEMELER
# =============================================================================
st.markdown("---")
st.markdown("## 🎯 İleri Seviye Analizler")

if len(investment_df_original) > 0:
    
    # 1. SANKEY DIAGRAM - Akış Analizi
    st.markdown("### 🌊 Sankey Akış Diyagramı: Bölge → Strateji → Top Şehirler")
    st.caption("💡 Kaynak akışını takip edin: Hangi bölgeden hangi stratejiye ne kadar PF Kutu akıyor?")
    
    # Top 15 şehir için Sankey hazırla
    sankey_df = investment_df_original.nlargest(15, 'PF Kutu').copy()
    
    # Node'ları oluştur
    all_bolge = sankey_df['Bölge'].unique().tolist()
    all_strateji = sankey_df['Yatırım Stratejisi'].unique().tolist()
    all_sehir = sankey_df['Şehir'].tolist()
    
    nodes = all_bolge + all_strateji + all_sehir
    node_dict = {node: idx for idx, node in enumerate(nodes)}
    
    # Akışları oluştur
    sources = []
    targets = []
    values = []
    colors_link = []
    
    # Bölge → Strateji
    for idx, row in sankey_df.iterrows():
        sources.append(node_dict[row['Bölge']])
        targets.append(node_dict[row['Yatırım Stratejisi']])
        values.append(row['PF Kutu'])
        colors_link.append('rgba(59, 130, 246, 0.3)')
    
    # Strateji → Şehir
    for idx, row in sankey_df.iterrows():
        sources.append(node_dict[row['Yatırım Stratejisi']])
        targets.append(node_dict[row['Şehir']])
        values.append(row['PF Kutu'])
        
        # Stratejiye göre renk
        if row['Yatırım Stratejisi'] == '🚀 Agresif':
            colors_link.append('rgba(239, 68, 68, 0.4)')
        elif row['Yatırım Stratejisi'] == '⚡ Hızlandırılmış':
            colors_link.append('rgba(245, 158, 11, 0.4)')
        elif row['Yatırım Stratejisi'] == '🛡️ Koruma':
            colors_link.append('rgba(16, 185, 129, 0.4)')
        elif row['Yatırım Stratejisi'] == '💎 Potansiyel':
            colors_link.append('rgba(139, 92, 246, 0.4)')
        else:
            colors_link.append('rgba(107, 114, 128, 0.4)')
    
    # Node renkleri
    node_colors = []
    for node in nodes:
        if node in all_bolge:
            node_colors.append('#3B82F6')  # Mavi - Bölgeler
        elif node in all_strateji:
            if '🚀' in node:
                node_colors.append('#EF4444')
            elif '⚡' in node:
                node_colors.append('#F59E0B')
            elif '🛡️' in node:
                node_colors.append('#10B981')
            elif '💎' in node:
                node_colors.append('#8B5CF6')
            else:
                node_colors.append('#6B7280')
        else:
            node_colors.append('#64748B')  # Gri - Şehirler
    
    fig_sankey = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color='white', width=2),
            label=nodes,
            color=node_colors
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=colors_link
        )
    )])
    
    fig_sankey.update_layout(
        title="Bölge → Strateji → Şehir Akışı (Top 15)",
        font=dict(size=10, color='white'),
        plot_bgcolor='#0f172a',
        paper_bgcolor='rgba(0,0,0,0)',
        height=600
    )
    
    st.plotly_chart(fig_sankey, use_container_width=True)
    
    st.markdown("---")
    
    # 2. FUNNEL CHART - Dönüşüm Hunisi
    st.markdown("### 📊 Pazar Penetrasyon Hunisi")
    st.caption("🎯 Toplam Pazar → PF Kutu → Top Performers - Dönüşüm oranlarını görün")
    
    col_funnel1, col_funnel2 = st.columns([2, 1])
    
    with col_funnel1:
        # Funnel verileri
        total_market = filtered_toplam_pazar
        total_pf = filtered_pf_toplam
        top_20_pf = investment_df_original.nlargest(20, 'PF Kutu')['PF Kutu'].sum()
        top_10_pf = investment_df_original.nlargest(10, 'PF Kutu')['PF Kutu'].sum()
        top_5_pf = investment_df_original.nlargest(5, 'PF Kutu')['PF Kutu'].sum()
        
        funnel_data = pd.DataFrame({
            'Aşama': [
                '🌍 Toplam Pazar',
                '📦 Bizim Toplam (PF)',
                '🏆 Top 20 Şehir',
                '⭐ Top 10 Şehir',
                '👑 Top 5 Şehir'
            ],
            'Değer': [total_market, total_pf, top_20_pf, top_10_pf, top_5_pf],
            'Yüzde': [
                100,
                (total_pf / total_market * 100) if total_market > 0 else 0,
                (top_20_pf / total_market * 100) if total_market > 0 else 0,
                (top_10_pf / total_market * 100) if total_market > 0 else 0,
                (top_5_pf / total_market * 100) if total_market > 0 else 0
            ]
        })
        
        fig_funnel = go.Figure(go.Funnel(
            y=funnel_data['Aşama'],
            x=funnel_data['Değer'],
            textposition='inside',
            textinfo='value+percent initial',
            opacity=0.85,
            marker=dict(
                color=['#60A5FA', '#3B82F6', '#2563EB', '#1D4ED8', '#1E40AF'],
                line=dict(width=2, color='white')
            ),
            connector=dict(line=dict(color='rgba(255,255,255,0.3)', width=2))
        ))
        
        fig_funnel.update_layout(
            height=500,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='#0f172a',
            font=dict(color='white', size=12)
        )
        
        st.plotly_chart(fig_funnel, use_container_width=True)
    
    with col_funnel2:
        st.markdown("#### 📈 Penetrasyon Metrikleri")
        
        st.metric(
            "🎯 Genel Pazar Payı",
            f"%{(total_pf / total_market * 100):.1f}" if total_market > 0 else "N/A",
            help="Toplam pazardaki payımız"
        )
        
        st.metric(
            "🏆 Top 20 Konsantrasyon",
            f"%{(top_20_pf / total_pf * 100):.1f}" if total_pf > 0 else "N/A",
            help="PF satışlarımızın ne kadarı top 20 şehirden?"
        )
        
        st.metric(
            "⭐ Top 10 Konsantrasyon",
            f"%{(top_10_pf / total_pf * 100):.1f}" if total_pf > 0 else "N/A",
            help="PF satışlarımızın ne kadarı top 10 şehirden?"
        )
        
        st.metric(
            "👑 Top 5 Konsantrasyon",
            f"%{(top_5_pf / total_pf * 100):.1f}" if total_pf > 0 else "N/A",
            help="PF satışlarımızın ne kadarı top 5 şehirden?"
        )
        
        st.info("""
        **💡 Analiz:**
        - Yüksek konsantrasyon = Risk (birkaç şehire bağımlı)
        - Düşük penetrasyon = Büyüme fırsatı
        - İdeal: Dengeli dağılım + yüksek penetrasyon
        """)
    
    st.markdown("---")
    
    # 3. PARALLEL COORDINATES - Çok Boyutlu Analiz
    st.markdown("### 🎨 Paralel Koordinat Analizi - Çok Boyutlu Şehir Profilleri")
    st.caption("🔍 Her çizgi bir şehir. Metriklerdeki kalıpları (patterns) keşfedin!")
    
    # Top 30 şehir için
    parallel_df = investment_df_original.nlargest(30, 'PF Kutu').copy()
    
    # Normalize et (0-1 arası)
    from sklearn.preprocessing import MinMaxScaler
    scaler = MinMaxScaler()
    
    metrics = ['PF Kutu', 'Toplam Kutu', 'Pazar Payı %', 'Büyüme Alanı']
    parallel_df[metrics] = scaler.fit_transform(parallel_df[metrics])
    
    # Strateji için sayısal değer
    strateji_map = {
        '🚀 Agresif': 5,
        '⚡ Hızlandırılmış': 4,
        '🛡️ Koruma': 3,
        '💎 Potansiyel': 2,
        '👁️ İzleme': 1
    }
    parallel_df['Strateji_Num'] = parallel_df['Yatırım Stratejisi'].map(strateji_map)
    
    # Renk için
    color_map = {
        '🚀 Agresif': 0,
        '⚡ Hızlandırılmış': 1,
        '🛡️ Koruma': 2,
        '💎 Potansiyel': 3,
        '👁️ İzleme': 4
    }
    parallel_df['color_code'] = parallel_df['Yatırım Stratejisi'].map(color_map)
    
    fig_parallel = go.Figure(data=go.Parcoords(
        line=dict(
            color=parallel_df['color_code'],
            colorscale=[
                [0, '#EF4444'],    # Agresif
                [0.25, '#F59E0B'], # Hızlandırılmış
                [0.5, '#10B981'],  # Koruma
                [0.75, '#8B5CF6'], # Potansiyel
                [1, '#6B7280']     # İzleme
            ],
            showscale=False
        ),
        dimensions=[
            dict(range=[0, 1], label='PF Kutu<br>(Normalize)', values=parallel_df['PF Kutu']),
            dict(range=[0, 1], label='Toplam Pazar<br>(Normalize)', values=parallel_df['Toplam Kutu']),
            dict(range=[0, 1], label='Pazar Payı %<br>(Normalize)', values=parallel_df['Pazar Payı %']),
            dict(range=[0, 1], label='Büyüme Alanı<br>(Normalize)', values=parallel_df['Büyüme Alanı']),
            dict(
                range=[1, 5],
                tickvals=[1, 2, 3, 4, 5],
                ticktext=['İzleme', 'Potansiyel', 'Koruma', 'Hızlandırılmış', 'Agresif'],
                label='Strateji',
                values=parallel_df['Strateji_Num']
            )
        ]
    ))
    
    fig_parallel.update_layout(
        height=500,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='#0f172a',
        font=dict(color='white', size=10)
    )
    
    st.plotly_chart(fig_parallel, use_container_width=True)
    
    st.info("""
    **📚 Nasıl Okunur?**
    - Her dikey çizgi bir metrik
    - Her renkli çizgi bir şehir
    - Çizgiler birbirine yakınsa benzer profilli şehirler
    - Renk = Yatırım Stratejisi
    """)
    
    st.markdown("---")
    
    # 4. ROI/PRIORITY MATRIX - Yatırım Öncelik Matrisi
    st.markdown("### 💎 Yatırım Öncelik Matrisi")
    st.caption("🎯 X: Büyüme Potansiyeli | Y: Mevcut Performans | Bubble: Pazar Büyüklüğü")
    
    # Priority Score hesapla
    priority_df = investment_df_original.copy()
    
    # Normalize metrikleri
    priority_df['Büyüme_Norm'] = (priority_df['Büyüme Alanı'] - priority_df['Büyüme Alanı'].min()) / (priority_df['Büyüme Alanı'].max() - priority_df['Büyüme Alanı'].min())
    priority_df['Performans_Norm'] = (priority_df['PF Kutu'] - priority_df['PF Kutu'].min()) / (priority_df['PF Kutu'].max() - priority_df['PF Kutu'].min())
    
    # Öncelik Skoru = (Büyüme Potansiyeli * 0.6) + (Mevcut Performans * 0.4)
    priority_df['Öncelik Skoru'] = (priority_df['Büyüme_Norm'] * 60) + (priority_df['Performans_Norm'] * 40)
    
    # Top 30
    priority_top = priority_df.nlargest(30, 'Öncelik Skoru')
    
    # Kadranları belirle
    buyume_median = priority_top['Büyüme_Norm'].median()
    perf_median = priority_top['Performans_Norm'].median()
    
    fig_priority = px.scatter(
        priority_top,
        x='Büyüme_Norm',
        y='Performans_Norm',
        size='Toplam Kutu',
        color='Yatırım Stratejisi',
        color_discrete_map={
            "🚀 Agresif": "#EF4444",
            "⚡ Hızlandırılmış": "#F59E0B",
            "🛡️ Koruma": "#10B981",
            "💎 Potansiyel": "#8B5CF6",
            "👁️ İzleme": "#6B7280"
        },
        hover_name='Şehir',
        hover_data={
            'Büyüme_Norm': False,
            'Performans_Norm': False,
            'PF Kutu': ':,.0f',
            'Toplam Kutu': ':,.0f',
            'Pazar Payı %': ':.1f',
            'Öncelik Skoru': ':.1f'
        },
        size_max=60
    )
    
    # Kadran çizgileri
    fig_priority.add_hline(y=perf_median, line_dash='dash', line_color='rgba(255,255,255,0.3)', line_width=2)
    fig_priority.add_vline(x=buyume_median, line_dash='dash', line_color='rgba(255,255,255,0.3)', line_width=2)
    
    # Kadran açıklamaları
    fig_priority.add_annotation(
        x=buyume_median + 0.3, y=perf_median + 0.3,
        text="💰 YÜKSEK ÖNCELİK<br>Büyük Fırsat + Güçlü Performans",
        showarrow=False,
        font=dict(size=11, color='rgba(16,185,129,0.5)'),
        bgcolor='rgba(0,0,0,0.5)',
        bordercolor='rgba(16,185,129,0.5)',
        borderwidth=2
    )
    
    fig_priority.add_annotation(
        x=buyume_median + 0.3, y=perf_median - 0.3,
        text="🚀 BÜYÜME FIRSATI<br>Yüksek Potansiyel + Zayıf Performans",
        showarrow=False,
        font=dict(size=11, color='rgba(239,68,68,0.5)'),
        bgcolor='rgba(0,0,0,0.5)',
        bordercolor='rgba(239,68,68,0.5)',
        borderwidth=2
    )
    
    fig_priority.add_annotation(
        x=buyume_median - 0.3, y=perf_median + 0.3,
        text="🛡️ KORUMA<br>İyi Performans + Sınırlı Büyüme",
        showarrow=False,
        font=dict(size=11, color='rgba(59,130,246,0.5)'),
        bgcolor='rgba(0,0,0,0.5)',
        bordercolor='rgba(59,130,246,0.5)',
        borderwidth=2
    )
    
    fig_priority.add_annotation(
        x=buyume_median - 0.3, y=perf_median - 0.3,
        text="👁️ İZLEME<br>Düşük Öncelik",
        showarrow=False,
        font=dict(size=11, color='rgba(107,114,128,0.5)'),
        bgcolor='rgba(0,0,0,0.5)',
        bordercolor='rgba(107,114,128,0.5)',
        borderwidth=2
    )
    
    fig_priority.update_layout(
        height=650,
        plot_bgcolor='#0f172a',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        xaxis=dict(
            title='Büyüme Potansiyeli (Normalize) →',
            range=[0, 1],
            showgrid=True,
            gridcolor='rgba(148,163,184,0.1)'
        ),
        yaxis=dict(
            title='Mevcut Performans (Normalize) →',
            range=[0, 1],
            showgrid=True,
            gridcolor='rgba(148,163,184,0.1)'
        )
    )
    
    fig_priority.update_traces(
        marker=dict(
            line=dict(width=2, color='rgba(255,255,255,0.5)'),
            opacity=0.8
        )
    )
    
    st.plotly_chart(fig_priority, use_container_width=True)
    
    # Top 10 Priority
    st.markdown("#### 🏆 En Yüksek Öncelikli 10 Şehir")
    priority_top10 = priority_df.nlargest(10, 'Öncelik Skoru')[
        ['Şehir', 'Bölge', 'PF Kutu', 'Toplam Kutu', 'Pazar Payı %', 'Öncelik Skoru', 'Yatırım Stratejisi']
    ].copy()
    priority_top10.index = range(1, 11)
    
    priority_top10['PF Kutu'] = priority_top10['PF Kutu'].apply(lambda x: f'{x:,.0f}')
    priority_top10['Toplam Kutu'] = priority_top10['Toplam Kutu'].apply(lambda x: f'{x:,.0f}')
    priority_top10['Öncelik Skoru'] = priority_top10['Öncelik Skoru'].apply(lambda x: f'{x:.1f}')
    
    st.dataframe(priority_top10, use_container_width=True, hide_index=False)
