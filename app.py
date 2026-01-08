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

    # Şehir bazında pazar payı hesapla
    merged["Pazar Payı %"] = (merged["PF Kutu"] / merged["Toplam Kutu"] * 100).round(2)
    merged["Pazar Payı %"] = merged["Pazar Payı %"].replace([float('inf'), -float('inf')], 0).fillna(0)

    # Bölge bazlı toplam hesapla
    bolge_df = (
        merged.groupby("Bölge", as_index=False)
        .agg({"PF Kutu": "sum", "Toplam Kutu": "sum"})
        .sort_values("PF Kutu", ascending=False)
    )
    
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
# FIGURE - DÜZELTİLMİŞ ETİKETLER
# =============================================================================
def create_figure(gdf, manager, view_mode, filtered_pf_toplam, filtered_toplam_pazar):
    """
    Harita oluşturur - etiketlerde FİLTRELENMİŞ veriye göre yüzde gösterir
    """
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
                    region_gdf["PF Kutu"],
                    region_gdf["Pazar Payı %"]
                )
            ),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Bölge: %{customdata[1]}<br>"
                "PF Kutu: %{customdata[2]:,.0f}<br>"
                "Pazar Payı: %{customdata[3]:.1f}%"
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
        # Bölge etiketleri - FİLTRELENMİŞ TOPLAMA GÖRE YÜZDE
        label_lons, label_lats, label_texts = [], [], []
        
        for region in gdf["Bölge"].unique():
            region_gdf = gdf[gdf["Bölge"] == region]
            total = region_gdf["PF Kutu"].sum()
            
            if total > 0:  # Sadece veri olan bölgeleri göster
                # FİLTRELENMİŞ veriye göre yüzde hesapla
                percent = (total / filtered_pf_toplam * 100) if filtered_pf_toplam > 0 else 0
                
                # Bölgedeki toplam pazar payını hesapla
                region_toplam_pazar = region_gdf["Toplam Kutu"].sum()
                pazar_payi = (total / region_toplam_pazar * 100) if region_toplam_pazar > 0 else 0
                
                lon, lat = get_region_center(region_gdf)
                label_lons.append(lon)
                label_lats.append(lat)
                label_texts.append(
                    f"<b>{region}</b><br>"
                    f"{total:,.0f} ({percent:.1f}%)<br>"
                    f"Pazar Payı: {pazar_payi:.1f}%"
                )

        fig.add_scattergeo(
            lon=label_lons,
            lat=label_lats,
            mode="text",
            text=label_texts,
            textfont=dict(size=10, color="black", family="Arial Black"),
            hoverinfo="skip",
            showlegend=False
        )
    
    else:  # Şehir Görünümü - FİLTRELENMİŞ TOPLAMA GÖRE YÜZDE
        city_lons, city_lats, city_texts = [], [], []
        
        for idx, row in gdf.iterrows():
            if row["PF Kutu"] > 0:
                # FİLTRELENMİŞ veriye göre yüzde hesapla
                percent = (row["PF Kutu"] / filtered_pf_toplam * 100) if filtered_pf_toplam > 0 else 0
                
                centroid = row.geometry.centroid
                city_lons.append(centroid.x)
                city_lats.append(centroid.y)
                city_texts.append(
                    f"<b>{row['Şehir']}</b><br>"
                    f"{row['PF Kutu']:,.0f} ({percent:.1f}%)<br>"
                    f"Pazar: {row['Pazar Payı %']:.1f}%"
                )
        
        fig.add_scattergeo(
            lon=city_lons,
            lat=city_lats,
            mode="text",
            text=city_texts,
            textfont=dict(size=8, color="black", family="Arial"),
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
# YATIRIM STRATEJİSİ - GELİŞTİRİLMİŞ ALGORİTMA
# =============================================================================
def calculate_investment_strategy(df):
    """
    Geliştirilmiş Yatırım Stratejisi Algoritması
    
    Metrikler:
    1. Pazar Büyüklüğü (Toplam Kutu): Pazarın ne kadar büyük olduğunu gösterir
    2. Mevcut Performans (PF Kutu): Şu anki satış hacmimiz
    3. Pazar Payı (%): Pazardaki yerimiz
    
    Strateji Mantığı:
    - 🚀 AGRESİF: Büyük pazar + Düşük pazar payı = Büyük büyüme potansiyeli
      → En yüksek ROI potansiyeli, agresif yatırım gerekli
    
    - ⚡ HIZLANDIRILMIŞ: Orta/Büyük pazar + Orta pazar payı = Momentum var
      → İyi performans gösteriyor, hızlandırılmış yatırım ile liderliğe geçebilir
    
    - 🛡️ KORUMA: Büyük pazar + Yüksek pazar payı = Lider pozisyon
      → Mevcut konumu korumak kritik, savunma odaklı
    
    - 💎 POTANSİYEL: Küçük pazar + Düşük pazar payı ANCAK yüksek büyüme hızı
      → Gelecek vaat eden, seçici yatırım
    
    - 👁️ İZLEME: Küçük pazar + Düşük performans
      → Düşük öncelik, izleme modunda tut
    """
    df = df.copy()
    df = df[df["PF Kutu"] > 0]  # Sadece aktif şehirler
    
    if len(df) == 0:
        return df
    
    # 1. PAZAR BÜYÜKLÜĞÜ SEGMENTİ (Toplam Kutu)
    try:
        df["Pazar Büyüklüğü"] = pd.qcut(
            df["Toplam Kutu"], 
            q=3, 
            labels=["Küçük", "Orta", "Büyük"],
            duplicates='drop'
        )
    except:
        df["Pazar Büyüklüğü"] = "Orta"
    
    # 2. PERFORMANS SEGMENTİ (PF Kutu)
    try:
        df["Performans"] = pd.qcut(
            df["PF Kutu"], 
            q=3, 
            labels=["Düşük", "Orta", "Yüksek"],
            duplicates='drop'
        )
    except:
        df["Performans"] = "Orta"
    
    # 3. PAZAR PAYI SEGMENTİ
    try:
        df["Pazar Payı Segment"] = pd.qcut(
            df["Pazar Payı %"], 
            q=3, 
            labels=["Düşük", "Orta", "Yüksek"],
            duplicates='drop'
        )
    except:
        df["Pazar Payı Segment"] = "Orta"
    
    # 4. BÜYÜME POTANSİYELİ (Gap = Pazar - Bizim Satış)
    df["Büyüme Alanı"] = df["Toplam Kutu"] - df["PF Kutu"]
    try:
        df["Büyüme Potansiyeli"] = pd.qcut(
            df["Büyüme Alanı"],
            q=3,
            labels=["Düşük", "Orta", "Yüksek"],
            duplicates='drop'
        )
    except:
        df["Büyüme Potansiyeli"] = "Orta"
    
    # 5. STRATEJİ ATAMA
    def assign_strategy(row):
        pazar_buyuklugu = str(row["Pazar Büyüklüğü"])
        pazar_payi = str(row["Pazar Payı Segment"])
        buyume_potansiyeli = str(row["Büyüme Potansiyeli"])
        performans = str(row["Performans"])
        
        # AGRESİF: Büyük pazar + Düşük pazar payı + Yüksek büyüme alanı
        if (pazar_buyuklugu in ["Büyük", "Orta"] and 
            pazar_payi == "Düşük" and 
            buyume_potansiyeli in ["Yüksek", "Orta"]):
            return "🚀 Agresif"
        
        # HIZLANDIRILMIŞ: Orta/Büyük pazar + Orta pazar payı + İyi performans
        elif (pazar_buyuklugu in ["Büyük", "Orta"] and 
              pazar_payi == "Orta" and
              performans in ["Orta", "Yüksek"]):
            return "⚡ Hızlandırılmış"
        
        # KORUMA: Büyük pazar + Yüksek pazar payı
        elif (pazar_buyuklugu == "Büyük" and 
              pazar_payi == "Yüksek"):
            return "🛡️ Koruma"
        
        # POTANSİYEL: Küçük pazar ama yüksek büyüme potansiyeli
        elif (pazar_buyuklugu == "Küçük" and 
              buyume_potansiyeli == "Yüksek" and
              performans in ["Orta", "Yüksek"]):
            return "💎 Potansiyel"
        
        # İZLEME: Geri kalan her şey
        else:
            return "👁️ İzleme"
    
    df["Yatırım Stratejisi"] = df.apply(assign_strategy, axis=1)
    
    return df

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

# Ticaret Müdürü filtresi
managers = ["TÜMÜ"] + sorted(merged["Ticaret Müdürü"].unique())
selected_manager = st.sidebar.selectbox("Ticaret Müdürü", managers)

st.sidebar.markdown("---")
st.sidebar.header("🔍 Gelişmiş Filtreler")

# Bölge filtresi
bolge_list = ["TÜMÜ"] + sorted([b for b in merged["Bölge"].unique() if b != "DİĞER"])
selected_bolge = st.sidebar.selectbox("Bölge Seçin", bolge_list)

# Yatırım stratejisi filtresi
strateji_list = ["Tümü", "🚀 Agresif", "⚡ Hızlandırılmış", "🛡️ Koruma", "💎 Potansiyel", "👁️ İzleme"]
selected_strateji = st.sidebar.selectbox("Yatırım Stratejisi", strateji_list)

# Renk legend'ı
st.sidebar.header("🎨 Bölge Renkleri")
for region, color in REGION_COLORS.items():
    if region in merged["Bölge"].values:
        st.sidebar.markdown(f"<span style='color:{color}'>⬤</span> {region}", unsafe_allow_html=True)

# =============================================================================
# FİLTRELEME MANTIĞI
# =============================================================================
# Seçilen müdüre göre veriyi filtrele
if selected_manager != "TÜMÜ":
    filtered_data = merged[merged["Ticaret Müdürü"] == selected_manager]
else:
    filtered_data = merged.copy()

# Bölge filtresini uygula
if selected_bolge != "TÜMÜ":
    filtered_data = filtered_data[filtered_data["Bölge"] == selected_bolge]

# FİLTRELENMİŞ toplam değerler (harita etiketleri için)
filtered_pf_toplam = filtered_data["PF Kutu"].sum()
filtered_toplam_pazar = filtered_data["Toplam Kutu"].sum()
filtered_aktif_sehir = (filtered_data["PF Kutu"] > 0).sum()

# Haritayı FİLTRELENMİŞ veriye göre çiz
fig = create_figure(filtered_data, selected_manager, view_mode, filtered_pf_toplam, filtered_toplam_pazar)
st.plotly_chart(fig, use_container_width=True)

# Genel İstatistikler - FİLTRELENMİŞ veriye göre
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📦 PF Toplam Kutu", f"{filtered_pf_toplam:,.0f}")
with col2:
    st.metric("🏪 Toplam Pazar", f"{filtered_toplam_pazar:,.0f}")
with col3:
    genel_pazar_payi = (filtered_pf_toplam / filtered_toplam_pazar * 100) if filtered_toplam_pazar > 0 else 0
    st.metric("📊 Genel Pazar Payı", f"%{genel_pazar_payi:.1f}")
with col4:
    st.metric("🏙️ Aktif Şehir", f"{filtered_aktif_sehir}")

# Bölge tablosu - FİLTRELENMİŞ veriye göre
display_bolge = (
    filtered_data.groupby("Bölge", as_index=False)
    .agg({"PF Kutu": "sum", "Toplam Kutu": "sum"})
    .sort_values("PF Kutu", ascending=False)
)
display_bolge["PF Pay %"] = (display_bolge["PF Kutu"] / filtered_pf_toplam * 100).round(2) if filtered_pf_toplam > 0 else 0
display_bolge["Pazar Payı %"] = (display_bolge["PF Kutu"] / display_bolge["Toplam Kutu"] * 100).round(2)
display_bolge["Pazar Payı %"] = display_bolge["Pazar Payı %"].replace([float('inf'), -float('inf')], 0).fillna(0)

st.subheader("📊 Bölge Bazlı Performans")
bolge_display = display_bolge[display_bolge["PF Kutu"] > 0].copy()
bolge_display = bolge_display[["Bölge", "PF Kutu", "Toplam Kutu", "PF Pay %", "Pazar Payı %"]]

# Sayıları formatlayarak string'e çevir
bolge_display["PF Kutu Formatli"] = bolge_display["PF Kutu"].apply(lambda x: f"{x:,.0f}")
bolge_display["Toplam Kutu Formatli"] = bolge_display["Toplam Kutu"].apply(lambda x: f"{x:,.0f}")

# Gösterilecek kolonları seç
display_cols = bolge_display[["Bölge", "PF Kutu Formatli", "Toplam Kutu Formatli", "PF Pay %", "Pazar Payı %"]].copy()
display_cols.columns = ["Bölge", "PF Kutu", "Toplam Pazar", "PF Pay % (Filtrede)", "Pazar Payı %"]

st.dataframe(
    display_cols, 
    use_container_width=True, 
    hide_index=True
)

# Yatırım Stratejisi Hesaplama - FİLTRELENMİŞ veri üzerinde
investment_df = calculate_investment_strategy(filtered_data)

# Strateji filtresini uygula
investment_df_original = investment_df.copy()  # Grafikler için orijinali sakla
if selected_strateji != "Tümü" and len(investment_df) > 0:
    investment_df = investment_df[investment_df["Yatırım Stratejisi"] == selected_strateji]

st.subheader("🎯 Yatırım Stratejisi Analizi")
if len(investment_df_original) > 0:
    # Strateji dağılımı
    strategy_counts = investment_df_original["Yatırım Stratejisi"].value_counts()
    col_a, col_b, col_c, col_d, col_e = st.columns(5)
    
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
        potansiyel_count = strategy_counts.get("💎 Potansiyel", 0)
        st.metric("💎 Potansiyel", f"{potansiyel_count} şehir")
    with col_e:
        izleme_count = strategy_counts.get("👁️ İzleme", 0)
        st.metric("👁️ İzleme", f"{izleme_count} şehir")
    
    st.markdown("---")
    st.markdown("### 📚 Strateji Açıklamaları")
    
    col_exp1, col_exp2 = st.columns(2)
    
    with col_exp1:
        st.markdown("""
        **🚀 Agresif Yatırım**
        - **Durum**: Büyük/orta pazar + Düşük pazar payımız + Yüksek büyüme alanı
        - **Anlam**: Pazarda çok büyük fırsat var, rakiplerimiz güçlü ama biz düşükteyiz
        - **Aksiyon**: En yüksek ROI potansiyeli! Agresif kaynak, promosyon, ve ekip yatırımı
        - **Hedef**: Pazar payını hızla artırmak, rakiplerin gerisinden çıkmak
        
        **⚡ Hızlandırılmış Yatırım**
        - **Durum**: Orta/büyük pazar + Orta pazar payımız + İyi performans
        - **Anlam**: İyi gidiyoruz, momentum var, liderliğe doğru ilerliyoruz
        - **Aksiyon**: Hızlandırılmış yatırım ile liderliğe geçmek için iteriz
        - **Hedef**: Orta seviyeden liderliğe geçiş
        """)
    
    with col_exp2:
        st.markdown("""
        **🛡️ Koruma**
        - **Durum**: Büyük pazar + Yüksek pazar payımız
        - **Anlam**: Zaten lideriz, konumu kaybetmemek kritik
        - **Aksiyon**: Savunma odaklı, mevcut müşterileri koruma, rakip saldırılarını önleme
        - **Hedef**: Lider pozisyonu sürdürmek
        
        **💎 Potansiyel**
        - **Durum**: Küçük pazar ama yüksek büyüme potansiyeli + İyi performansımız
        - **Anlam**: Pazar küçük ama biz iyiyiz ve pazar büyüyor olabilir
        - **Aksiyon**: Seçici yatırım, gelecek için hazırlık
        - **Hedef**: Pazarın büyüme potansiyelinden yararlanmak
        
        **👁️ İzleme**
        - **Durum**: Düşük öncelikli pazarlar
        - **Anlam**: Şu an yatırım yapmaya değmez
        - **Aksiyon**: Minimal kaynak, durumu takip et
        """)

st.subheader("🏙️ Şehir Bazlı Detay Analiz")
# Şehir bazında tabloyu hazırla
if len(investment_df) > 0:
    city_df = investment_df[[
        "Şehir", "Bölge", "PF Kutu", "Toplam Kutu", 
        "Pazar Payı %", "Yatırım Stratejisi", 
        "Pazar Büyüklüğü", "Performans", "Pazar Payı Segment",
        "Büyüme Potansiyeli", "Ticaret Müdürü"
    ]].copy()
else:
    city_df = filtered_data[filtered_data["PF Kutu"] > 0][[
        "Şehir", "Bölge", "PF Kutu", "Toplam Kutu", 
        "Pazar Payı %", "Ticaret Müdürü"
    ]].copy()
    city_df["Yatırım Stratejisi"] = "👁️ İzleme"

# PF Kutu'ya göre sırala
city_df = city_df.sort_values("PF Kutu", ascending=False).reset_index(drop=True)

# Sayıları formatlayarak string'e çevir
city_df["PF Kutu Formatli"] = city_df["PF Kutu"].apply(lambda x: f"{x:,.0f}")
city_df["Toplam Kutu Formatli"] = city_df["Toplam Kutu"].apply(lambda x: f"{x:,.0f}")

# FİLTRELENMİŞ veriye göre PF Pay % hesapla
city_df["PF Pay % (Filtrede)"] = (city_df["PF Kutu"] / filtered_pf_toplam * 100).round(2) if filtered_pf_toplam > 0 else 0

# Index'i 1'den başlat
city_df.index = city_df.index + 1

# Gösterilecek kolonları yeniden düzenle
if len(investment_df) > 0:
    display_city = city_df[[
        "Şehir", "Bölge", "PF Kutu Formatli", "Toplam Kutu Formatli",
        "PF Pay % (Filtrede)", "Pazar Payı %",
        "Yatırım Stratejisi", "Pazar Büyüklüğü", "Büyüme Potansiyeli",
        "Ticaret Müdürü"
    ]].copy()
    display_city.columns = [
        "Şehir", "Bölge", "PF Kutu", "Toplam Pazar",
        "PF Pay % (Filtre)", "Pazar Payı %",
        "Strateji", "Pazar", "Büyüme",
        "Ticaret Müdürü"
    ]
else:
    display_city = city_df[[
        "Şehir", "Bölge", "PF Kutu Formatli", "Toplam Kutu Formatli",
        "PF Pay % (Filtrede)", "Pazar Payı %", "Yatırım Stratejisi",
        "Ticaret Müdürü"
    ]].copy()
    display_city.columns = [
        "Şehir", "Bölge", "PF Kutu", "Toplam Pazar",
        "PF Pay % (Filtre)", "Pazar Payı %", "Strateji",
        "Ticaret Müdürü"
    ]

st.caption("📊 Şehirler **PF Kutu hacmine** göre sıralanmıştır")
st.dataframe(
    display_city,
    use_container_width=True,
    hide_index=False
)

# =============================================================================
# GÖRSELLEŞTİRMELER - İYİLEŞTİRİLMİŞ
# =============================================================================
import plotly.express as px

st.markdown("---")
st.subheader("📊 Görsel Analizler")

if len(investment_df_original) > 0:
    col_viz1, col_viz2 = st.columns(2)
    
    with col_viz1:
        st.markdown("#### 🏆 Top 10 Öncelikli Şehirler")
        if "Öncelik Skoru" in investment_df_original.columns:
            top10 = investment_df_original.nlargest(10, "Öncelik Skoru")[["Şehir", "Öncelik Skoru", "Yatırım Stratejisi"]]
            fig_bar = px.bar(
                top10, 
                x="Öncelik Skoru", 
                y="Şehir",
                orientation='h',
                color="Yatırım Stratejisi",
                text="Öncelik Skoru",
                color_discrete_map={
                    "🚀 Agresif": "#EF4444",
                    "⚡ Hızlandırılmış": "#F59E0B",
                    "🛡️ Koruma": "#10B981",
                    "💎 Potansiyel": "#8B5CF6",
                    "👁️ İzleme": "#6B7280"
                }
            )
            fig_bar.update_traces(textposition='outside', texttemplate='%{text:.0f}')
        else:
            top10 = investment_df_original.nlargest(10, "PF Kutu")[["Şehir", "PF Kutu"]]
            fig_bar = px.bar(
                top10, 
                x="PF Kutu", 
                y="Şehir",
                orientation='h',
                color="PF Kutu",
                color_continuous_scale=["#3B82F6", "#1E40AF"]
            )
            fig_bar.update_traces(textposition='outside', texttemplate='%{text:,.0f}')
        
        fig_bar.update_layout(
            height=400, 
            showlegend=True, 
            yaxis={'categoryorder':'total ascending'},
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    
    with col_viz2:
        st.markdown("#### 🎯 Yatırım Stratejisi Dağılımı")
        strateji_counts = investment_df_original["Yatırım Stratejisi"].value_counts().reset_index()
        strateji_counts.columns = ["Strateji", "Şehir Sayısı"]
        
        # Modern renkler - stratejiye uygun
        color_map = {
            "🚀 Agresif": "#EF4444",         # Kırmızı - Agresif
            "⚡ Hızlandırılmış": "#F59E0B",  # Turuncu - Hızlı
            "🛡️ Koruma": "#10B981",         # Yeşil - Güvenli
            "💎 Potansiyel": "#8B5CF6",     # Mor - Değerli
            "👁️ İzleme": "#6B7280"          # Gri - Pasif
        }
        
        fig_pie = px.pie(
            strateji_counts,
            values="Şehir Sayısı",
            names="Strateji",
            color="Strateji",
            color_discrete_map=color_map
        )
        fig_pie.update_layout(
            height=400,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)
    
    # İYİLEŞTİRİLMİŞ Scatter plot: Pazar Büyüklüğü vs Pazar Payı
    st.markdown("#### 💡 Pazar Haritası: Büyüklük vs Pazar Payı")
    
    # Nokta boyutlarını normalize et (çok küçük noktaları önlemek için)
    scatter_df = investment_df_original.copy()
    scatter_df["Nokta Boyutu"] = scatter_df["PF Kutu"]
    
    # Min-max normalization ile boyutları 15-80 arasına getir (daha dengeli)
    min_val = scatter_df["Nokta Boyutu"].min()
    max_val = scatter_df["Nokta Boyutu"].max()
    if max_val > min_val:
        scatter_df["Nokta Boyutu"] = 15 + (scatter_df["Nokta Boyutu"] - min_val) / (max_val - min_val) * 65
    else:
        scatter_df["Nokta Boyutu"] = 40
    
    # Modern renk paleti
    color_map = {
        "🚀 Agresif": "#EF4444",         # Kırmızı
        "⚡ Hızlandırılmış": "#F59E0B",  # Turuncu
        "🛡️ Koruma": "#10B981",         # Yeşil
        "💎 Potansiyel": "#8B5CF6",     # Mor
        "👁️ İzleme": "#6B7280"          # Gri
    }
    
    fig_scatter = px.scatter(
        scatter_df,
        x="Toplam Kutu",
        y="Pazar Payı %",
        size="Nokta Boyutu",
        color="Yatırım Stratejisi",
        color_discrete_map=color_map,
        hover_name="Şehir",
        hover_data={
            "Toplam Kutu": ":,.0f", 
            "PF Kutu": ":,.0f", 
            "Pazar Payı %": ":.1f",
            "Nokta Boyutu": False
        },
        labels={
            "Toplam Kutu": "Pazar Büyüklüğü (Toplam Kutu)",
            "Pazar Payı %": "Pazar Payımız (%)"
        },
        title="Her nokta bir şehir - Büyüklük = PF Kutu hacmimiz",
        size_max=50
    )
    
    # Tasarım iyileştirmeleri
    fig_scatter.update_layout(
        height=550,
        plot_bgcolor='rgba(245,245,245,0.5)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(200,200,200,0.3)',
            zeroline=False
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(200,200,200,0.3)',
            zeroline=False
        ),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="rgba(0,0,0,0.1)",
            borderwidth=1
        )
    )
    
    # Nokta kenarları ekle
    fig_scatter.update_traces(
        marker=dict(
            line=dict(width=1.5, color='rgba(255,255,255,0.6)')
        )
    )
    
    st.plotly_chart(fig_scatter, use_container_width=True)
    
    # Rehber kartları yan yana daha kompakt
    col_guide1, col_guide2 = st.columns(2)
    with col_guide1:
        st.info("""
        **🎯 Sağ Üst Bölge**  
        🛡️ Koruma stratejisi  
        Büyük pazar + Yüksek payımız = Lider pozisyon
        
        **🚀 Sağ Alt Bölge**  
        🚀 Agresif strateji  
        Büyük pazar + Düşük payımız = En yüksek fırsat!
        """)
    with col_guide2:
        st.info("""
        **💎 Sol Üst Bölge**  
        Niş liderlikler  
        Küçük pazar + Yüksek payımız
        
        **👁️ Sol Alt Bölge**  
        👁️ İzleme stratejisi  
        Küçük pazar + Düşük payımız = Düşük öncelik
        """)

# =============================================================================
# EXPORT ÖZELLİKLERİ
# =============================================================================
st.markdown("---")
st.subheader("📥 Raporları İndir")

col_exp1, col_exp2 = st.columns(2)

with col_exp1:
    if len(investment_df_original) > 0:
        # Yatırım Stratejisi Raporu Excel Export
        export_df = investment_df_original[[
            "Şehir", "Bölge", "PF Kutu", "Toplam Kutu", "Pazar Payı %",
            "Yatırım Stratejisi", "Pazar Büyüklüğü", "Performans",
            "Büyüme Potansiyeli", "Ticaret Müdürü"
        ]].copy()
        export_df = export_df.sort_values("PF Kutu", ascending=False)
        
        # Excel'e çevir
        from io import BytesIO
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            export_df.to_excel(writer, sheet_name='Yatırım Stratejisi', index=False)
            display_bolge.to_excel(writer, sheet_name='Bölge Analizi', index=False)
        
        st.download_button(
            label="📊 Yatırım Stratejisi Raporu (Excel)",
            data=output.getvalue(),
            file_name="yatirim_stratejisi_raporu.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

with col_exp2:
    st.info("💡 İlerleyen zamanlarda PDF export özelliği eklenecek!")
