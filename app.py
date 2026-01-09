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
                color_discrete_map={
                    "🚀 Agresif": "#EF4444",
                    "⚡ Hızlandırılmış": "#F59E0B",
                    "🛡️ Koruma": "#10B981",
                    "💎 Potansiyel": "#8B5CF6",
                    "👁️ İzleme": "#6B7280"
                }
            )
            fig_bar.update_traces(textposition='outside', texttemplate='%{x:.0f}')
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
            fig_bar.update_traces(textposition='outside', texttemplate='%{x:,.0f}')
        
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
    
    # =========================================================================
    # YENİ GÖRSELLEŞTİRMELER - 6 FARKLI ANALİZ
    # =========================================================================
    
    # 1. TREEMAP - Hiyerarşik Görünüm (En Anlaşılır)
    st.markdown("#### 🗺️ Hiyerarşik Pazar Haritası")
    st.caption("📦 Bölge → Strateji → Şehir • Kutu boyutu = PF Kutu | Renk = Pazar Payı %")
    
    treemap_df = investment_df_original.copy()
    treemap_df["Strateji_Kısa"] = treemap_df["Yatırım Stratejisi"].str.replace("🚀 ", "").str.replace("⚡ ", "").str.replace("🛡️ ", "").str.replace("💎 ", "").str.replace("👁️ ", "")
    
    fig_treemap = px.treemap(
        treemap_df,
        path=[px.Constant("TÜRKİYE"), 'Bölge', 'Strateji_Kısa', 'Şehir'],
        values='PF Kutu',
        color='Pazar Payı %',
        color_continuous_scale='Blues',
        color_continuous_midpoint=treemap_df['Pazar Payı %'].median(),
        hover_data={
            'PF Kutu': ':,.0f',
            'Pazar Payı %': ':.1f',
            'Toplam Kutu': ':,.0f'
        }
    )
    
    fig_treemap.update_layout(
        height=600,
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(size=11, color='white')
    )
    
    fig_treemap.update_traces(
        textposition="middle center",
        marker=dict(line=dict(color='white', width=2))
    )
    
    st.plotly_chart(fig_treemap, use_container_width=True)
    
    st.markdown("---")
    
    # 2 & 3. SUNBURST + TOP 15 DUAL AXIS
    col_sun1, col_sun2 = st.columns(2)
    
    with col_sun1:
        st.markdown("#### ☀️ Radyal Dağılım (Sunburst)")
        st.caption("🎯 Merkezden dışa: Türkiye → Bölge → Strateji")
        
        sunburst_df = investment_df_original.groupby(['Bölge', 'Yatırım Stratejisi'], as_index=False).agg({
            'PF Kutu': 'sum',
            'Pazar Payı %': 'mean'
        })
        
        fig_sunburst = px.sunburst(
            sunburst_df,
            path=[px.Constant("TÜRKİYE"), 'Bölge', 'Yatırım Stratejisi'],
            values='PF Kutu',
            color='Pazar Payı %',
            color_continuous_scale='Viridis',
            hover_data={'PF Kutu': ':,.0f', 'Pazar Payı %': ':.1f'}
        )
        
        fig_sunburst.update_layout(
            height=500,
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(size=10, color='white')
        )
        
        st.plotly_chart(fig_sunburst, use_container_width=True)
    
    with col_sun2:
        st.markdown("#### 📊 Top 15 Şehir - PF Kutu Hacmi")
        st.caption("🏆 En yüksek PF Kutu hacmine sahip 15 şehir")
        
        top15 = investment_df_original.nlargest(15, 'PF Kutu').copy()
        
        fig_top15 = px.bar(
            top15,
            x='Şehir',
            y='PF Kutu',
            color='Pazar Payı %',
            color_continuous_scale='Blues',
            text='PF Kutu',
            hover_data={'PF Kutu': ':,.0f', 'Pazar Payı %': ':.1f', 'Toplam Kutu': ':,.0f'}
        )
        
        fig_top15.update_traces(
            texttemplate='%{text:,.0f}',
            textposition='outside',
            textfont=dict(size=9, color='white')
        )
        
        fig_top15.update_layout(
            height=500,
            plot_bgcolor='#1a1a2e',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white', size=10),
            xaxis=dict(tickangle=-45),
            yaxis=dict(title='PF Kutu'),
            showlegend=False
        )
        
        st.plotly_chart(fig_top15, use_container_width=True)
    
    st.markdown("---")
    
    # 4 & 5. BOX PLOT + VIOLIN PLOT
    col_dist1, col_dist2 = st.columns(2)
    
    with col_dist1:
        st.markdown("#### 📦 Bölgelere Göre Dağılım (Box Plot)")
        st.caption("🎻 Her bölgedeki şehirlerin PF Kutu dağılımı")
        
        fig_box = px.box(
            investment_df_original,
            x='Bölge',
            y='PF Kutu',
            color='Bölge',
            points='all',
            hover_data={'Şehir': True, 'PF Kutu': ':,.0f'}
        )
        
        fig_box.update_layout(
            height=450,
            plot_bgcolor='#0f172a',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white', size=10),
            xaxis=dict(tickangle=-45, showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
            showlegend=False
        )
        
        st.plotly_chart(fig_box, use_container_width=True)
    
    with col_dist2:
        st.markdown("#### 📈 Strateji Bazlı Pazar Payı")
        st.caption("🎯 Her stratejideki ortalama pazar payı (±Std)")
        
        strateji_stats = investment_df_original.groupby('Yatırım Stratejisi').agg({
            'Pazar Payı %': ['mean', 'std', 'count'],
            'PF Kutu': 'sum'
        }).reset_index()
        
        strateji_stats.columns = ['Strateji', 'Ort_Pay', 'Std_Pay', 'Şehir_Sayısı', 'Toplam_PF']
        
        fig_strateji = go.Figure()
        
        colors_map = {
            "🚀 Agresif": "#EF4444",
            "⚡ Hızlandırılmış": "#F59E0B",
            "🛡️ Koruma": "#10B981",
            "💎 Potansiyel": "#8B5CF6",
            "👁️ İzleme": "#6B7280"
        }
        
        fig_strateji.add_trace(go.Bar(
            x=strateji_stats['Strateji'],
            y=strateji_stats['Ort_Pay'],
            error_y=dict(type='data', array=strateji_stats['Std_Pay']),
            marker_color=[colors_map.get(s, '#6B7280') for s in strateji_stats['Strateji']],
            text=strateji_stats['Ort_Pay'].apply(lambda x: f'{x:.1f}%'),
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Ortalama: %{y:.1f}%<br>Şehir: %{customdata}<extra></extra>',
            customdata=strateji_stats['Şehir_Sayısı']
        ))
        
        fig_strateji.update_layout(
            height=450,
            plot_bgcolor='#0f172a',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white', size=10),
            xaxis=dict(showgrid=False, tickangle=-20),
            yaxis=dict(
                title='Ortalama Pazar Payı %',
                showgrid=True,
                gridcolor='rgba(255,255,255,0.1)'
            )
        )
        
        st.plotly_chart(fig_strateji, use_container_width=True)
    
    st.markdown("---")
    
    # 6. WATERFALL CHART - Bölge Katkı Analizi
    st.markdown("#### 💧 Bölgelerin Kümülatif Katkı Analizi (Waterfall)")
    st.caption("📊 Her bölgenin toplam PF Kutu'ya katkısı - soldan sağa birikiyor")
    
    bolge_katki = investment_df_original.groupby('Bölge')['PF Kutu'].sum().sort_values(ascending=False).reset_index()
    
    fig_waterfall = go.Figure(go.Waterfall(
        name="PF Kutu",
        orientation="v",
        measure=["relative"] * len(bolge_katki) + ["total"],
        x=list(bolge_katki['Bölge']) + ["🎯 TOPLAM"],
        y=list(bolge_katki['PF Kutu']) + [0],  # Son değer otomatik hesaplanır
        text=[f"{x:,.0f}" for x in bolge_katki['PF Kutu']] + [f"{bolge_katki['PF Kutu'].sum():,.0f}"],
        textposition="outside",
        connector={"line": {"color": "rgba(255,255,255,0.3)", "width": 2}},
        increasing={"marker": {"color": "#10B981", "line": {"color": "white", "width": 1}}},
        decreasing={"marker": {"color": "#EF4444"}},
        totals={"marker": {"color": "#3B82F6", "line": {"color": "white", "width": 2}}}
    ))
    
    fig_waterfall.update_layout(
        height=500,
        plot_bgcolor='#0f172a',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white', size=11),
        xaxis=dict(tickangle=-45, showgrid=False),
        yaxis=dict(
            title='PF Kutu (Kümülatif)',
            showgrid=True,
            gridcolor='rgba(255,255,255,0.1)'
        ),
        showlegend=False
    )
    
    st.plotly_chart(fig_waterfall, use_container_width=True)
    
    st.markdown("---")
    
    # 7. HEATMAP - Bölge x Strateji Matrix
    st.markdown("#### 🔥 Bölge × Strateji Isı Haritası")
    st.caption("🎨 Hangi bölgede hangi strateji ne kadar güçlü?")
    
    heatmap_data = investment_df_original.pivot_table(
        index='Bölge',
        columns='Yatırım Stratejisi',
        values='PF Kutu',
        aggfunc='sum',
        fill_value=0
    )
    
    fig_heatmap = px.imshow(
        heatmap_data,
        labels=dict(x="Yatırım Stratejisi", y="Bölge", color="PF Kutu"),
        color_continuous_scale='YlOrRd',
        aspect="auto",
        text_auto='.0f'
    )
    
    fig_heatmap.update_layout(
        height=500,
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white', size=10),
        xaxis=dict(tickangle=-30)
    )
    
    st.plotly_chart(fig_heatmap, use_container_width=True)
    
    st.markdown("---")
    
    # 8. BCG MATRIX - Stratejik Pozisyonlama (MAVİ TONLARI)
    st.markdown("#### 🎯 BCG Matrix - Stratejik Pazar Pozisyonları")
    st.caption("⭐ Stars | ❓ Question Marks | 💰 Cash Cows | 🐕 Dogs")
    
    col_bcg1, col_bcg2 = st.columns([2, 1])
    
    with col_bcg1:
        # BCG Matrix hesaplamaları
        scatter_df = investment_df_original.copy()
        
        # Median değerler
        pazar_median = scatter_df["Toplam Kutu"].median()
        pay_median = scatter_df["Pazar Payı %"].median()
        
        # BCG Kadran atama
        def assign_bcg_quadrant(row):
            if row["Toplam Kutu"] >= pazar_median and row["Pazar Payı %"] >= pay_median:
                return "⭐ Stars (Yıldızlar)"
            elif row["Toplam Kutu"] >= pazar_median and row["Pazar Payı %"] < pay_median:
                return "❓ Question Marks (Soru İşaretleri)"
            elif row["Toplam Kutu"] < pazar_median and row["Pazar Payı %"] >= pay_median:
                return "💰 Cash Cows (Nakit İnekleri)"
            else:
                return "🐕 Dogs (Düşük Öncelik)"
        
        scatter_df["BCG Kategori"] = scatter_df.apply(assign_bcg_quadrant, axis=1)
        
        # Mavi tonları renk paleti
        color_map_bcg = {
            "⭐ Stars (Yıldızlar)": "#1E40AF",
            "❓ Question Marks (Soru İşaretleri)": "#3B82F6",
            "💰 Cash Cows (Nakit İnekleri)": "#60A5FA",
            "🐕 Dogs (Düşük Öncelik)": "#93C5FD"
        }
        
        # Nokta boyutları
        min_val = scatter_df["PF Kutu"].min()
        max_val = scatter_df["PF Kutu"].max()
        if max_val > min_val:
            scatter_df["Nokta Boyutu"] = 20 + (scatter_df["PF Kutu"] - min_val) / (max_val - min_val) * 40
        else:
            scatter_df["Nokta Boyutu"] = 35
        
        # BCG Scatter Plot
        fig_bcg = px.scatter(
            scatter_df,
            x="Toplam Kutu",
            y="Pazar Payı %",
            size="Nokta Boyutu",
            color="BCG Kategori",
            color_discrete_map=color_map_bcg,
            hover_name="Şehir",
            hover_data={
                "Toplam Kutu": ":,.0f",
                "PF Kutu": ":,.0f",
                "Pazar Payı %": ":.1f",
                "Nokta Boyutu": False,
                "BCG Kategori": True
            },
            labels={
                "Toplam Kutu": "Pazar Büyüklüğü →",
                "Pazar Payı %": "Pazar Payımız (%) →"
            },
            size_max=50
        )
        
        # Kadran çizgileri
        fig_bcg.add_hline(y=pay_median, line_dash="dash", line_color="rgba(255,255,255,0.4)", line_width=2)
        fig_bcg.add_vline(x=pazar_median, line_dash="dash", line_color="rgba(255,255,255,0.4)", line_width=2)
        
        # Kadran etiketleri
        max_x = scatter_df["Toplam Kutu"].max()
        max_y = scatter_df["Pazar Payı %"].max()
        
        annotations = [
            dict(x=pazar_median + (max_x - pazar_median) * 0.5, y=pay_median + (max_y - pay_median) * 0.5,
                 text="⭐<br>STARS", showarrow=False,
                 font=dict(size=18, color="rgba(30,64,175,0.3)", family="Arial Black")),
            dict(x=pazar_median + (max_x - pazar_median) * 0.5, y=pay_median * 0.5,
                 text="❓<br>QUESTION<br>MARKS", showarrow=False,
                 font=dict(size=16, color="rgba(59,130,246,0.3)", family="Arial Black")),
            dict(x=pazar_median * 0.5, y=pay_median + (max_y - pay_median) * 0.5,
                 text="💰<br>CASH<br>COWS", showarrow=False,
                 font=dict(size=16, color="rgba(96,165,250,0.3)", family="Arial Black")),
            dict(x=pazar_median * 0.5, y=pay_median * 0.5,
                 text="🐕<br>DOGS", showarrow=False,
                 font=dict(size=18, color="rgba(147,197,253,0.3)", family="Arial Black"))
        ]
        
        # Layout
        fig_bcg.update_layout(
            height=600,
            plot_bgcolor='#0f172a',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e2e8f0', size=11),
            xaxis=dict(showgrid=True, gridwidth=0.5, gridcolor='rgba(148,163,184,0.15)', zeroline=False),
            yaxis=dict(showgrid=True, gridwidth=0.5, gridcolor='rgba(148,163,184,0.15)', zeroline=False),
            legend=dict(orientation="v", yanchor="top", y=0.98, xanchor="left", x=0.01,
                       bgcolor="rgba(15,23,42,0.9)", bordercolor="rgba(148,163,184,0.3)", borderwidth=1),
            annotations=annotations
        )
        
        fig_bcg.update_traces(marker=dict(line=dict(width=2, color='rgba(255,255,255,0.5)'), opacity=0.85))
        
        st.plotly_chart(fig_bcg, use_container_width=True)
    
    with col_bcg2:
        st.markdown("##### 📚 BCG Matrix Rehberi")
        
        st.success("""
        **⭐ STARS (Yıldızlar)**  
        Büyük pazar + Yüksek pay  
        → Lider pozisyonlar  
        → Büyümeye devam et  
        → Yatırım yap, koru, genişlet
        """)
        
        st.info("""
        **❓ QUESTION MARKS (Soru İşaretleri)**  
        Büyük pazar + Düşük pay  
        → En yüksek fırsatlar!  
        → Agresif yatırım gerekli  
        → Star olmak için çabala
        """)
        
        st.warning("""
        **💰 CASH COWS (Nakit İnekleri)**  
        Küçük pazar + Yüksek pay  
        → Stabil gelir kaynağı  
        → Minimal yatırım  
        → Kazancı başka alanlara aktar
        """)
        
        st.error("""
        **🐕 DOGS (Düşük Öncelik)**  
        Küçük pazar + Düşük pay  
        → Düşük öncelik  
        → Minimal kaynak  
        → İzleme modu veya çıkış
        """)
    
    # BCG Dağılımı - Grafiğin Altında
    st.markdown("---")
    st.markdown("##### 📊 BCG Kadran Dağılımı")
    st.caption("Her kadranda kaç şehir var ve toplam PF Kutu hacmi ne kadar?")
    
    # 4 kolon yan yana
    col_dist1, col_dist2, col_dist3, col_dist4 = st.columns(4)
    
    bcg_stats = scatter_df.groupby('BCG Kategori').agg({
        'Şehir': 'count',
        'PF Kutu': 'sum',
        'Pazar Payı %': 'mean'
    }).reset_index()
    bcg_stats.columns = ['Kategori', 'Şehir Sayısı', 'Toplam PF Kutu', 'Ort. Pay']
    
    bcg_dict = bcg_stats.set_index('Kategori').to_dict('index')
    
    with col_dist1:
        if "⭐ Stars (Yıldızlar)" in bcg_dict:
            row = bcg_dict["⭐ Stars (Yıldızlar)"]
            st.metric(
                label="⭐ Stars",
                value=f"{int(row['Şehir Sayısı'])} şehir",
                delta=f"{row['Toplam PF Kutu']:,.0f} PF Kutu",
                help="Bu kadranda toplam PF Kutu hacmi"
            )
    
    with col_dist2:
        if "❓ Question Marks (Soru İşaretleri)" in bcg_dict:
            row = bcg_dict["❓ Question Marks (Soru İşaretleri)"]
            st.metric(
                label="❓ Question Marks",
                value=f"{int(row['Şehir Sayısı'])} şehir",
                delta=f"{row['Toplam PF Kutu']:,.0f} PF Kutu",
                help="Bu kadranda toplam PF Kutu hacmi"
            )
    
    with col_dist3:
        if "💰 Cash Cows (Nakit İnekleri)" in bcg_dict:
            row = bcg_dict["💰 Cash Cows (Nakit İnekleri)"]
            st.metric(
                label="💰 Cash Cows",
                value=f"{int(row['Şehir Sayısı'])} şehir",
                delta=f"{row['Toplam PF Kutu']:,.0f} PF Kutu",
                help="Bu kadranda toplam PF Kutu hacmi"
            )
    
    with col_dist4:
        if "🐕 Dogs (Düşük Öncelik)" in bcg_dict:
            row = bcg_dict["🐕 Dogs (Düşük Öncelik)"]
            st.metric(
                label="🐕 Dogs",
                value=f"{int(row['Şehir Sayısı'])} şehir",
                delta=f"{row['Toplam PF Kutu']:,.0f} PF Kutu",
                delta_color="off",
                help="Bu kadranda toplam PF Kutu hacmi"
            )
    
    st.markdown("---")
    
    # 4. ÇOK BOYUTLU ŞEHİR ANALİZİ - PROFESYONEL
    st.markdown("#### 🔗 Çok Boyutlu Şehir Analizi (Top 30)")
    st.caption("📊 Üç boyutlu metrik analizi: PF Kutu, Pazar Büyüklüğü ve Pazar Payı")
    
    top30_df = investment_df_original.nlargest(30, 'PF Kutu').copy()
    
    col_3d1, col_3d2 = st.columns(2)
    
    with col_3d1:
        st.markdown("##### 🌐 3D Metrik Uzayı")
        
        # 3D Scatter Plot
        fig_3d = px.scatter_3d(
            top30_df,
            x='Toplam Kutu',
            y='PF Kutu',
            z='Pazar Payı %',
            size='PF Kutu',
            color='Pazar Payı %',
            color_continuous_scale='Blues',
            hover_name='Şehir',
            hover_data={
                'Bölge': True,
                'Toplam Kutu': ':,.0f',
                'PF Kutu': ':,.0f',
                'Pazar Payı %': ':.1f',
                'Yatırım Stratejisi': True
            },
            labels={
                'Toplam Kutu': 'Pazar Büyüklüğü',
                'PF Kutu': 'Bizim Hacmimiz',
                'Pazar Payı %': 'Pazar Payımız (%)'
            },
            size_max=30
        )
        
        fig_3d.update_layout(
            height=550,
            paper_bgcolor='rgba(0,0,0,0)',
            scene=dict(
                bgcolor='#0f172a',
                xaxis=dict(
                    title='Pazar Büyüklüğü →',
                    backgroundcolor='#0f172a',
                    gridcolor='rgba(148,163,184,0.2)',
                    showbackground=True
                ),
                yaxis=dict(
                    title='Bizim Hacmimiz →',
                    backgroundcolor='#0f172a',
                    gridcolor='rgba(148,163,184,0.2)',
                    showbackground=True
                ),
                zaxis=dict(
                    title='Pazar Payı % →',
                    backgroundcolor='#0f172a',
                    gridcolor='rgba(148,163,184,0.2)',
                    showbackground=True
                ),
                camera=dict(
                    eye=dict(x=1.5, y=1.5, z=1.3)
                )
            ),
            font=dict(color='#e2e8f0', size=10)
        )
        
        fig_3d.update_traces(
            marker=dict(
                line=dict(width=1, color='rgba(255,255,255,0.4)'),
                opacity=0.9
            )
        )
        
        st.plotly_chart(fig_3d, use_container_width=True)
        st.caption("🎯 3 eksende şehirlerin konumu. Büyük top = Yüksek hacim. Koyu mavi = Yüksek pazar payı.")
    
    with col_3d2:
        st.markdown("##### 💎 Stratejik Konumlandırma")
        
        # Advanced Bubble Chart - Stratejiye göre
        fig_bubble_adv = px.scatter(
            top30_df,
            x='Toplam Kutu',
            y='Pazar Payı %',
            size='PF Kutu',
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
                'Bölge': True,
                'Toplam Kutu': ':,.0f',
                'PF Kutu': ':,.0f',
                'Pazar Payı %': ':.1f'
            },
            labels={
                'Toplam Kutu': 'Pazar Büyüklüğü',
                'Pazar Payı %': 'Pazar Payımız (%)'
            },
            size_max=50
        )
        
        fig_bubble_adv.update_layout(
            height=550,
            plot_bgcolor='#0f172a',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e2e8f0', size=10),
            xaxis=dict(
                title='Pazar Büyüklüğü (Toplam Kutu) →',
                showgrid=True,
                gridcolor='rgba(148,163,184,0.15)',
                zeroline=False
            ),
            yaxis=dict(
                title='Pazar Payımız (%) →',
                showgrid=True,
                gridcolor='rgba(148,163,184,0.15)',
                zeroline=False
            ),
            legend=dict(
                title='Yatırım Stratejisi',
                orientation='v',
                yanchor='top',
                y=0.98,
                xanchor='left',
                x=0.01,
                bgcolor='rgba(15,23,42,0.9)',
                bordercolor='rgba(148,163,184,0.3)',
                borderwidth=1
            )
        )
        
        fig_bubble_adv.update_traces(
            marker=dict(
                line=dict(width=2, color='rgba(255,255,255,0.5)'),
                opacity=0.85
            )
        )
        
        st.plotly_chart(fig_bubble_adv, use_container_width=True)
        st.caption("💡 Bubble boyutu = PF Kutu. Renk = Strateji. Sağ üst köşe = İdeal pozisyon.")
    
    st.markdown("---")
    
    # Detaylı Tablo
    st.markdown("##### 📋 Detaylı Şehir Sıralaması")
    
    top30_display = top30_df.reset_index(drop=True)
    top30_display.index = top30_display.index + 1
    
    display_cols = ['Şehir', 'Bölge', 'PF Kutu', 'Toplam Kutu', 'Pazar Payı %', 'Yatırım Stratejisi']
    top30_display_formatted = top30_display[display_cols].copy()
    
    # Formatting
    top30_display_formatted['PF Kutu'] = top30_display_formatted['PF Kutu'].apply(lambda x: f'{x:,.0f}')
    top30_display_formatted['Toplam Kutu'] = top30_display_formatted['Toplam Kutu'].apply(lambda x: f'{x:,.0f}')
    top30_display_formatted['Pazar Payı %'] = top30_display_formatted['Pazar Payı %'].apply(lambda x: f'{x:.1f}%')
    
    # Conditional formatting için stil
    def highlight_top(row):
        if row.name <= 5:
            return ['background-color: rgba(16, 185, 129, 0.2)'] * len(row)
        elif row.name <= 10:
            return ['background-color: rgba(59, 130, 246, 0.2)'] * len(row)
        else:
            return [''] * len(row)
    
    st.dataframe(
        top30_display_formatted,
        use_container_width=True,
        hide_index=False,
        height=400
    )
    
    # Metrik özeti
    col_sum1, col_sum2, col_sum3, col_sum4 = st.columns(4)
    
    with col_sum1:
        st.metric("🏆 Top 30 Toplam PF", f"{top30_df['PF Kutu'].sum():,.0f}")
    
    with col_sum2:
        st.metric("📊 Ortalama Pazar Payı", f"%{top30_df['Pazar Payı %'].mean():.1f}")
    
    with col_sum3:
        st.metric("🎯 En Yüksek Pay", f"%{top30_df['Pazar Payı %'].max():.1f}")
    
    with col_sum4:
        st.metric("📈 Toplam Pazar", f"{top30_df['Toplam Kutu'].sum():,.0f}")
    
    st.markdown("---")
    
    # 5. RADAR CHART - Bölge Karşılaştırması
    st.markdown("#### 🎯 Bölge Performans Karşılaştırması")
    
    # Bölge bazında metrikler
    bolge_metrics = investment_df_original.groupby('Bölge').agg({
        'PF Kutu': 'sum',
        'Toplam Kutu': 'sum',
        'Pazar Payı %': 'mean',
        'Şehir': 'count'
    }).reset_index()
    
    bolge_metrics.columns = ['Bölge', 'PF Kutu', 'Toplam Kutu', 'Ort Pazar Payı', 'Şehir Sayısı']
    
    # Normalize et (0-100 arası)
    for col in ['PF Kutu', 'Toplam Kutu', 'Ort Pazar Payı', 'Şehir Sayısı']:
        bolge_metrics[f'{col} Norm'] = (bolge_metrics[col] - bolge_metrics[col].min()) / (bolge_metrics[col].max() - bolge_metrics[col].min()) * 100
    
    # Top 5 bölge
    top5_bolge = bolge_metrics.nlargest(5, 'PF Kutu')
    
    fig_radar = go.Figure()
    
    for idx, row in top5_bolge.iterrows():
        fig_radar.add_trace(go.Scatterpolar(
            r=[row['PF Kutu Norm'], row['Toplam Kutu Norm'], row['Ort Pazar Payı Norm'], row['Şehir Sayısı Norm']],
            theta=['PF Kutu', 'Toplam Pazar', 'Ort Pazar Payı', 'Şehir Sayısı'],
            fill='toself',
            name=row['Bölge']
        ))
    
    fig_radar.update_layout(
        polar=dict(
            bgcolor='#0f172a',
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                gridcolor='rgba(148,163,184,0.2)'
            ),
            angularaxis=dict(
                gridcolor='rgba(148,163,184,0.2)'
            )
        ),
        height=500,
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e2e8f0'),
        showlegend=True,
        legend=dict(
            bgcolor="rgba(15,23,42,0.85)",
            bordercolor="rgba(148,163,184,0.3)",
            borderwidth=1
        )
    )
    
    st.plotly_chart(fig_radar, use_container_width=True)
    st.caption("🎯 Her eksen bir metriği temsil eder. Şeklin büyüklüğü o bölgenin genel performansını gösterir.")
    
    st.markdown("---")

import plotly.express as px

if len(investment_df_original) > 0:
    
    # [Document'teki tüm grafikler buraya]
    # ... Treemap, Sunburst, Box Plot, vb ...
    
    #  🌊 1. SANKEY AKIŞ DİYAGRAMI
    st.markdown("### 🌊 Sankey Akış Diyagramı")
    st.caption("💡 Bölge → Strateji → Top Şehirler akışı")
    
    sankey_df = investment_df_original.nlargest(15, 'PF Kutu').copy()
    all_bolge = sankey_df['Bölge'].unique().tolist()
    all_strateji = sankey_df['Yatırım Stratejisi'].unique().tolist()
    all_sehir = sankey_df['Şehir'].tolist()
    nodes = all_bolge + all_strateji + all_sehir
    node_dict = {node: idx for idx, node in enumerate(nodes)}
    
    sources, targets, values, colors_link = [], [], [], []
    for idx, row in sankey_df.iterrows():
        sources.append(node_dict[row['Bölge']])
        targets.append(node_dict[row['Yatırım Stratejisi']])
        values.append(row['PF Kutu'])
        colors_link.append('rgba(59, 130, 246, 0.3)')
    
    for idx, row in sankey_df.iterrows():
        sources.append(node_dict[row['Yatırım Stratejisi']])
        targets.append(node_dict[row['Şehir']])
        values.append(row['PF Kutu'])
        if '🚀' in row['Yatırım Stratejisi']:
            colors_link.append('rgba(239, 68, 68, 0.4)')
        elif '⚡' in row['Yatırım Stratejisi']:
            colors_link.append('rgba(245, 158, 11, 0.4)')
        elif '🛡️' in row['Yatırım Stratejisi']:
            colors_link.append('rgba(16, 185, 129, 0.4)')
        elif '💎' in row['Yatırım Stratejisi']:
            colors_link.append('rgba(139, 92, 246, 0.4)')
        else:
            colors_link.append('rgba(107, 114, 128, 0.4)')
    
    node_colors = []
    for node in nodes:
        if node in all_bolge:
            node_colors.append('#3B82F6')
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
            node_colors.append('#64748B')
    
    fig_sankey = go.Figure(data=[go.Sankey(
        node=dict(pad=15, thickness=20, line=dict(color='white', width=2),
                  label=nodes, color=node_colors),
        link=dict(source=sources, target=targets, value=values, color=colors_link)
    )])
    
    fig_sankey.update_layout(
        height=600,
        font=dict(size=10, color='white'),
        plot_bgcolor='#0f172a',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig_sankey, use_container_width=True)
    
    st.markdown("---")
    
    # 📊 2. FUNNEL CHART
    st.markdown("### 📊 Pazar Penetrasyon Hunisi")
    st.caption("🎯 Toplam Pazar → PF Kutu → Top Performers")
    
    col_f1, col_f2 = st.columns([2, 1])
    
    with col_f1:
        total_market = filtered_toplam_pazar
        total_pf = filtered_pf_toplam
        top_20 = investment_df_original.nlargest(20, 'PF Kutu')['PF Kutu'].sum()
        top_10 = investment_df_original.nlargest(10, 'PF Kutu')['PF Kutu'].sum()
        top_5 = investment_df_original.nlargest(5, 'PF Kutu')['PF Kutu'].sum()
        
        funnel_data = pd.DataFrame({
            'Aşama': ['🌍 Toplam Pazar', '📦 PF Toplam', '🏆 Top 20', '⭐ Top 10', '👑 Top 5'],
            'Değer': [total_market, total_pf, top_20, top_10, top_5]
        })
        
        fig_funnel = go.Figure(go.Funnel(
            y=funnel_data['Aşama'],
            x=funnel_data['Değer'],
            textposition='inside',
            textinfo='value+percent initial',
            marker=dict(color=['#60A5FA', '#3B82F6', '#2563EB', '#1D4ED8', '#1E40AF'])
        ))
        fig_funnel.update_layout(height=500, paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
        st.plotly_chart(fig_funnel, use_container_width=True)
    
    with col_f2:
        st.markdown("#### 📈 Metriks")
        st.metric("🎯 Genel Pay", f"%{(total_pf/total_market*100):.1f}" if total_market>0 else "N/A")
        st.metric("🏆 Top 20", f"%{(top_20/total_pf*100):.1f}" if total_pf>0 else "N/A")
        st.metric("⭐ Top 10", f"%{(top_10/total_pf*100):.1f}" if total_pf>0 else "N/A")
        st.metric("👑 Top 5", f"%{(top_5/total_pf*100):.1f}" if total_pf>0 else "N/A")
    
    st.markdown("---")






# ============================================================================
# YENİ ÖZELLİK 1: TİCARET MÜDÜRÜ PERFORMANS SCORECARD
# ============================================================================
st.markdown("---")
st.markdown("### 👥 Ticaret Müdürü Performans Scorecard")

if len(investment_df_original) > 0:
    mudur_performance = investment_df_original.groupby('Ticaret Müdürü').agg({
        'PF Kutu': 'sum',
        'Toplam Kutu': 'sum',
        'Şehir': 'count',
        'Pazar Payı %': 'mean'
    }).reset_index()
    
    mudur_performance['Ort. Pazar Payı %'] = mudur_performance['Pazar Payı %'].round(1)
    mudur_performance['Toplam Pazar Payı %'] = (
        mudur_performance['PF Kutu'] / mudur_performance['Toplam Kutu'] * 100
    ).round(1)
    mudur_performance = mudur_performance.sort_values('PF Kutu', ascending=False)
    mudur_performance['Rank'] = range(1, len(mudur_performance) + 1)
    
    # Renkli kartlar - MAVİ TONLARI
    col_m1, col_m2, col_m3 = st.columns(3)
    
    top3_mudur = mudur_performance.head(3)
    mavi_gradyanlar = [
        "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",  # 🥇
        "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)",  # 🥈
        "linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)"   # 🥉
    ]
    
    for idx, col in enumerate([col_m1, col_m2, col_m3]):
        if idx < len(top3_mudur):
            row = top3_mudur.iloc[idx]
            rank_emoji = ["🥇", "🥈", "🥉"][idx]
            
            with col:
                st.markdown(f"""
                <div style="
                    background: {mavi_gradyanlar[idx]};
                    padding: 20px;
                    border-radius: 10px;
                    color: white;
                    text-align: center;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                ">
                    <h1>{rank_emoji}</h1>
                    <h3>{row['Ticaret Müdürü']}</h3>
                    <h2>{row['PF Kutu']:,.0f}</h2>
                    <p>PF Kutu | {int(row['Şehir'])} Şehir</p>
                    <h4>%{row['Toplam Pazar Payı %']:.1f} Pazar Payı</h4>
                </div>
                """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Detaylı tablo
    st.markdown("#### 📊 Detaylı Müdür Karşılaştırması")
    
    mudur_display = mudur_performance[['Rank', 'Ticaret Müdürü', 'PF Kutu', 'Toplam Kutu', 
                                       'Şehir', 'Toplam Pazar Payı %']].copy()
    mudur_display['PF Kutu'] = mudur_display['PF Kutu'].apply(lambda x: f"{x:,.0f}")
    mudur_display['Toplam Kutu'] = mudur_display['Toplam Kutu'].apply(lambda x: f"{x:,.0f}")
    mudur_display.columns = ['Sıra', 'Müdür', 'PF Kutu', 'Toplam Pazar', 'Şehir Sayısı', 'Pazar Payı %']
    
    st.dataframe(mudur_display, use_container_width=True, hide_index=True)
    
    # Müdür karşılaştırma grafiği
    col_mg1, col_mg2 = st.columns(2)
    
    with col_mg1:
        st.markdown("##### 📈 Müdür Bazlı PF Kutu")
        fig_mudur = px.bar(
            mudur_performance,
            x='Ticaret Müdürü',
            y='PF Kutu',
            color='Toplam Pazar Payı %',
            color_continuous_scale='Blues',
            text='PF Kutu'
        )
        fig_mudur.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig_mudur.update_layout(
            height=400,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(tickangle=-45)
        )
        st.plotly_chart(fig_mudur, use_container_width=True)
    
    with col_mg2:
        st.markdown("##### 🎯 Pazar Payı Karşılaştırması")
        fig_mudur_pay = px.scatter(
            mudur_performance,
            x='Şehir',
            y='Toplam Pazar Payı %',
            size='PF Kutu',
            color='Ticaret Müdürü',
            hover_name='Ticaret Müdürü',
            hover_data={'PF Kutu': ':,.0f', 'Şehir': True}
        )
        fig_mudur_pay.update_layout(
            height=400,
            plot_bgcolor='#0f172a',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_mudur_pay, use_container_width=True)

# ============================================================================
# YENİ ÖZELLİK 2: BÜYÜK FIRSATLAR - AKSIYONA DÖNÜŞTÜR (KIRMIZI)
# ============================================================================
st.markdown("---")
st.markdown("### 💎 Büyük Fırsatlar - Aksiyon Gerekli!")
st.caption("🎯 Büyük pazar + Düşük payımız = En yüksek ROI potansiyeli")

if len(investment_df_original) > 0:
    investment_df_original['Büyüme Potansiyeli Kutu'] = (
        investment_df_original['Toplam Kutu'] - investment_df_original['PF Kutu']
    )
    
    # Fırsat kriterleri
    median_pazar = investment_df_original['Toplam Kutu'].median()
    
    firsatlar_df = investment_df_original[
        (investment_df_original['Toplam Kutu'] > median_pazar) &
        (investment_df_original['Pazar Payı %'] < 10) &
        (investment_df_original['Büyüme Potansiyeli Kutu'] > 50000)
    ].copy()
    
    if len(firsatlar_df) > 0:
        firsatlar_df = firsatlar_df.sort_values('Büyüme Potansiyeli Kutu', ascending=False)
        
        st.error(f"🚨 **{len(firsatlar_df)} şehirde büyük fırsat tespit edildi!**")
        
        # Top 10 fırsat
        top_firsatlar = firsatlar_df.head(10)
        
        # GRAFİK ÜST SIRA - TAM GENİŞLİK
        st.markdown("##### 🗺️ Büyük Fırsatlar Haritası")
        
        fig_firsat = px.scatter(
            top_firsatlar,
            x='Toplam Kutu',
            y='Pazar Payı %',
            size='Büyüme Potansiyeli Kutu',
            color='Bölge',
            text='Şehir',
            hover_data={
                'PF Kutu': ':,.0f',
                'Toplam Kutu': ':,.0f',
                'Büyüme Potansiyeli Kutu': ':,.0f'
            },
            size_max=60
        )
        
        fig_firsat.update_traces(
            textposition='top center',
            textfont=dict(size=10, color='white'),
            marker=dict(line=dict(width=2, color='rgba(255,255,255,0.5)'))
        )
        
        fig_firsat.update_layout(
            height=500,
            plot_bgcolor='#0f172a',
            paper_bgcolor='rgba(0,0,0,0)',
            title="🎯 Fırsat Şehirler - Pazar Büyük, Payımız Düşük",
            xaxis_title="Pazar Büyüklüğü (Toplam Kutu)",
            yaxis_title="Bizim Pazar Payımız (%)",
            font=dict(color='white')
        )
        
        st.plotly_chart(fig_firsat, use_container_width=True)
        
        st.markdown("---")
        
        # AKSİYON ÖNERİLERİ ALT SIRA - KARTLAR
        st.markdown("#### 🎯 Aksiyon Önerileri")
        
        # 3'lü satırlar halinde göster
        for i in range(0, min(9, len(top_firsatlar)), 3):
            cols = st.columns(3)
            for j, col in enumerate(cols):
                if i + j < len(top_firsatlar):
                    row = top_firsatlar.iloc[i + j]
                    potential_revenue = row['Büyüme Potansiyeli Kutu']
                    
                    with col:
                        st.markdown(f"""
                        <div style="
                            background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%);
                            padding: 15px;
                            border-radius: 8px;
                            margin-bottom: 10px;
                            color: white;
                            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                        ">
                            <h4>🎯 {row['Şehir']}</h4>
                            <p>📍 Bölge: {row['Bölge']}</p>
                            <p>💰 Potansiyel: <b>{potential_revenue:,.0f} kutu</b></p>
                            <p>📊 Mevcut Pay: <b>%{row['Pazar Payı %']:.1f}</b></p>
                            <hr style="border-color: rgba(255,255,255,0.3);">
                            <small>✅ Acil ekip takviyesi gerekli</small>
                        </div>
                        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Detaylı tablo
        st.markdown("##### 📋 Tüm Fırsatlar - Detaylı Liste")
        firsat_display = firsatlar_df[['Şehir', 'Bölge', 'PF Kutu', 'Toplam Kutu', 
                                        'Pazar Payı %', 'Büyüme Potansiyeli Kutu', 
                                        'Ticaret Müdürü']].copy()
        firsat_display['PF Kutu'] = firsat_display['PF Kutu'].apply(lambda x: f"{x:,.0f}")
        firsat_display['Toplam Kutu'] = firsat_display['Toplam Kutu'].apply(lambda x: f"{x:,.0f}")
        firsat_display['Büyüme Potansiyeli Kutu'] = firsat_display['Büyüme Potansiyeli Kutu'].apply(lambda x: f"{x:,.0f}")
        firsat_display.columns = ['Şehir', 'Bölge', 'PF Kutu', 'Toplam Pazar', 'Pazar Payı %', 'Potansiyel', 'Sorumlu Müdür']
        
        st.dataframe(firsat_display, use_container_width=True, hide_index=True)
    else:
        st.success("✅ Şu anda büyük fırsat kategorisinde şehir yok!")

# ============================================================================
# YENİ ÖZELLİK 3: SIFIR SATIŞ OLAN ŞEHİRLER - UYARI
# ============================================================================
st.markdown("---")
st.markdown("### ⚠️ Sıfır Satış Olan Şehirler")

if len(investment_df_original) > 0:
    sifir_satis = investment_df_original[investment_df_original['PF Kutu'] == 0].copy()
    
    if len(sifir_satis) > 0:
        st.error(f"🚨 **{len(sifir_satis)} şehirde hiç satış YOK!**")
        
        col_sif1, col_sif2 = st.columns([1, 2])
        
        with col_sif1:
            st.markdown("##### 📋 Liste")
            for _, row in sifir_satis.iterrows():
                pazar = row['Toplam Kutu']
                if pazar > 0:
                    st.warning(f"🔴 **{row['Şehir']}** - Pazar: {pazar:,.0f}")
                else:
                    st.info(f"⚪ **{row['Şehir']}** - Pazar verisi yok")
        
        with col_sif2:
            st.markdown("##### 🗺️ Coğrafi Dağılım")
            sifir_bolge = sifir_satis.groupby('Bölge').size().reset_index()
            sifir_bolge.columns = ['Bölge', 'Sıfır Satış Şehir Sayısı']
            
            fig_sifir = px.bar(
                sifir_bolge,
                x='Bölge',
                y='Sıfır Satış Şehir Sayısı',
                color='Sıfır Satış Şehir Sayısı',
                color_continuous_scale='Reds',
                text='Sıfır Satış Şehir Sayısı'
            )
            fig_sifir.update_traces(textposition='outside')
            fig_sifir.update_layout(
                height=350,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(tickangle=-45)
            )
            st.plotly_chart(fig_sifir, use_container_width=True)
    else:
        st.success("✅ Harika! Her şehirde satış var!")

# ============================================================================
# YENİ ÖZELLİK 4: KONSANTRASYON RİSKİ ANALİZİ
# ============================================================================
st.markdown("---")
st.markdown("### 📊 Konsantrasyon Risk Analizi")
st.caption("💡 Pareto prensibi: Satışların ne kadarı az sayıda şehirden geliyor?")

if len(investment_df_original) > 0:
    total_pf = investment_df_original['PF Kutu'].sum()
    
    # Kümülatif hesaplama
    sorted_df = investment_df_original.sort_values('PF Kutu', ascending=False).copy()
    sorted_df['Kümülatif PF'] = sorted_df['PF Kutu'].cumsum()
    sorted_df['Kümülatif %'] = (sorted_df['Kümülatif PF'] / total_pf * 100).round(1)
    sorted_df['Şehir Sırası'] = range(1, len(sorted_df) + 1)
    
    # 80/20 kuralı - %80 satış kaç şehirden?
    sehir_80 = sorted_df[sorted_df['Kümülatif %'] <= 80]['Şehir Sırası'].max()
    
    col_kon1, col_kon2, col_kon3 = st.columns(3)
    
    with col_kon1:
        st.metric(
            "🎯 Top 10 Şehir",
            f"%{sorted_df.head(10)['Kümülatif %'].iloc[-1]:.1f}",
            delta="Toplam satıştan"
        )
    
    with col_kon2:
        st.metric(
            "📊 %80 Satış",
            f"{sehir_80} şehirden",
            delta="geliyor"
        )
    
    with col_kon3:
        risk_seviye = "🟢 Düşük" if sehir_80 > 20 else "🟡 Orta" if sehir_80 > 10 else "🔴 Yüksek"
        st.metric(
            "⚠️ Risk Seviyesi",
            risk_seviye
        )
    
    # Pareto grafiği
    fig_pareto = go.Figure()
    
    # Bar chart (PF Kutu) - Mavi tonları
    fig_pareto.add_trace(go.Bar(
        x=sorted_df.head(30)['Şehir'],
        y=sorted_df.head(30)['PF Kutu'],
        name='PF Kutu',
        marker_color='#3B82F6',
        yaxis='y'
    ))
    
    # Line chart (Kümülatif %) - Koyu mavi
    fig_pareto.add_trace(go.Scatter(
        x=sorted_df.head(30)['Şehir'],
        y=sorted_df.head(30)['Kümülatif %'],
        name='Kümülatif %',
        mode='lines+markers',
        marker=dict(size=8, color='#1E40AF'),
        line=dict(width=3, color='#1E40AF'),
        yaxis='y2'
    ))
    
    # 80% çizgisi
    fig_pareto.add_hline(
        y=80,
        line_dash="dash",
        line_color="#EF4444",
        annotation_text="80% hedefi",
        yref='y2'
    )
    
    # Layout ayarları
    fig_pareto.update_layout(
        title="Pareto Analizi: Hangi şehirler %80 satışı yapıyor?",
        height=500,
        plot_bgcolor='#0f172a',
        paper_bgcolor='rgba(0,0,0,0)',
        showlegend=True,
        font=dict(color='white')
    )
    
    # X axis
    fig_pareto.update_xaxes(
        tickangle=-45,
        title='Şehir'
    )
    
    # Y axis (sol) - basitleştirilmiş
    fig_pareto.update_yaxes(
        title='PF Kutu'
    )
    
    # Y2 axis (sağ) - ayrı layout update ile
    fig_pareto.update_layout(
        yaxis2=dict(
            title='Kümülatif %',
            overlaying='y',
            side='right',
            range=[0, 100]
        ),
        legend=dict(
            x=0.7,
            y=0.95,
            bgcolor='rgba(15,23,42,0.9)',
            bordercolor='rgba(148,163,184,0.3)',
            borderwidth=1
        )
    )
    
    st.plotly_chart(fig_pareto, use_container_width=True)
    
    # Yorum
    if sehir_80 <= 10:
        st.warning(f"""
        ⚠️ **Yüksek Konsantrasyon Riski!**
        
        Satışların %80'i sadece {sehir_80} şehirden geliyor. Bu şehirlerde bir sorun olursa 
        toplam satışlar ciddi etkilenebilir. Long-tail stratejisi geliştirmeniz önerilir.
        """)
    else:
        st.success(f"""
        ✅ **Dengeli Dağılım**
        
        Satışlar {sehir_80} şehre yayılmış durumda. Risk dengeli.
        """)

# ============================================================================
# YENİ ÖZELLİK 5: AKSİYON PLANI OLUŞTURUCU
# ============================================================================
st.markdown("---")
st.markdown("### 📋 Otomatik Aksiyon Planı")
st.caption("🤖 AI destekli öneriler - Veriye dayalı aksiyonlar")

if len(investment_df_original) > 0:
    
    st.markdown("#### 🎯 Öncelikli 10 Aksiyon")
    
    aksiyonlar = []
    
    # 1. En büyük fırsatlar
    top_firsatlar = investment_df_original[
        (investment_df_original['Pazar Payı %'] < 5) & 
        (investment_df_original['Toplam Kutu'] > investment_df_original['Toplam Kutu'].median())
    ].nlargest(3, 'Toplam Kutu')
    
    for idx, row in top_firsatlar.iterrows():
        aksiyonlar.append({
            'Öncelik': '🔴 Kritik',
            'Aksiyon': f"{row['Şehir']}'de agresif yatırım",
            'Neden': f"Pazar büyük ({row['Toplam Kutu']:,.0f}) ama payımız %{row['Pazar Payı %']:.1f}",
            'Sorumlu': row['Ticaret Müdürü'],
            'Potansiyel': f"+{(row['Toplam Kutu'] - row['PF Kutu']):,.0f} kutu"
        })
    
    # 2. Sıfır satış olanlar
    sifir_satis_top = investment_df_original[
        investment_df_original['PF Kutu'] == 0
    ].nlargest(2, 'Toplam Kutu')
    
    for idx, row in sifir_satis_top.iterrows():
        aksiyonlar.append({
            'Öncelik': '🟠 Yüksek',
            'Aksiyon': f"{row['Şehir']}'ye giriş yap",
            'Neden': f"Hiç satış yok ama pazar var ({row['Toplam Kutu']:,.0f})",
            'Sorumlu': row['Ticaret Müdürü'],
            'Potansiyel': f"+{row['Toplam Kutu']:,.0f} kutu"
        })
    
    # 3. Düşük performanslı müdürler
    mudur_perf = investment_df_original.groupby('Ticaret Müdürü').agg({
        'PF Kutu': 'sum',
        'Toplam Kutu': 'sum'
    })
    mudur_perf['Pay %'] = mudur_perf['PF Kutu'] / mudur_perf['Toplam Kutu'] * 100
    dusuk_mudur = mudur_perf[mudur_perf['Pay %'] < 5].sort_values('Pay %').head(2)
    
    for mudur, row in dusuk_mudur.iterrows():
        aksiyonlar.append({
            'Öncelik': '🟡 Orta',
            'Aksiyon': f"{mudur} ile performans görüşmesi",
            'Neden': f"Genel pazar payı %{row['Pay %']:.1f} - ortalamanın altında",
            'Sorumlu': 'Bölge Müdürü',
            'Potansiyel': 'Ekip motivasyonu artışı'
        })
    
    # DataFrame'e çevir ve göster
    aksiyon_df = pd.DataFrame(aksiyonlar)
    
    # Renkli gösterim
    for idx, aksiyon in enumerate(aksiyonlar, 1):
        if aksiyon['Öncelik'] == '🔴 Kritik':
            color = "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)"
        elif aksiyon['Öncelik'] == '🟠 Yüksek':
            color = "linear-gradient(135deg, #fa709a 0%, #fee140 100%)"
        else:
            color = "linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)"
        
        st.markdown(f"""
        <div style="
            background: {color};
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 10px;
            color: white;
        ">
            <h4>{idx}. {aksiyon['Aksiyon']}</h4>
            <p><b>Öncelik:</b> {aksiyon['Öncelik']}</p>
            <p><b>Neden:</b> {aksiyon['Neden']}</p>
            <p><b>Sorumlu:</b> {aksiyon['Sorumlu']}</p>
            <p><b>Potansiyel Kazanç:</b> {aksiyon['Potansiyel']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Excel export
    st.markdown("---")
    
    from io import BytesIO
    output_aksiyon = BytesIO()
    with pd.ExcelWriter(output_aksiyon, engine='openpyxl') as writer:
        aksiyon_df.to_excel(writer, sheet_name='Aksiyon Planı', index=False)
    
    st.download_button(
        label="📥 Aksiyon Planını İndir (Excel)",
        data=output_aksiyon.getvalue(),
        file_name="aksiyon_plani.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


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
    if len(investment_df_original) > 0:
        st.markdown("##### 📄 PDF Özet Raporu")
        st.caption("BCG Matrix ve temel metrikleri içeren özet rapor")
        
        from io import BytesIO
        from datetime import datetime
        
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
            from reportlab.lib.units import cm
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            
            # PDF için veri hazırla
            top10_summary = investment_df_original.nlargest(10, 'PF Kutu')[['Şehir', 'Bölge', 'PF Kutu', 'Pazar Payı %']]
            bolge_summary = investment_df_original.groupby('Bölge').agg({
                'PF Kutu': 'sum',
                'Pazar Payı %': 'mean'
            }).sort_values('PF Kutu', ascending=False).head(5).reset_index()
            strateji_summary = investment_df_original.groupby('Yatırım Stratejisi').agg({
                'Şehir': 'count',
                'PF Kutu': 'sum'
            }).reset_index()
            
            # PDF oluştur
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
            elements = []
            styles = getSampleStyleSheet()
            
            # Başlık
            title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#1E40AF'), spaceAfter=30, alignment=1)
            elements.append(Paragraph("TÜRKİYE SATIŞ ANALİZİ - ÖZET RAPOR", title_style))
            elements.append(Paragraph(f"Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}", styles['Normal']))
            elements.append(Spacer(1, 0.5*cm))
            
            # Genel Özet
            elements.append(Paragraph("GENEL ÖZET", styles['Heading2']))
            genel_data = [
                ['Metrik', 'Değer'],
                ['Toplam PF Kutu', f'{filtered_pf_toplam:,.0f}'],
                ['Toplam Pazar', f'{filtered_toplam_pazar:,.0f}'],
                ['Genel Pazar Payı', f'%{genel_pazar_payi:.1f}'],
                ['Aktif Şehir Sayısı', f'{filtered_aktif_sehir}']
            ]
            genel_table = Table(genel_data, colWidths=[8*cm, 8*cm])
            genel_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(genel_table)
            elements.append(Spacer(1, 1*cm))
            
            # Yatırım Stratejisi Dağılımı
            elements.append(Paragraph("YATIRIM STRATEJİSİ DAĞILIMI", styles['Heading2']))
            strateji_data = [['Strateji', 'Şehir Sayısı', 'PF Kutu']]
            for idx, row in strateji_summary.iterrows():
                strateji_data.append([
                    row['Yatırım Stratejisi'],
                    f"{int(row['Şehir'])}",
                    f"{row['PF Kutu']:,.0f}"
                ])
            strateji_table = Table(strateji_data, colWidths=[8*cm, 4*cm, 4*cm])
            strateji_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(strateji_table)
            elements.append(Spacer(1, 1*cm))
            
            # Top 5 Bölge
            elements.append(Paragraph("TOP 5 BÖLGE", styles['Heading2']))
            bolge_data = [['#', 'Bölge', 'PF Kutu', 'Ort. Pazar Payı']]
            for idx, row in bolge_summary.iterrows():
                bolge_data.append([
                    f"{idx+1}",
                    row['Bölge'],
                    f"{row['PF Kutu']:,.0f}",
                    f"%{row['Pazar Payı %']:.1f}"
                ])
            bolge_table = Table(bolge_data, colWidths=[1.5*cm, 6*cm, 4.5*cm, 4*cm])
            bolge_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10B981')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(bolge_table)
            elements.append(Spacer(1, 1*cm))
            
            # Top 10 Şehir
            elements.append(Paragraph("TOP 10 ŞEHİR", styles['Heading2']))
            sehir_data = [['#', 'Şehir', 'Bölge', 'PF Kutu', 'Pazar Payı']]
            for idx, row in top10_summary.iterrows():
                sehir_data.append([
                    f"{idx+1}",
                    row['Şehir'],
                    row['Bölge'],
                    f"{row['PF Kutu']:,.0f}",
                    f"%{row['Pazar Payı %']:.1f}"
                ])
            sehir_table = Table(sehir_data, colWidths=[1*cm, 4*cm, 4*cm, 4*cm, 3*cm])
            sehir_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F59E0B')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(sehir_table)
            
            # PDF'i oluştur
            doc.build(elements)
            pdf_bytes = buffer.getvalue()
            buffer.close()
            
            st.download_button(
                label="📄 PDF Rapor İndir",
                data=pdf_bytes,
                file_name=f"turkiye_satis_raporu_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                help="Detaylı PDF raporu - tablolar ve grafiklerle"
            )
            
        except ImportError:
            # reportlab yoksa basit text raporu sun
            st.warning("⚠️ PDF özelliği için reportlab kütüphanesi gerekli. Text raporu indirilebilir:")
            
            top10_summary = investment_df_original.nlargest(10, 'PF Kutu')[['Şehir', 'Bölge', 'PF Kutu', 'Pazar Payı %']]
            bolge_summary = investment_df_original.groupby('Bölge').agg({
                'PF Kutu': 'sum',
                'Pazar Payı %': 'mean'
            }).sort_values('PF Kutu', ascending=False).head(5).reset_index()
            strateji_summary = investment_df_original.groupby('Yatırım Stratejisi').agg({
                'Şehir': 'count',
                'PF Kutu': 'sum'
            }).reset_index()
            
            pdf_content = f"""
╔══════════════════════════════════════════════════════════════╗
║           TÜRKİYE SATIŞ ANALİZİ - ÖZET RAPOR                ║
║              Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}                      ║
╚══════════════════════════════════════════════════════════════╝

📊 GENEL ÖZET
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Toplam PF Kutu: {filtered_pf_toplam:,.0f}
• Toplam Pazar: {filtered_toplam_pazar:,.0f}
• Genel Pazar Payı: %{genel_pazar_payi:.1f}
• Aktif Şehir Sayısı: {filtered_aktif_sehir}

🎯 YATIRIM STRATEJİSİ DAĞILIMI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            
            for idx, row in strateji_summary.iterrows():
                pdf_content += f"• {row['Yatırım Stratejisi']}: {int(row['Şehir'])} şehir - {row['PF Kutu']:,.0f} PF Kutu\n"
            
            pdf_content += f"""
🏆 TOP 5 BÖLGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            
            for idx, row in bolge_summary.iterrows():
                pdf_content += f"{idx+1}. {row['Bölge']}: {row['PF Kutu']:,.0f} PF Kutu (Pazar Payı: %{row['Pazar Payı %']:.1f})\n"
            
            pdf_content += f"""
🌟 TOP 10 ŞEHİR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            
            for idx, row in top10_summary.iterrows():
                pdf_content += f"{idx+1}. {row['Şehir']} ({row['Bölge']}): {row['PF Kutu']:,.0f} - Pazar Payı: %{row['Pazar Payı %']:.1f}\n"
            
            pdf_content += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Bu rapor Türkiye Satış Haritası uygulaması tarafından oluşturulmuştur.
"""
            
            st.download_button(
                label="📄 Text Rapor İndir",
                data=pdf_content.encode('utf-8'),
                file_name=f"turkiye_satis_raporu_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain",
                help="Genel özet ve top performansları içeren rapor"
            )











