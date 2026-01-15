"""
🎯 GELİŞMİŞ TİCARİ PORTFÖY ANALİZ SİSTEMİ
Territory × Zaman × Coğrafi Analiz Platformu

Özellikler:
- Türkiye haritası üzerinde interaktif görselleştirme
- Territory bazlı performans ve yatırım stratejisi analizi
- Detaylı zaman serisi analizi ve trend tahminleri
- BCG Matrix ve stratejik konumlandırma
- Manager performans scorecards
- Otomatik aksiyon planı oluşturma
- Excel ve PDF rapor çıktıları
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import warnings
from io import BytesIO
import json

warnings.filterwarnings("ignore")

# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(
    page_title="Ticari Portföy Analizi",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# CUSTOM CSS - MODERN & PROFESSIONAL
# =============================================================================
st.markdown("""
<style>
    .main-header {
        font-size: 2.8rem;
        font-weight: bold;
        text-align: center;
        padding: 1.5rem 0;
        margin-bottom: 2rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        color: white;
        text-align: center;
        transition: transform 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 3.5rem;
        padding: 0 2rem;
        font-size: 1.1rem;
        font-weight: 600;
        border-radius: 8px;
        background-color: white;
        transition: all 0.3s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #e9ecef;
    }
    
    .territory-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #3B82F6;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .priority-critical {
        background: linear-gradient(135deg, #DC2626 0%, #991B1B 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    
    .priority-high {
        background: linear-gradient(135deg, #EA580C 0%, #C2410C 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    
    .priority-medium {
        background: linear-gradient(135deg, #0891B2 0%, #0E7490 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def safe_divide(a, b):
    """Güvenli bölme işlemi"""
    return np.where(b != 0, a / b, 0)

def format_number(x):
    """Sayı formatlama"""
    if pd.isna(x):
        return 0
    return round(float(x), 2)

def get_product_columns(product):
    """Ürün kolonlarını döndür"""
    product_map = {
        "TROCMETAM": {"pf": "TROCMETAM", "rakip": "DIGER TROCMETAM"},
        "CORTIPOL": {"pf": "CORTIPOL", "rakip": "DIGER CORTIPOL"},
        "DEKSAMETAZON": {"pf": "DEKSAMETAZON", "rakip": "DIGER DEKSAMETAZON"},
        "PF IZOTONIK": {"pf": "PF IZOTONIK", "rakip": "DIGER IZOTONIK"}
    }
    return product_map.get(product, {"pf": product, "rakip": f"DIGER {product}"})

# =============================================================================
# TÜRKIYE HARİTASI İÇİN ŞEHİR EŞLEŞTİRME
# =============================================================================
CITY_NORMALIZE_MAP = {
    "AGRI": "AĞRI",
    "BARTIN": "BARTIN",
    "BINGOL": "BİNGÖL",
    "DUZCE": "DÜZCE",
    "ELAZIG": "ELAZĞ",
    "ESKISEHIR": "ESKİŞEHİR",
    "GUMUSHANE": "GÜMÜŞHANE",
    "HAKKARI": "HAKKARİ",
    "ISTANBUL": "İSTANBUL",
    "IZMIR": "İZMİR",
    "IGDIR": "IĞDIR",
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
    "CORUM": "ÇORUM",
    "K. MARAS": "KAHRAMANMARAŞ"
}

REGION_COLORS = {
    "MARMARA": "#0EA5E9",
    "BATI ANADOLU": "#14B8A6",
    "EGE": "#FCD34D",
    "İÇ ANADOLU": "#F59E0B",
    "GÜNEY DOĞU ANADOLU": "#E07A5F",
    "KUZEY ANADOLU": "#059669",
    "KARADENİZ": "#059669",
    "AKDENİZ": "#8B5CF6",
    "DOĞU ANADOLU": "#7C3AED",
    "DİĞER": "#64748B"
}

def normalize_city_name(name):
    """Şehir isimlerini normalize et"""
    if pd.isna(name):
        return None
    
    name = str(name).upper().strip()
    
    # Türkçe karakter dönüşümü
    tr_map = {
        "İ": "I", "Ğ": "G", "Ü": "U",
        "Ş": "S", "Ö": "O", "Ç": "C"
    }
    
    for k, v in tr_map.items():
        name = name.replace(k, v)
    
    # Eşleştirme haritasını kontrol et
    return CITY_NORMALIZE_MAP.get(name, name)

# =============================================================================
# DATA LOADING
# =============================================================================

@st.cache_data
def load_excel_data(file):
    """Excel dosyasını yükle ve ön işleme yap"""
    try:
        df = pd.read_excel(file)
        
        # Tarih sütununu datetime'a çevir
        if 'DATE' in df.columns:
            df['DATE'] = pd.to_datetime(df['DATE'])
            df['YIL_AY'] = df['DATE'].dt.strftime('%Y-%m')
            df['AY'] = df['DATE'].dt.month
            df['YIL'] = df['DATE'].dt.year
            df['QUARTER'] = df['DATE'].dt.quarter
            df['HAFTA'] = df['DATE'].dt.isocalendar().week
        
        # Standartlaştırma
        if 'TERRITORIES' in df.columns:
            df['TERRITORIES'] = df['TERRITORIES'].str.upper().str.strip()
        if 'CITY' in df.columns:
            df['CITY'] = df['CITY'].str.strip()
            df['CITY_NORMALIZED'] = df['CITY'].apply(normalize_city_name)
        if 'REGION' in df.columns:
            df['REGION'] = df['REGION'].str.upper().str.strip()
        if 'MANAGER' in df.columns:
            df['MANAGER'] = df['MANAGER'].str.upper().str.strip()
        
        return df
    except Exception as e:
        st.error(f"Veri yükleme hatası: {str(e)}")
        return None

@st.cache_resource
def load_turkey_geojson():
    """Türkiye GeoJSON haritasını yükle"""
    # Not: Gerçek uygulamada turkey.geojson dosyası gerekli
    # Bu örnek için basit bir yapı döndürüyoruz
    return None

# =============================================================================
# ANALYSIS FUNCTIONS - TERRITORY PERFORMANCE
# =============================================================================

def calculate_territory_performance(df, product, start_date=None, end_date=None):
    """Territory bazlı performans analizi"""
    df_filtered = df.copy()
    
    # Tarih filtreleme
    if start_date and end_date and 'DATE' in df.columns:
        df_filtered = df_filtered[
            (df_filtered['DATE'] >= start_date) & 
            (df_filtered['DATE'] <= end_date)
        ]
    
    cols = get_product_columns(product)
    
    # Territory bazlı toplam
    agg_dict = {}
    if cols['pf'] in df_filtered.columns:
        agg_dict[cols['pf']] = 'sum'
    if cols['rakip'] in df_filtered.columns:
        agg_dict[cols['rakip']] = 'sum'
    
    group_cols = ['TERRITORIES']
    if 'REGION' in df_filtered.columns:
        group_cols.append('REGION')
    if 'CITY' in df_filtered.columns:
        group_cols.append('CITY')
    if 'MANAGER' in df_filtered.columns:
        group_cols.append('MANAGER')
    
    terr_perf = df_filtered.groupby(group_cols).agg(agg_dict).reset_index()
    
    terr_perf.columns = list(terr_perf.columns[:len(group_cols)]) + ['PF_Satis', 'Rakip_Satis']
    terr_perf['Toplam_Pazar'] = terr_perf['PF_Satis'] + terr_perf['Rakip_Satis']
    terr_perf['Pazar_Payi_%'] = safe_divide(terr_perf['PF_Satis'], terr_perf['Toplam_Pazar']) * 100
    
    # Toplam içindeki ağırlık
    total_pf = terr_perf['PF_Satis'].sum()
    terr_perf['Agirlik_%'] = safe_divide(terr_perf['PF_Satis'], total_pf) * 100
    
    # Göreceli pazar payı
    terr_perf['Goreceli_Pazar_Payi'] = safe_divide(terr_perf['PF_Satis'], terr_perf['Rakip_Satis'])
    
    # Büyüme potansiyeli
    terr_perf['Buyume_Potansiyeli'] = terr_perf['Toplam_Pazar'] - terr_perf['PF_Satis']
    
    return terr_perf.sort_values('PF_Satis', ascending=False)

# =============================================================================
# TIME SERIES ANALYSIS
# =============================================================================

def calculate_time_series(df, product, territory=None, frequency='M'):
    """
    Zaman serisi analizi
    frequency: 'D' (günlük), 'W' (haftalık), 'M' (aylık), 'Q' (çeyrek)
    """
    cols = get_product_columns(product)
    
    df_filtered = df.copy()
    if territory and territory != "TÜMÜ":
        df_filtered = df_filtered[df_filtered['TERRITORIES'] == territory]
    
    # Frekansa göre gruplama
    if frequency == 'D':
        time_col = df_filtered['DATE']
        group_col = df_filtered['DATE'].dt.strftime('%Y-%m-%d')
    elif frequency == 'W':
        time_col = df_filtered['DATE']
        group_col = df_filtered['DATE'].dt.strftime('%Y-W%U')
    elif frequency == 'Q':
        time_col = df_filtered['DATE']
        group_col = df_filtered['DATE'].dt.to_period('Q').astype(str)
    else:  # Monthly
        time_col = df_filtered['DATE']
        group_col = df_filtered['YIL_AY']
    
    # Gruplama ve toplam
    time_series = df_filtered.groupby(group_col).agg({
        cols['pf']: 'sum',
        cols['rakip']: 'sum'
    }).reset_index().sort_values(group_col)
    
    time_series.columns = ['Period', 'PF_Satis', 'Rakip_Satis']
    time_series['Toplam_Pazar'] = time_series['PF_Satis'] + time_series['Rakip_Satis']
    time_series['Pazar_Payi_%'] = safe_divide(time_series['PF_Satis'], time_series['Toplam_Pazar']) * 100
    
    # Büyüme oranları
    time_series['PF_Buyume_%'] = time_series['PF_Satis'].pct_change() * 100
    time_series['Rakip_Buyume_%'] = time_series['Rakip_Satis'].pct_change() * 100
    time_series['Goreceli_Buyume_%'] = time_series['PF_Buyume_%'] - time_series['Rakip_Buyume_%']
    
    # Hareketli ortalamalar
    window_3 = min(3, len(time_series))
    window_6 = min(6, len(time_series))
    time_series['MA_3'] = time_series['PF_Satis'].rolling(window=window_3, min_periods=1).mean()
    time_series['MA_6'] = time_series['PF_Satis'].rolling(window=window_6, min_periods=1).mean()
    
    # Trend (basit doğrusal)
    if len(time_series) > 2:
        x = np.arange(len(time_series))
        y = time_series['PF_Satis'].values
        z = np.polyfit(x, y, 1)
        time_series['Trend'] = np.poly1d(z)(x)
    else:
        time_series['Trend'] = time_series['PF_Satis']
    
    return time_series

def calculate_period_comparison(df, product, territory=None):
    """Dönemsel karşılaştırma analizi"""
    cols = get_product_columns(product)
    
    df_filtered = df.copy()
    if territory and territory != "TÜMÜ":
        df_filtered = df_filtered[df_filtered['TERRITORIES'] == territory]
    
    max_date = df_filtered['DATE'].max()
    
    # Farklı dönemleri tanımla
    periods = {
        'Son_7_Gun': max_date - timedelta(days=7),
        'Son_30_Gun': max_date - timedelta(days=30),
        'Son_3_Ay': max_date - pd.DateOffset(months=3),
        'Son_6_Ay': max_date - pd.DateOffset(months=6),
        'YTD': pd.Timestamp(year=max_date.year, month=1, day=1),
        'Tum_Donem': df_filtered['DATE'].min()
    }
    
    results = {}
    for period_name, start_date in periods.items():
        period_data = df_filtered[df_filtered['DATE'] >= start_date]
        pf_total = period_data[cols['pf']].sum()
        rakip_total = period_data[cols['rakip']].sum()
        total_market = pf_total + rakip_total
        market_share = (pf_total / total_market * 100) if total_market > 0 else 0
        
        results[period_name] = {
            'PF_Satis': pf_total,
            'Rakip_Satis': rakip_total,
            'Toplam_Pazar': total_market,
            'Pazar_Payi_%': market_share
        }
    
    return results

# =============================================================================
# BCG MATRIX & INVESTMENT STRATEGY
# =============================================================================

def calculate_bcg_matrix(df, product, start_date=None, end_date=None):
    """BCG Matrix kategorileri hesapla"""
    terr_perf = calculate_territory_performance(df, product, start_date, end_date)
    
    cols = get_product_columns(product)
    df_sorted = df.sort_values('DATE')
    
    # İlk yarı vs ikinci yarı karşılaştırması
    mid_point = len(df_sorted) // 2
    first_half = df_sorted.iloc[:mid_point].groupby('TERRITORIES')[cols['pf']].sum()
    second_half = df_sorted.iloc[mid_point:].groupby('TERRITORIES')[cols['pf']].sum()
    
    growth_rate = {}
    for terr in first_half.index:
        if terr in second_half.index and first_half[terr] > 0:
            growth_rate[terr] = ((second_half[terr] - first_half[terr]) / first_half[terr]) * 100
        else:
            growth_rate[terr] = 0
    
    terr_perf['Pazar_Buyume_%'] = terr_perf['TERRITORIES'].map(growth_rate).fillna(0)
    
    # BCG Sınıflandırma
    median_share = terr_perf['Goreceli_Pazar_Payi'].median()
    median_growth = terr_perf['Pazar_Buyume_%'].median()
    
    def assign_bcg(row):
        if row['Goreceli_Pazar_Payi'] >= median_share:
            if row['Pazar_Buyume_%'] >= median_growth:
                return "⭐ Star"
            else:
                return "🐄 Cash Cow"
        else:
            if row['Pazar_Buyume_%'] >= median_growth:
                return "❓ Question Mark"
            else:
                return "🐶 Dog"
    
    terr_perf['BCG_Kategori'] = terr_perf.apply(assign_bcg, axis=1)
    
    return terr_perf

def calculate_investment_strategy(bcg_df):
    """Gelişmiş yatırım stratejisi hesapla"""
    bcg_df = bcg_df.copy()
    
    # Segment tanımlama
    try:
        bcg_df['Pazar_Buyuklugu_Segment'] = pd.qcut(
            bcg_df['Toplam_Pazar'], 
            q=3, 
            labels=['Küçük', 'Orta', 'Büyük'],
            duplicates='drop'
        )
    except:
        bcg_df['Pazar_Buyuklugu_Segment'] = 'Orta'
    
    try:
        bcg_df['Pazar_Payi_Segment'] = pd.qcut(
            bcg_df['Pazar_Payi_%'], 
            q=3, 
            labels=['Düşük', 'Orta', 'Yüksek'],
            duplicates='drop'
        )
    except:
        bcg_df['Pazar_Payi_Segment'] = 'Orta'
    
    try:
        bcg_df['Buyume_Potansiyeli_Segment'] = pd.qcut(
            bcg_df['Buyume_Potansiyeli'],
            q=3,
            labels=['Düşük', 'Orta', 'Yüksek'],
            duplicates='drop'
        )
    except:
        bcg_df['Buyume_Potansiyeli_Segment'] = 'Orta'
    
    # Strateji atama
    def assign_strategy(row):
        pazar = str(row['Pazar_Buyuklugu_Segment'])
        payi = str(row['Pazar_Payi_Segment'])
        buyume = str(row['Buyume_Potansiyeli_Segment'])
        
        # Agresif: Büyük pazar + Düşük pay + Yüksek potansiyel
        if pazar in ['Büyük', 'Orta'] and payi == 'Düşük' and buyume in ['Yüksek', 'Orta']:
            return '🚀 Agresif'
        # Hızlandırılmış: Orta pazar + Orta pay
        elif pazar in ['Büyük', 'Orta'] and payi == 'Orta':
            return '⚡ Hızlandırılmış'
        # Koruma: Büyük pazar + Yüksek pay
        elif pazar == 'Büyük' and payi == 'Yüksek':
            return '🛡️ Koruma'
        # Potansiyel: Küçük pazar ama yüksek büyüme
        elif pazar == 'Küçük' and buyume == 'Yüksek':
            return '💎 Potansiyel'
        else:
            return '👁️ İzleme'
    
    bcg_df['Yatirim_Stratejisi'] = bcg_df.apply(assign_strategy, axis=1)
    
    # Aksiyon önerileri
    def suggest_action(row):
        strategy = row['Yatirim_Stratejisi']
        if '🚀' in strategy:
            return 'Yatırımı artır, agresif büyüme stratejisi uygula'
        elif '⚡' in strategy:
            return 'Hızlandırılmış kaynak tahsisi, pazar payını yükselt'
        elif '🛡️' in strategy:
            return 'Lider konumu koru, savunma stratejisi'
        elif '💎' in strategy:
            return 'Seçici yatırım, gelecek potansiyeli izle'
        else:
            return 'Minimal kaynak, izleme modunda tut'
    
    bcg_df['Aksiyon'] = bcg_df.apply(suggest_action, axis=1)
    
    # Öncelik skoru (0-100)
    bcg_df['Oncelik_Skoru'] = 0
    
    # Pazar büyüklüğü katkısı
    max_pazar = bcg_df['Toplam_Pazar'].max()
    if max_pazar > 0:
        bcg_df['Oncelik_Skoru'] += (bcg_df['Toplam_Pazar'] / max_pazar) * 40
    
    # Büyüme potansiyeli katkısı
    max_pot = bcg_df['Buyume_Potansiyeli'].max()
    if max_pot > 0:
        bcg_df['Oncelik_Skoru'] += (bcg_df['Buyume_Potansiyeli'] / max_pot) * 30
    
    # Düşük pazar payı varsa ekstra puan
    bcg_df.loc[bcg_df['Pazar_Payi_%'] < 10, 'Oncelik_Skoru'] += 30
    
    return bcg_df

# =============================================================================
# VISUALIZATION FUNCTIONS
# =============================================================================

def create_territory_bar_chart(df, top_n=20, title="Territory Performans"):
    """Territory performans bar chart"""
    top_terr = df.nlargest(top_n, 'PF_Satis')
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=top_terr['TERRITORIES'],
        y=top_terr['PF_Satis'],
        name='PF Satış',
        marker_color='#3B82F6',
        text=top_terr['PF_Satis'].apply(lambda x: f'{x:,.0f}'),
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>PF: %{y:,.0f}<extra></extra>'
    ))
    
    fig.add_trace(go.Bar(
        x=top_terr['TERRITORIES'],
        y=top_terr['Rakip_Satis'],
        name='Rakip Satış',
        marker_color='#EF4444',
        text=top_terr['Rakip_Satis'].apply(lambda x: f'{x:,.0f}'),
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Rakip: %{y:,.0f}<extra></extra>'
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title='Territory',
        yaxis_title='Satış',
        barmode='group',
        height=500,
        xaxis=dict(tickangle=-45),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        hovermode='x unified'
    )
    
    return fig

def create_time_series_chart(monthly_df, title="Zaman Serisi Analizi"):
    """Gelişmiş zaman serisi chart"""
    fig = go.Figure()
    
    # Ana satış çizgisi
    fig.add_trace(go.Scatter(
        x=monthly_df['Period'],
        y=monthly_df['PF_Satis'],
        mode='lines+markers',
        name='PF Satış',
        line=dict(color='#3B82F6', width=3),
        marker=dict(size=8, symbol='circle'),
        fill='tonexty',
        hovertemplate='<b>%{x}</b><br>Satış: %{y:,.0f}<extra></extra>'
    ))
    
    # Rakip satış
    fig.add_trace(go.Scatter(
        x=monthly_df['Period'],
        y=monthly_df['Rakip_Satis'],
        mode='lines+markers',
        name='Rakip Satış',
        line=dict(color='#EF4444', width=3, dash='dash'),
        marker=dict(size=8, symbol='square'),
        hovertemplate='<b>%{x}</b><br>Rakip: %{y:,.0f}<extra></extra>'
    ))
    
    # MA-3
    fig.add_trace(go.Scatter(
        x=monthly_df['Period'],
        y=monthly_df['MA_3'],
        mode='lines',
        name='3 Dönem Ort.',
        line=dict(color='#10B981', width=2, dash='dot'),
        hovertemplate='<b>%{x}</b><br>MA-3: %{y:,.0f}<extra></extra>'
    ))
    
    # MA-6
    fig.add_trace(go.Scatter(
        x=monthly_df['Period'],
        y=monthly_df['MA_6'],
        mode='lines',
        name='6 Dönem Ort.',
        line=dict(color='#8B5CF6', width=2, dash='dashdot'),
        hovertemplate='<b>%{x}</b><br>MA-6: %{y:,.0f}<extra></extra>'
    ))
    
    # Trend çizgisi
    if 'Trend' in monthly_df.columns:
        fig.add_trace(go.Scatter(
            x=monthly_df['Period'],
            y=monthly_df['Trend'],
            mode='lines',
            name='Trend',
            line=dict(color='#F59E0B', width=3, dash='longdash'),
            hovertemplate='<b>%{x}</b><br>Trend: %{y:,.0f}<extra></extra>'
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title='Dönem',
        yaxis_title='Satış',
        height=500,
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        )
    )
    
    return fig

def create_growth_heatmap(df, product):
    """Aylık büyüme ısı haritası"""
    cols = get_product_columns(product)
    
    # Ay x Territory pivot
    pivot_data = df.pivot_table(
        index='TERRITORIES',
        columns='YIL_AY',
        values=cols['pf'],
        aggfunc='sum',
        fill_value=0
    )
    
    # Büyüme oranları hesapla
    growth_data = pivot_data.pct_change(axis=1) * 100
    
    # Top 20 territory
    top_territories = pivot_data.sum(axis=1).nlargest(20).index
    growth_data_top = growth_data.loc[top_territories]
    
    fig = go.Figure(data=go.Heatmap(
        z=growth_data_top.values,
        x=growth_data_top.columns,
        y=growth_data_top.index,
        colorscale='RdYlGn',
        zmid=0,
        text=growth_data_top.values,
        texttemplate='%{text:.1f}%',
        textfont={"size": 8},
        hovertemplate='Territory: %{y}<br>Dönem: %{x}<br>Büyüme: %{z:.1f}%<extra></extra>',
        colorbar=dict(title='Büyüme %')
    ))
    
    fig.update_layout(
        title='Territory Bazlı Aylık Büyüme Isı Haritası',
        xaxis_title='Dönem',
        yaxis_title='Territory',
        height=600,
        xaxis=dict(tickangle=-45)
    )
    
    return fig

def create_bcg_scatter(bcg_df):
    """Gelişmiş BCG Matrix scatter"""
    color_map = {
        "⭐ Star": "#FFD700",
        "🐄 Cash Cow": "#10B981",
        "❓ Question Mark": "#3B82F6",
        "🐶 Dog": "#9CA3AF"
    }
    
    fig = px.scatter(
        bcg_df,
        x='Goreceli_Pazar_Payi',
        y='Pazar_Buyume_%',
        size='PF_Satis',
        color='BCG_Kategori',
        color_discrete_map=color_map,
        hover_name='TERRITORIES',
        hover_data={
            'PF_Satis': ':,.0f',
            'Pazar_Payi_%': ':.1f',
            'Toplam_Pazar': ':,.0f',
            'Goreceli_Pazar_Payi': ':.2f',
            'Pazar_Buyume_%': ':.1f'
        },
        labels={
            'Goreceli_Pazar_Payi': 'Göreceli Pazar Payı (PF/Rakip)',
            'Pazar_Buyume_%': 'Pazar Büyüme Oranı (%)'
        },
        size_max=60
    )
    
    # Median çizgileri
    median_share = bcg_df['Goreceli_Pazar_Payi'].median()
    median_growth = bcg_df['Pazar_Buyume_%'].median()
    
    fig.add_hline(y=median_growth, line_dash="dash", line_color="rgba(255,255,255,0.5)", line_width=2)
    fig.add_vline(x=median_share, line_dash="dash", line_color="rgba(255,255,255,0.5)", line_width=2)
    
    # Kadran etiketleri
    max_x = bcg_df['Goreceli_Pazar_Payi'].max()
    max_y = bcg_df['Pazar_Buyume_%'].max()
    min_y = bcg_df['Pazar_Buyume_%'].min()
    
    annotations = [
        dict(x=median_share + (max_x - median_share) * 0.5, y=median_growth + (max_y - median_growth) * 0.5,
             text="⭐<br>STARS", showarrow=False, font=dict(size=20, color="rgba(255,215,0,0.4)")),
        dict(x=median_share * 0.5, y=median_growth + (max_y - median_growth) * 0.5,
             text="❓<br>QUESTIONS", showarrow=False, font=dict(size=18, color="rgba(59,130,246,0.4)")),
        dict(x=median_share + (max_x - median_share) * 0.5, y=min_y + (median_growth - min_y) * 0.5,
             text="🐄<br>COWS", showarrow=False, font=dict(size=18, color="rgba(16,185,129,0.4)")),
        dict(x=median_share * 0.5, y=min_y + (median_growth - min_y) * 0.5,
             text="🐶<br>DOGS", showarrow=False, font=dict(size=18, color="rgba(156,163,175,0.4)"))
    ]
    
    fig.update_layout(
        title='BCG Matrix - Stratejik Portföy Analizi',
        height=650,
        plot_bgcolor='#0f172a',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e2e8f0'),
        annotations=annotations,
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
    )
    
    fig.update_traces(marker=dict(line=dict(width=2, color='rgba(255,255,255,0.5)'), opacity=0.8))
    
    return fig

def create_turkey_map(df, product, metric='PF_Satis'):
    """Türkiye haritası görselleştirmesi"""
    cols = get_product_columns(product)
    
    # Şehir bazlı toplam
    if 'CITY_NORMALIZED' in df.columns:
        city_data = df.groupby('CITY_NORMALIZED').agg({
            cols['pf']: 'sum',
            cols['rakip']: 'sum'
        }).reset_index()
        
        city_data.columns = ['City', 'PF_Satis', 'Rakip_Satis']
        city_data['Toplam_Pazar'] = city_data['PF_Satis'] + city_data['Rakip_Satis']
        city_data['Pazar_Payi_%'] = safe_divide(city_data['PF_Satis'], city_data['Toplam_Pazar']) * 100
        
        # Basit scatter map (GeoJSON olmadan)
        fig = px.scatter_geo(
            city_data,
            locations='City',
            locationmode='country names',
            size=metric if metric in city_data.columns else 'PF_Satis',
            color='Pazar_Payi_%',
            hover_name='City',
            hover_data={
                'PF_Satis': ':,.0f',
                'Toplam_Pazar': ':,.0f',
                'Pazar_Payi_%': ':.1f'
            },
            color_continuous_scale='Blues',
            size_max=50,
            title='Türkiye - Şehir Bazlı Performans Haritası'
        )
        
        fig.update_geos(
            center=dict(lat=39, lon=35),
            projection_scale=6,
            visible=True,
            resolution=50,
            showcountries=True,
            countrycolor="lightgray"
        )
        
        fig.update_layout(
            height=600,
            geo=dict(bgcolor='rgba(0,0,0,0)'),
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        return fig
    
    return None

# =============================================================================
# MANAGER PERFORMANCE SCORECARD
# =============================================================================

def create_manager_scorecard(df, product):
    """Manager performans scorecard"""
    cols = get_product_columns(product)
    
    manager_perf = df.groupby('MANAGER').agg({
        cols['pf']: 'sum',
        cols['rakip']: 'sum',
        'TERRITORIES': 'nunique'
    }).reset_index()
    
    manager_perf.columns = ['Manager', 'PF_Satis', 'Rakip_Satis', 'Territory_Sayisi']
    manager_perf['Toplam_Pazar'] = manager_perf['PF_Satis'] + manager_perf['Rakip_Satis']
    manager_perf['Pazar_Payi_%'] = safe_divide(manager_perf['PF_Satis'], manager_perf['Toplam_Pazar']) * 100
    manager_perf['Ortalama_Territory_Performans'] = safe_divide(manager_perf['PF_Satis'], manager_perf['Territory_Sayisi'])
    
    # Sıralama
    manager_perf = manager_perf.sort_values('PF_Satis', ascending=False)
    manager_perf['Rank'] = range(1, len(manager_perf) + 1)
    
    return manager_perf

# =============================================================================
# OPPORTUNITY ANALYSIS
# =============================================================================

def identify_opportunities(df, product):
    """Büyük fırsat olan territory'leri belirle"""
    terr_perf = calculate_territory_performance(df, product)
    
    # Fırsat kriterleri
    median_market = terr_perf['Toplam_Pazar'].median()
    
    opportunities = terr_perf[
        (terr_perf['Toplam_Pazar'] > median_market) &
        (terr_perf['Pazar_Payi_%'] < 10) &
        (terr_perf['Buyume_Potansiyeli'] > terr_perf['Buyume_Potansiyeli'].median())
    ].copy()
    
    opportunities = opportunities.sort_values('Buyume_Potansiyeli', ascending=False)
    
    return opportunities

def identify_zero_sales(df, product):
    """Sıfır satış olan territory'leri belirle"""
    cols = get_product_columns(product)
    
    all_territories = df['TERRITORIES'].unique()
    sales_territories = df[df[cols['pf']] > 0]['TERRITORIES'].unique()
    
    zero_sales = list(set(all_territories) - set(sales_territories))
    
    zero_sales_data = df[df['TERRITORIES'].isin(zero_sales)].groupby('TERRITORIES').agg({
        cols['rakip']: 'sum',
        'REGION': 'first',
        'CITY': 'first',
        'MANAGER': 'first'
    }).reset_index()
    
    zero_sales_data.columns = ['TERRITORIES', 'Rakip_Satis', 'REGION', 'CITY', 'MANAGER']
    
    return zero_sales_data

# =============================================================================
# ACTION PLAN GENERATOR
# =============================================================================

def generate_action_plan(df, product):
    """Otomatik aksiyon planı oluştur"""
    actions = []
    
    # 1. En büyük fırsatlar
    opportunities = identify_opportunities(df, product)
    for idx, row in opportunities.head(3).iterrows():
        actions.append({
            'Öncelik': '🔴 Kritik',
            'Territory': row['TERRITORIES'],
            'Aksiyon': f"Agresif yatırım - Pazar payını %{row['Pazar_Payi_%']:.1f}'den artır",
            'Neden': f"Büyük pazar ({row['Toplam_Pazar']:,.0f}) ama düşük payımız",
            'Potansiyel': f"+{row['Buyume_Potansiyeli']:,.0f}",
            'Sorumlu': row.get('MANAGER', 'N/A')
        })
    
    # 2. Sıfır satış olanlar
    zero_sales = identify_zero_sales(df, product)
    for idx, row in zero_sales.head(2).iterrows():
        actions.append({
            'Öncelik': '🟠 Yüksek',
            'Territory': row['TERRITORIES'],
            'Aksiyon': f"Pazar girişi - İlk satışı gerçekleştir",
            'Neden': f"Hiç satış yok ama rakip satıyor ({row['Rakip_Satis']:,.0f})",
            'Potansiyel': f"+{row['Rakip_Satis']:,.0f}",
            'Sorumlu': row.get('MANAGER', 'N/A')
        })
    
    # 3. Düşük performanslı manager'lar
    manager_perf = create_manager_scorecard(df, product)
    low_performers = manager_perf[manager_perf['Pazar_Payi_%'] < manager_perf['Pazar_Payi_%'].median()].head(2)
    
    for idx, row in low_performers.iterrows():
        actions.append({
            'Öncelik': '🟡 Orta',
            'Territory': 'Tüm Territory\'ler',
            'Aksiyon': f"{row['Manager']} ile performans görüşmesi",
            'Neden': f"Pazar payı %{row['Pazar_Payi_%']:.1f} - ortalamanın altında",
            'Potansiyel': 'Ekip motivasyonu',
            'Sorumlu': 'Bölge Müdürü'
        })
    
    return pd.DataFrame(actions)

# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main():
    # Header
    st.markdown('<h1 class="main-header">💊 GELİŞMİŞ TİCARİ PORTFÖY ANALİZ SİSTEMİ</h1>', unsafe_allow_html=True)
    st.markdown("**Territory × Zaman × Coğrafi Analiz | Stratejik Karar Destek Platformu**")
    
    # Sidebar - Dosya Yükleme
    st.sidebar.header("📂 Veri Yönetimi")
    uploaded_file = st.sidebar.file_uploader(
        "Excel Dosyası Yükleyin",
        type=['xlsx', 'xls'],
        help="Ticari ürün satış verisi (DATE, TERRITORIES, REGION, CITY, MANAGER, ürün kolonları)"
    )
    
    if not uploaded_file:
        st.info("👈 Lütfen sol taraftan Excel dosyasını yükleyin")
        st.markdown("""
        ### 📋 Gerekli Veri Formatı:
        
        **Zorunlu Kolonlar:**
        - `DATE`: Tarih bilgisi (aylık/günlük)
        - `TERRITORIES`: Territory adı
        - `REGION`: Bölge bilgisi
        - `CITY`: Şehir
        - `MANAGER`: Ticaret müdürü
        - Ürün kolonları: `CORTIPOL`, `DIGER CORTIPOL`, vb.
        
        **Örnek Veri Yapısı:**
        ```
        DATE       | TERRITORIES | REGION      | CITY     | MANAGER    | CORTIPOL | DIGER CORTIPOL
        2024-01-01 | TR-IST-01  | MARMARA     | ISTANBUL | AHMET YILMAZ | 1500    | 3000
        2024-01-01 | TR-ANK-01  | İÇ ANADOLU  | ANKARA   | MEHMET KAN   | 1200    | 2500
        ```
        """)
        st.stop()
    
    # Veriyi yükle
    try:
        df = load_excel_data(uploaded_file)
        if df is None:
            st.error("Veri yüklenemedi!")
            st.stop()
        
        st.sidebar.success(f"✅ {len(df):,} satır veri yüklendi")
        
        # Veri özeti
        with st.sidebar.expander("📊 Veri Özeti", expanded=False):
            st.write(f"📅 **Tarih Aralığı:**")
            st.write(f"   {df['DATE'].min().strftime('%Y-%m-%d')} → {df['DATE'].max().strftime('%Y-%m-%d')}")
            st.write(f"🏢 **Territory:** {df['TERRITORIES'].nunique()}")
            st.write(f"🗺️ **Bölge:** {df['REGION'].nunique()}")
            st.write(f"🏙️ **Şehir:** {df['CITY'].nunique()}")
            st.write(f"👤 **Manager:** {df['MANAGER'].nunique()}")
            st.write(f"📦 **Toplam Kayıt:** {len(df):,}")
    
    except Exception as e:
        st.error(f"❌ Veri yükleme hatası: {str(e)}")
        st.stop()
    
    # Sidebar - Filtreler
    st.sidebar.markdown("---")
    st.sidebar.header("🎯 Analiz Parametreleri")
    
    # Ürün seçimi
    available_products = ["TROCMETAM", "CORTIPOL", "DEKSAMETAZON", "PF IZOTONIK"]
    selected_product = st.sidebar.selectbox(
        "💊 Ürün",
        available_products,
        help="Analiz edilecek ürünü seçin"
    )
    
    # Tarih aralığı seçimi
    st.sidebar.markdown("### 📅 Zaman Aralığı")
    date_range_type = st.sidebar.radio(
        "Seçim Tipi",
        ["Tüm Dönem", "Özel Aralık"],
        horizontal=True
    )
    
    if date_range_type == "Özel Aralık":
        col_date1, col_date2 = st.sidebar.columns(2)
        with col_date1:
            start_date = st.date_input(
                "Başlangıç",
                df['DATE'].min(),
                min_value=df['DATE'].min(),
                max_value=df['DATE'].max()
            )
        with col_date2:
            end_date = st.date_input(
                "Bitiş",
                df['DATE'].max(),
                min_value=df['DATE'].min(),
                max_value=df['DATE'].max()
            )
        start_date = pd.Timestamp(start_date)
        end_date = pd.Timestamp(end_date)
    else:
        start_date = df['DATE'].min()
        end_date = df['DATE'].max()
    
    # Veriyi filtrele
    df_filtered = df[(df['DATE'] >= start_date) & (df['DATE'] <= end_date)].copy()
    
    # Territory filtresi
    st.sidebar.markdown("### 🏢 Territory Filtresi")
    territories = ["TÜMÜ"] + sorted(df_filtered['TERRITORIES'].unique())
    selected_territory = st.sidebar.selectbox("Territory", territories)
    
    # Region filtresi
    regions = ["TÜMÜ"] + sorted(df_filtered['REGION'].unique())
    selected_region = st.sidebar.selectbox("Bölge", regions)
    
    # Manager filtresi
    managers = ["TÜMÜ"] + sorted(df_filtered['MANAGER'].unique())
    selected_manager = st.sidebar.selectbox("Manager", managers)
    
    # Filtreleri uygula
    if selected_territory != "TÜMÜ":
        df_filtered = df_filtered[df_filtered['TERRITORIES'] == selected_territory]
    if selected_region != "TÜMÜ":
        df_filtered = df_filtered[df_filtered['REGION'] == selected_region]
    if selected_manager != "TÜMÜ":
        df_filtered = df_filtered[df_filtered['MANAGER'] == selected_manager]
    
    # ==========================================================================
    # TAB YAPISI
    # ==========================================================================
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📊 Dashboard",
        "🏢 Territory Analizi",
        "📈 Zaman Serisi",
        "🗺️ Coğrafi Analiz",
        "⭐ BCG & Strateji",
        "👥 Manager Performans",
        "🎯 Aksiyon Planı",
        "📥 Raporlar"
    ])
    
    # ==========================================================================
    # TAB 1: DASHBOARD
    # ==========================================================================
    with tab1:
        st.header("📊 Genel Performans Dashboard")
        
        # Temel metrikler
        cols = get_product_columns(selected_product)
        total_pf = df_filtered[cols['pf']].sum()
        total_rakip = df_filtered[cols['rakip']].sum()
        total_market = total_pf + total_rakip
        market_share = (total_pf / total_market * 100) if total_market > 0 else 0
        active_territories = df_filtered['TERRITORIES'].nunique()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "💊 PF Toplam Satış",
                f"{total_pf:,.0f}",
                help="Seçilen dönemde toplam PF satışı"
            )
        
        with col2:
            st.metric(
                "🏪 Toplam Pazar",
                f"{total_market:,.0f}",
                delta=f"+{total_rakip:,.0f} rakip",
                help="Toplam pazar büyüklüğü (PF + Rakip)"
            )
        
        with col3:
            st.metric(
                "📊 Pazar Payı",
                f"%{market_share:.1f}",
                delta=f"%{market_share - 50:.1f}" if market_share > 0 else None,
                help="PF'nin toplam pazardaki payı"
            )
        
        with col4:
            st.metric(
                "🏢 Aktif Territory",
                active_territories,
                help="Veri bulunan territory sayısı"
            )
        
        st.markdown("---")
        
        # Dönemsel karşılaştırma
        st.subheader("📅 Dönemsel Performans Karşılaştırması")
        period_comparison = calculate_period_comparison(df_filtered, selected_product, selected_territory)
        
        # Dönem metrikleri
        col_p1, col_p2, col_p3, col_p4, col_p5 = st.columns(5)
        
        periods = [
            ('Son_7_Gun', '📆 Son 7 Gün', col_p1),
            ('Son_30_Gun', '📆 Son 30 Gün', col_p2),
            ('Son_3_Ay', '📆 Son 3 Ay', col_p3),
            ('Son_6_Ay', '📆 Son 6 Ay', col_p4),
            ('YTD', '📆 YTD', col_p5)
        ]
        
        for period_key, period_label, col in periods:
            if period_key in period_comparison:
                with col:
                    data = period_comparison[period_key]
                    st.metric(
                        period_label,
                        f"{data['PF_Satis']:,.0f}",
                        delta=f"%{data['Pazar_Payi_%']:.1f} pay"
                    )
        
        st.markdown("---")
        
        # Hızlı görselleştirmeler
        col_v1, col_v2 = st.columns(2)
        
        with col_v1:
            st.markdown("#### 🏆 Top 10 Territory")
            terr_perf = calculate_territory_performance(df_filtered, selected_product, start_date, end_date)
            fig_top10 = create_territory_bar_chart(terr_perf, top_n=10, title="Top 10 Territory - PF vs Rakip")
            st.plotly_chart(fig_top10, use_container_width=True)
        
        with col_v2:
            st.markdown("#### 🎯 Pazar Payı Dağılımı")
            fig_pie = px.pie(
                terr_sorted.head(10),
                values='PF_Satis',
                names='TERRITORIES',
                title='Top 10 Territory - Satış Dağılımı',
                color_discrete_sequence=px.colors.sequential.Blues_r
            )
            fig_pie.update_layout(height=500)
            st.plotly_chart(fig_pie, use_container_width=True)
        
        st.markdown("---")
        
        # Detaylı tablo
        st.subheader("📋 Detaylı Territory Listesi")
        
        display_cols = ['TERRITORIES', 'REGION', 'CITY', 'MANAGER', 'PF_Satis', 
                       'Rakip_Satis', 'Toplam_Pazar', 'Pazar_Payi_%', 'Buyume_Potansiyeli']
        
        terr_display = terr_sorted[display_cols].copy()
        terr_display.index = range(1, len(terr_display) + 1)
        
        st.dataframe(
            terr_display.style.format({
                'PF_Satis': '{:,.0f}',
                'Rakip_Satis': '{:,.0f}',
                'Toplam_Pazar': '{:,.0f}',
                'Pazar_Payi_%': '{:.1f}%',
                'Buyume_Potansiyeli': '{:,.0f}'
            }).background_gradient(subset=['Pazar_Payi_%'], cmap='RdYlGn'),
            use_container_width=True,
            height=400
        )
        
        # Region bazlı özet
        st.markdown("---")
        st.subheader("🗺️ Region Bazlı Özet Analiz")
        
        region_summary = terr_sorted.groupby('REGION').agg({
            'PF_Satis': 'sum',
            'Rakip_Satis': 'sum',
            'Toplam_Pazar': 'sum',
            'TERRITORIES': 'count'
        }).reset_index()
        
        region_summary['Pazar_Payi_%'] = (region_summary['PF_Satis'] / region_summary['Toplam_Pazar'] * 100).round(1)
        region_summary = region_summary.sort_values('PF_Satis', ascending=False)
        
        col_r1, col_r2 = st.columns([1, 1])
        
        with col_r1:
            st.dataframe(
                region_summary.style.format({
                    'PF_Satis': '{:,.0f}',
                    'Rakip_Satis': '{:,.0f}',
                    'Toplam_Pazar': '{:,.0f}',
                    'Pazar_Payi_%': '{:.1f}%'
                }),
                use_container_width=True,
                hide_index=True
            )
        
        with col_r2:
            fig_region = px.bar(
                region_summary,
                x='REGION',
                y='PF_Satis',
                color='Pazar_Payi_%',
                color_continuous_scale='Blues',
                text='PF_Satis',
                title='Region Bazlı PF Satış'
            )
            fig_region.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig_region.update_layout(height=400, xaxis=dict(tickangle=-45))
            st.plotly_chart(fig_region, use_container_width=True)
    
    # ==========================================================================
    # TAB 3: ZAMAN SERİSİ ANALİZİ
    # ==========================================================================
    with tab3:
        st.header("📈 Zaman Serisi Analizi ve Trend Tahmini")
        
        # Frekans seçimi
        col_freq1, col_freq2, col_freq3 = st.columns([2, 2, 2])
        
        with col_freq1:
            frequency = st.selectbox(
                "📅 Zaman Periyodu",
                [('M', 'Aylık'), ('W', 'Haftalık'), ('Q', 'Çeyreklik')],
                format_func=lambda x: x[1]
            )[0]
        
        with col_freq2:
            territory_ts = st.selectbox(
                "🏢 Territory Seçimi",
                ["TÜMÜ"] + sorted(df_filtered['TERRITORIES'].unique()),
                key='ts_territory'
            )
        
        with col_freq3:
            show_trend = st.checkbox("📈 Trend Göster", value=True)
        
        # Zaman serisi hesapla
        time_series = calculate_time_series(df_filtered, selected_product, territory_ts, frequency)
        
        if len(time_series) == 0:
            st.warning("⚠️ Seçilen filtrelerde veri bulunamadı")
        else:
            # Temel istatistikler
            col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
            
            with col_stat1:
                avg_pf = time_series['PF_Satis'].mean()
                st.metric("📊 Ortalama PF", f"{avg_pf:,.0f}")
            
            with col_stat2:
                avg_growth = time_series['PF_Buyume_%'].mean()
                st.metric("📈 Ort. Büyüme", f"%{avg_growth:.1f}")
            
            with col_stat3:
                avg_share = time_series['Pazar_Payi_%'].mean()
                st.metric("🎯 Ort. Pazar Payı", f"%{avg_share:.1f}")
            
            with col_stat4:
                volatility = time_series['PF_Satis'].std() / time_series['PF_Satis'].mean()
                st.metric("📊 Volatilite", f"{volatility:.2f}")
            
            st.markdown("---")
            
            # Ana zaman serisi grafiği
            st.subheader("📈 Satış Trendi ve Hareketli Ortalamalar")
            fig_ts = create_time_series_chart(time_series, "Zaman Serisi Analizi")
            st.plotly_chart(fig_ts, use_container_width=True)
            
            st.markdown("---")
            
            # Büyüme analizi
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.markdown("#### 📊 Büyüme Oranları")
                
                # Büyüme bar chart
                colors_pf = ['#10B981' if x > 0 else '#EF4444' for x in time_series['PF_Buyume_%']]
                fig_growth = go.Figure()
                
                fig_growth.add_trace(go.Bar(
                    x=time_series['Period'],
                    y=time_series['PF_Buyume_%'],
                    name='PF Büyüme %',
                    marker_color=colors_pf,
                    text=time_series['PF_Buyume_%'].apply(lambda x: f'{x:.1f}%' if not pd.isna(x) else ''),
                    textposition='outside'
                ))
                
                fig_growth.update_layout(
                    title='Dönemsel Büyüme Oranları',
                    xaxis_title='Dönem',
                    yaxis_title='Büyüme (%)',
                    height=400,
                    xaxis=dict(tickangle=-45),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)'
                )
                
                st.plotly_chart(fig_growth, use_container_width=True)
            
            with col_g2:
                st.markdown("#### 🎯 Pazar Payı Evrimi")
                
                fig_share = go.Figure()
                
                fig_share.add_trace(go.Scatter(
                    x=time_series['Period'],
                    y=time_series['Pazar_Payi_%'],
                    mode='lines+markers',
                    fill='tozeroy',
                    line=dict(color='#8B5CF6', width=3),
                    marker=dict(size=8),
                    name='Pazar Payı %'
                ))
                
                # Ortalama çizgisi
                avg_line = time_series['Pazar_Payi_%'].mean()
                fig_share.add_hline(
                    y=avg_line,
                    line_dash="dash",
                    line_color="#F59E0B",
                    annotation_text=f"Ortalama: {avg_line:.1f}%"
                )
                
                fig_share.update_layout(
                    title='Pazar Payı Trendi',
                    xaxis_title='Dönem',
                    yaxis_title='Pazar Payı (%)',
                    height=400,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)'
                )
                
                st.plotly_chart(fig_share, use_container_width=True)
            
            st.markdown("---")
            
            # Detaylı istatistikler
            st.subheader("📊 Detaylı İstatistikler")
            
            col_stats1, col_stats2 = st.columns(2)
            
            with col_stats1:
                st.markdown("##### 📈 Büyüme İstatistikleri")
                growth_stats = time_series[['PF_Buyume_%', 'Rakip_Buyume_%', 'Goreceli_Buyume_%']].describe()
                st.dataframe(
                    growth_stats.style.format("{:.2f}%"),
                    use_container_width=True
                )
            
            with col_stats2:
                st.markdown("##### 📅 Son 3 Dönem Performansı")
                last_3 = time_series.tail(3)[['Period', 'PF_Satis', 'Pazar_Payi_%', 'PF_Buyume_%']]
                st.dataframe(
                    last_3.style.format({
                        'PF_Satis': '{:,.0f}',
                        'Pazar_Payi_%': '{:.1f}%',
                        'PF_Buyume_%': '{:.1f}%'
                    }),
                    use_container_width=True,
                    hide_index=True
                )
            
            st.markdown("---")
            
            # Detaylı veri tablosu
            st.subheader("📋 Zaman Serisi Veri Tablosu")
            
            time_series_display = time_series.copy()
            st.dataframe(
                time_series_display.style.format({
                    'PF_Satis': '{:,.0f}',
                    'Rakip_Satis': '{:,.0f}',
                    'Toplam_Pazar': '{:,.0f}',
                    'Pazar_Payi_%': '{:.1f}%',
                    'PF_Buyume_%': '{:.1f}%',
                    'Rakip_Buyume_%': '{:.1f}%',
                    'Goreceli_Buyume_%': '{:.1f}%',
                    'MA_3': '{:,.0f}',
                    'MA_6': '{:,.0f}'
                }).background_gradient(subset=['Goreceli_Buyume_%'], cmap='RdYlGn'),
                use_container_width=True,
                height=400
            )
    
    # ==========================================================================
    # TAB 4: COĞRAFİ ANALİZ
    # ==========================================================================
    with tab4:
        st.header("🗺️ Coğrafi Performans Analizi - Türkiye Haritası")
        
        st.info("💡 Bu bölümde Türkiye haritası üzerinde şehir ve bölge bazlı performans görselleştirmeleri yer alacak. GeoJSON dosyası yüklendikten sonra aktif olacaktır.")
        
        # Şehir bazlı performans tablosu
        st.subheader("🏙️ Şehir Bazlı Performans")
        
        cols = get_product_columns(selected_product)
        city_perf = df_filtered.groupby(['CITY', 'REGION']).agg({
            cols['pf']: 'sum',
            cols['rakip']: 'sum'
        }).reset_index()
        
        city_perf.columns = ['City', 'Region', 'PF_Satis', 'Rakip_Satis']
        city_perf['Toplam_Pazar'] = city_perf['PF_Satis'] + city_perf['Rakip_Satis']
        city_perf['Pazar_Payi_%'] = safe_divide(city_perf['PF_Satis'], city_perf['Toplam_Pazar']) * 100
        city_perf = city_perf.sort_values('PF_Satis', ascending=False)
        
        # Top 20 şehir
        col_city1, col_city2 = st.columns([1, 1])
        
        with col_city1:
            st.markdown("#### 🏆 Top 20 Şehir")
            fig_city_bar = px.bar(
                city_perf.head(20),
                x='City',
                y='PF_Satis',
                color='Pazar_Payi_%',
                color_continuous_scale='Blues',
                text='PF_Satis',
                title='Şehir Bazlı PF Satış'
            )
            fig_city_bar.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig_city_bar.update_layout(height=500, xaxis=dict(tickangle=-45))
            st.plotly_chart(fig_city_bar, use_container_width=True)
        
        with col_city2:
            st.markdown("#### 📊 Pazar Payı Dağılımı")
            fig_city_scatter = px.scatter(
                city_perf.head(30),
                x='Toplam_Pazar',
                y='Pazar_Payi_%',
                size='PF_Satis',
                color='Region',
                hover_name='City',
                title='Pazar Büyüklüğü vs Pazar Payı',
                size_max=50
            )
            fig_city_scatter.update_layout(height=500)
            st.plotly_chart(fig_city_scatter, use_container_width=True)
        
        st.markdown("---")
        
        # Detaylı şehir tablosu
        st.subheader("📋 Tüm Şehirler - Detaylı Liste")
        
        city_display = city_perf.copy()
        city_display.index = range(1, len(city_display) + 1)
        
        st.dataframe(
            city_display.style.format({
                'PF_Satis': '{:,.0f}',
                'Rakip_Satis': '{:,.0f}',
                'Toplam_Pazar': '{:,.0f}',
                'Pazar_Payi_%': '{:.1f}%'
            }).background_gradient(subset=['Pazar_Payi_%'], cmap='RdYlGn'),
            use_container_width=True,
            height=400
        )
    
    # ==========================================================================
    # TAB 5: BCG MATRIX & STRATEJİ
    # ==========================================================================
    with tab5:
        st.header("⭐ BCG Matrix & Yatırım Stratejisi Analizi")
        
        # BCG hesapla
        bcg_df = calculate_bcg_matrix(df_filtered, selected_product, start_date, end_date)
        strategy_df = calculate_investment_strategy(bcg_df)
        
        # BCG dağılımı
        st.subheader("📊 Portföy Dağılımı (BCG Kategorileri)")
        
        bcg_counts = strategy_df['BCG_Kategori'].value_counts()
        
        col_bcg1, col_bcg2, col_bcg3, col_bcg4 = st.columns(4)
        
        with col_bcg1:
            star_count = bcg_counts.get("⭐ Star", 0)
            star_pf = strategy_df[strategy_df['BCG_Kategori'] == "⭐ Star"]['PF_Satis'].sum()
            st.metric("⭐ Stars", f"{star_count} territory", delta=f"{star_pf:,.0f} PF")
        
        with col_bcg2:
            cow_count = bcg_counts.get("🐄 Cash Cow", 0)
            cow_pf = strategy_df[strategy_df['BCG_Kategori'] == "🐄 Cash Cow"]['PF_Satis'].sum()
            st.metric("🐄 Cash Cows", f"{cow_count} territory", delta=f"{cow_pf:,.0f} PF")
        
        with col_bcg3:
            q_count = bcg_counts.get("❓ Question Mark", 0)
            q_pf = strategy_df[strategy_df['BCG_Kategori'] == "❓ Question Mark"]['PF_Satis'].sum()
            st.metric("❓ Question Marks", f"{q_count} territory", delta=f"{q_pf:,.0f} PF")
        
        with col_bcg4:
            dog_count = bcg_counts.get("🐶 Dog", 0)
            dog_pf = strategy_df[strategy_df['BCG_Kategori'] == "🐶 Dog"]['PF_Satis'].sum()
            st.metric("🐶 Dogs", f"{dog_count} territory", delta=f"{dog_pf:,.0f} PF", delta_color="off")
        
        st.markdown("---")
        
        # BCG Scatter Plot
        st.subheader("🎯 BCG Matrix - Stratejik Konumlandırma")
        fig_bcg = create_bcg_scatter(strategy_df)
        st.plotly_chart(fig_bcg, use_container_width=True)
        
        st.markdown("---")
        
        # Yatırım stratejisi dağılımı
        st.subheader("🎯 Yatırım Stratejisi Dağılımı")
        
        strategy_counts = strategy_df['Yatirim_Stratejisi'].value_counts()
        
        col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
        
        strategies_colors = [
            ('🚀 Agresif', col_s1, '#DC2626'),
            ('⚡ Hızlandırılmış', col_s2, '#EA580C'),
            ('🛡️ Koruma', col_s3, '#10B981'),
            ('💎 Potansiyel', col_s4, '#8B5CF6'),
            ('👁️ İzleme', col_s5, '#6B7280')
        ]
        
        for strategy, col, color in strategies_colors:
            with col:
                count = strategy_counts.get(strategy, 0)
                pf_sum = strategy_df[strategy_df['Yatirim_Stratejisi'] == strategy]['PF_Satis'].sum()
                st.markdown(f"""
                <div style="background: {color}; padding: 1rem; border-radius: 8px; text-align: center; color: white;">
                    <h4>{strategy.split()[0]}</h4>
                    <h2>{count}</h2>
                    <p>{pf_sum:,.0f} PF</p>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Detaylı strateji tablosu
        st.subheader("📋 Territory'ler - Strateji & Aksiyon Detayları")
        
        strategy_filter = st.multiselect(
            "🔍 Strateji Filtrele",
            strategy_df['Yatirim_Stratejisi'].unique(),
            default=strategy_df['Yatirim_Stratejisi'].unique()
        )
        
        strategy_filtered = strategy_df[strategy_df['Yatirim_Stratejisi'].isin(strategy_filter)]
        
        display_cols_strategy = ['TERRITORIES', 'REGION', 'BCG_Kategori', 'Yatirim_Stratejisi',
                                'PF_Satis', 'Pazar_Payi_%', 'Buyume_Potansiyeli', 
                                'Oncelik_Skoru', 'Aksiyon']
        
        strategy_display = strategy_filtered[display_cols_strategy].copy()
        strategy_display = strategy_display.sort_values('Oncelik_Skoru', ascending=False)
        strategy_display.index = range(1, len(strategy_display) + 1)
        
        st.dataframe(
            strategy_display.style.format({
                'PF_Satis': '{:,.0f}',
                'Pazar_Payi_%': '{:.1f}%',
                'Buyume_Potansiyeli': '{:,.0f}',
                'Oncelik_Skoru': '{:.0f}'
            }).background_gradient(subset=['Oncelik_Skoru'], cmap='YlOrRd'),
            use_container_width=True,
            height=500
        )
    
    # ==========================================================================
    # TAB 6: MANAGER PERFORMANS
    # ==========================================================================
    with tab6:
        st.header("👥 Manager Performans Scorecard")
        
        manager_perf = create_manager_scorecard(df_filtered, selected_product)
        
        # Top 3 Manager - Ödül Podası
        st.subheader("🏆 Top 3 Manager - Performans Liderleri")
        
        col_m1, col_m2, col_m3 = st.columns(3)
        
        top3_managers = manager_perf.head(3)
        ocean_colors = [
            "linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%)",  # 🥇 Sky Blue
            "linear-gradient(135deg, #06B6D4 0%, #0891B2 100%)",  # 🥈 Cyan
            "linear-gradient(135deg, #14B8A6 0%, #0D9488 100%)"   # 🥉 Teal
        ]
        
        for idx, (col, row) in enumerate(zip([col_m1, col_m2, col_m3], top3_managers.itertuples())):
            rank_emoji = ["🥇", "🥈", "🥉"][idx]
            with col:
                st.markdown(f"""
                <div style="
                    background: {ocean_colors[idx]};
                    padding: 20px;
                    border-radius: 10px;
                    color: white;
                    text-align: center;
                    box-shadow: 0 8px 16px rgba(0,0,0,0.2);
                ">
                    <h1 style="font-size: 3rem; margin: 10px 0;">{rank_emoji}</h1>
                    <h3 style="font-size: 1.3rem; margin: 10px 0; font-weight: bold;">{row.Manager}</h3>
                    <h2 style="font-size: 2.2rem; margin: 15px 0; font-weight: bold;">{row.PF_Satis:,.0f}</h2>
                    <p style="font-size: 1rem; margin: 8px 0;">{int(row.Territory_Sayisi)} Territory</p>
                    <h4 style="font-size: 1.4rem; margin: 10px 0; font-weight: bold;">%{row.Pazar_Payi_:,.1f} Pazar Payı</h4>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Tüm manager'lar tablosu
        st.subheader("📊 Tüm Manager Performans Listesi")
        
        manager_display = manager_perf.copy()
        
        st.dataframe(
            manager_display.style.format({
                'PF_Satis': '{:,.0f}',
                'Rakip_Satis': '{:,.0f}',
                'Toplam_Pazar': '{:,.0f}',
                'Pazar_Payi_%': '{:.1f}%',
                'Ortalama_Territory_Performans': '{:,.0f}'
            }).background_gradient(subset=['Pazar_Payi_%'], cmap='RdYlGn'),
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown("---")
        
        # Manager karşılaştırma grafikleri
        col_mg1, col_mg2 = st.columns(2)
        
        with col_mg1:
            st.markdown("#### 📈 Manager Bazlı PF Satış")
            fig_manager = px.bar(
                manager_perf,
                x='Manager',
                y='PF_Satis',
                color='Pazar_Payi_%',
                color_continuous_scale='Blues',
                text='PF_Satis',
                title='Manager Performans Karşılaştırması'
            )
            fig_manager.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig_manager.update_layout(height=450, xaxis=dict(tickangle=-45))
            st.plotly_chart(fig_manager, use_container_width=True)
        
        with col_mg2:
            st.markdown("#### 🎯 Territory Sayısı vs Performans")
            fig_scatter_mgr = px.scatter(
                manager_perf,
                x='Territory_Sayisi',
                y='Pazar_Payi_%',
                size='PF_Satis',
                color='Manager',
                hover_name='Manager',
                title='Territory Etkinliği Analizi',
                size_max=50
            )
            fig_scatter_mgr.update_layout(height=450)
            st.plotly_chart(fig_scatter_mgr, use_container_width=True)
    
    # ==========================================================================
    # TAB 7: AKSİYON PLANI
    # ==========================================================================
    with tab7:
        st.header("🎯 Otomatik Aksiyon Planı")
        
        st.markdown("""
        Bu bölümde veriye dayalı otomatik aksiyon önerileri sunulmaktadır.
        Öncelik sıralaması: 🔴 Kritik > 🟠 Yüksek > 🟡 Orta
        """)
        
        # Aksiyon planı oluştur
        action_plan = generate_action_plan(df_filtered, selected_product)
        
        if len(action_plan) > 0:
            st.subheader(f"📋 {len(action_plan)} Öncelikli Aksiyon Tespit Edildi")
            
            # Aksiyonları göster
            for idx, row in action_plan.iterrows():
                priority = row['Öncelik']
                
                if '🔴' in priority:
                    css_class = 'priority-critical'
                elif '🟠' in priority:
                    css_class = 'priority-high'
                else:
                    css_class = 'priority-medium'
                
                st.markdown(f"""
                <div class="{css_class}">
                    <h4>{idx + 1}. {row['Aksiyon']}</h4>
                    <p><strong>Territory:</strong> {row['Territory']}</p>
                    <p><strong>Öncelik:</strong> {priority}</p>
                    <p><strong>Neden:</strong> {row['Neden']}</p>
                    <p><strong>Potansiyel Kazanç:</strong> {row['Potansiyel']}</p>
                    <p><strong>Sorumlu:</strong> {row['Sorumlu']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Excel export
            output_action = BytesIO()
            with pd.ExcelWriter(output_action, engine='openpyxl') as writer:
                action_plan.to_excel(writer, sheet_name='Aksiyon Planı', index=False)
            
            st.download_button(
                label="📥 Aksiyon Planını İndir (Excel)",
                data=output_action.getvalue(),
                file_name=f"aksiyon_plani_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.success("✅ Acil aksiyon gerektiren durum tespit edilmedi!")
    
    # ==========================================================================
    # TAB 8: RAPORLAR
    # ==========================================================================
     with tab8:
        st.header("📥 Rapor İndirme Merkezi")

        st.markdown("""
        Bu bölümden tüm analizlerin Excel raporlarını indirebilirsiniz.

        **Rapor İçeriği:**
        - ✅ Territory Performans Analizi
        - ✅ Zaman Serisi Verileri
            - ✅ BCG Matrix & Strateji
        - ✅ Manager Performans Scorecard
        - ✅ Aksiyon Planı
        """)

        st.markdown("---")
    
    # 📈 Son 12 Ay Trend Grafiği
    st.subheader("📈 Son 12 Aylık Satış Trendi")

    monthly_ts = calculate_time_series(
        df_filtered,
        selected_product,
        selected_territory,
        frequency='M'
    )

    if len(monthly_ts) > 0:
        fig_trend = create_time_series_chart(
            monthly_ts.tail(12),
            "Son 12 Aylık Trend"
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.warning("⚠️ Trend grafiği için yeterli veri bulunamadı.")

    st.markdown("---")


        # =========================================================
# BCG PORTFÖY ÖZETİ
# =========================================================

    st.subheader("⭐ Portföy Dağılımı (BCG)")

    bcg_data = calculate_bcg_matrix(
    df_filtered,
    selected_product,
    start_date,
    end_date
)

    bcg_counts = bcg_data["BCG_Kategori"].value_counts()

    col_bcg1, col_bcg2, col_bcg3, col_bcg4 = st.columns(4)

    bcg_categories = [
        ("⭐ Star", col_bcg1),
        ("🐄 Cash Cow", col_bcg2),
        ("❓ Question Mark", col_bcg3),
        ("🐶 Dog", col_bcg4),
    ]

    for category, col in bcg_categories:
    with col:
        count = int(bcg_counts.get(category, 0))
        pf_sum = bcg_data.loc[
            bcg_data["BCG_Kategori"] == category,
            "PF_Satis"
        ].sum()

        st.metric(
            label=category,
            value=f"{count} Territory",
            delta=f"{pf_sum:,.0f} PF"
        )

    

    
    # ==========================================================================
    # TAB 2: TERRITORY ANALİZİ
    # ==========================================================================
    with tab2:
        st.header("🏢 Territory Bazlı Detaylı Analiz")
        
        terr_perf = calculate_territory_performance(df_filtered, selected_product, start_date, end_date)
        
        # Sıralama seçenekleri
        col_sort1, col_sort2, col_sort3 = st.columns([2, 2, 1])
        
        with col_sort1:
            sort_by = st.selectbox(
                "🔄 Sıralama Kriteri",
                ['PF_Satis', 'Pazar_Payi_%', 'Toplam_Pazar', 'Buyume_Potansiyeli'],
                format_func=lambda x: {
                    'PF_Satis': '💊 PF Satış',
                    'Pazar_Payi_%': '📊 Pazar Payı',
                    'Toplam_Pazar': '🏪 Toplam Pazar',
                    'Buyume_Potansiyeli': '🚀 Büyüme Potansiyeli'
                }[x]
            )
        
        with col_sort2:
            show_n = st.slider("📊 Gösterilecek Territory", 10, 50, 20)
        
        with col_sort3:
            sort_order = st.radio("Sıra", ["↓ Azalan", "↑ Artan"], label_visibility="collapsed")
        
        terr_sorted = terr_perf.sort_values(sort_by, ascending=(sort_order == "↑ Artan")).head(show_n)
        
        # Görselleştirmeler
        col_v1, col_v2 = st.columns(2)
        
        with col_v1:
            st.markdown("#### 📊 PF vs Rakip Satış")
            fig_bar = create_territory_bar_chart(terr_sorted, top_n=show_n)
            st.plotly_chart(fig_bar, use_container_width=True)
        
        with col_v2:
            st.markdown("####









