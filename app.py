"""
🎯 GELİŞMİŞ TİCARİ PORTFÖY ANALİZ SİSTEMİ
Territory Bazlı Performans, ML Tahminleme, Türkiye Haritası ve Rekabet Analizi

Özellikler:
- 🗺️ Türkiye il bazlı harita görselleştirme
- 🤖 GERÇEK Machine Learning (Linear Regression, Ridge, Random Forest)
- 📊 Aylık/Yıllık dönem seçimi
- 📈 Gelişmiş rakip analizi ve trend karşılaştırması
- 🎯 Dinamik zaman aralığı filtreleme
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
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

warnings.filterwarnings("ignore")

# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(
    page_title="Ticari Portföy Analizi",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# CSS
# =============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #334155 100%);
    }
    
    .main-header {
        font-size: 3.5rem;
        font-weight: 900;
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #ffd700 0%, #f59e0b 50%, #d97706 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 0 40px rgba(255, 215, 0, 0.4);
        letter-spacing: -1px;
    }
    
    div[data-testid="stMetricValue"] {
        font-size: 2.8rem;
        font-weight: 900;
        background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 50%, #8b5cf6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    div[data-testid="metric-container"] {
        background: rgba(30, 41, 59, 0.9);
        padding: 2rem;
        border-radius: 16px;
        border: 1px solid rgba(59, 130, 246, 0.3);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
    }
    
    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px rgba(59, 130, 246, 0.4);
        border-color: rgba(59, 130, 246, 0.6);
    }
    
    .stTabs [data-baseweb="tab"] {
        color: #94a3b8;
        font-weight: 600;
        padding: 1rem 2rem;
        background: rgba(30, 41, 59, 0.5);
        border-radius: 8px 8px 0 0;
        margin: 0 0.25rem;
        transition: all 0.2s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(59, 130, 246, 0.2);
        color: #e0e7ff;
    }
    
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        box-shadow: 0 6px 20px rgba(59, 130, 246, 0.5);
    }
    
    h1, h2, h3 {
        color: #f1f5f9 !important;
        font-weight: 700;
    }
    
    p, span, div, label {
        color: #cbd5e1;
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(59, 130, 246, 0.5);
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# ŞEHİR NORMALIZASYON
# =============================================================================
CITY_NORMALIZE_CLEAN = {
    'ADANA': 'Adana',
    'ADIYAMAN': 'Adiyaman',
    'AFYONKARAHISAR': 'Afyonkarahisar',
    'AFYON': 'Afyonkarahisar',
    'AGRI': 'Agri',
    'AĞRI': 'Agri',
    'ANKARA': 'Ankara',
    'ANTALYA': 'Antalya',
    'AYDIN': 'Aydin',
    'BALIKESIR': 'Balikesir',
    'BARTIN': 'Bartin',
    'BATMAN': 'Batman',
    'BILECIK': 'Bilecik',
    'BINGOL': 'Bingol',
    'BITLIS': 'Bitlis',
    'BOLU': 'Bolu',
    'BURDUR': 'Burdur',
    'BURSA': 'Bursa',
    'CANAKKALE': 'Canakkale',
    'ÇANAKKALE': 'Canakkale',
    'CANKIRI': 'Cankiri',
    'ÇANKIRI': 'Cankiri',
    'CORUM': 'Corum',
    'ÇORUM': 'Corum',
    'DENIZLI': 'Denizli',
    'DIYARBAKIR': 'Diyarbakir',
    'DUZCE': 'Duzce',
    'DÜZCE': 'Duzce',
    'EDIRNE': 'Edirne',
    'ELAZIG': 'Elazig',
    'ELAZĞ': 'Elazig',
    'ELAZIĞ': 'Elazig',
    'ERZINCAN': 'Erzincan',
    'ERZURUM': 'Erzurum',
    'ESKISEHIR': 'Eskisehir',
    'ESKİŞEHİR': 'Eskisehir',
    'GAZIANTEP': 'Gaziantep',
    'GIRESUN': 'Giresun',
    'GİRESUN': 'Giresun',
    'GUMUSHANE': 'Gumushane',
    'GÜMÜŞHANE': 'Gumushane',
    'HAKKARI': 'Hakkari',
    'HATAY': 'Hatay',
    'IGDIR': 'Igdir',
    'IĞDIR': 'Igdir',
    'ISPARTA': 'Isparta',
    'ISTANBUL': 'Istanbul',
    'İSTANBUL': 'Istanbul',
    'IZMIR': 'Izmir',
    'İZMİR': 'Izmir',
    'KAHRAMANMARAS': 'K. Maras',
    'KAHRAMANMARAŞ': 'K. Maras',
    'K.MARAS': 'K. Maras',
    'KMARAS': 'K. Maras',
    'KARABUK': 'Karabuk',
    'KARABÜK': 'Karabuk',
    'KARAMAN': 'Karaman',
    'KARS': 'Kars',
    'KASTAMONU': 'Kastamonu',
    'KAYSERI': 'Kayseri',
    'KIRIKKALE': 'Kinkkale',
    'KIRKLARELI': 'Kirklareli',
    'KIRKLARELİ': 'Kirklareli',
    'KIRSEHIR': 'Kirsehir',
    'KIRŞEHİR': 'Kirsehir',
    'KILIS': 'Kilis',
    'KİLİS': 'Kilis',
    'KOCAELI': 'Kocaeli',
    'KONYA': 'Konya',
    'KUTAHYA': 'Kutahya',
    'KÜTAHYA': 'Kutahya',
    'MALATYA': 'Malatya',
    'MANISA': 'Manisa',
    'MANİSA': 'Manisa',
    'MARDIN': 'Mardin',
    'MARDİN': 'Mardin',
    'MERSIN': 'Mersin',
    'MERSİN': 'Mersin',
    'MUGLA': 'Mugla',
    'MUĞLA': 'Mugla',
    'MUS': 'Mus',
    'MUŞ': 'Mus',
    'NEVSEHIR': 'Nevsehir',
    'NEVŞEHİR': 'Nevsehir',
    'NIGDE': 'Nigde',
    'NİĞDE': 'Nigde',
    'ORDU': 'Ordu',
    'OSMANIYE': 'Osmaniye',
    'OSMANİYE': 'Osmaniye',
    'RIZE': 'Rize',
    'RİZE': 'Rize',
    'SAKARYA': 'Sakarya',
    'SAMSUN': 'Samsun',
    'SIIRT': 'Siirt',
    'SİİRT': 'Siirt',
    'SINOP': 'Sinop',
    'SİNOP': 'Sinop',
    'SIVAS': 'Sivas',
    'SİVAS': 'Sivas',
    'SANLIURFA': 'Sanliurfa',
    'ŞANLIURFA': 'Sanliurfa',
    'SIRNAK': 'Sirnak',
    'ŞIRNAK': 'Sirnak',
    'TEKIRDAG': 'Tekirdag',
    'TEKİRDAĞ': 'Tekirdag',
    'TOKAT': 'Tokat',
    'TRABZON': 'Trabzon',
    'TUNCELI': 'Tunceli',
    'TUNCELİ': 'Tunceli',
    'USAK': 'Usak',
    'UŞAK': 'Usak',
    'VAN': 'Van',
    'YALOVA': 'Yalova',
    'YOZGAT': 'Yozgat',
    'ZONGULDAK': 'Zonguldak',
    'ARDAHAN': 'Ardahan'
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def safe_divide(a, b):
    """Güvenli bölme işlemi"""
    return np.where(b != 0, a / b, 0)

def get_product_columns(product):
    """Ürün kolonlarını döndür"""
    if product == "TROCMETAM":
        return {"pf": "TROCMETAM", "rakip": "DIGER TROCMETAM"}
    elif product == "CORTIPOL":
        return {"pf": "CORTIPOL", "rakip": "DIGER CORTIPOL"}
    elif product == "DEKSAMETAZON":
        return {"pf": "DEKSAMETAZON", "rakip": "DIGER DEKSAMETAZON"}
    else:
        return {"pf": "PF IZOTONIK", "rakip": "DIGER IZOTONIK"}

def normalize_city_name_fixed(city_name):
    """Düzeltilmiş şehir normalizasyon"""
    if pd.isna(city_name):
        return None
    city_upper = str(city_name).strip().upper()
    city_upper = (city_upper
                  .replace('İ', 'I')
                  .replace('Ş', 'S')
                  .replace('Ğ', 'G')
                  .replace('Ü', 'U')
                  .replace('Ö', 'O')
                  .replace('Ç', 'C'))
    return CITY_NORMALIZE_CLEAN.get(city_upper, city_name)

# =============================================================================
# DATA LOADING
# =============================================================================

@st.cache_data
def load_excel_data(file):
    """Excel dosyasını yükle"""
    df = pd.read_excel(file)
    df['DATE'] = pd.to_datetime(df['DATE'])
    df['YIL_AY'] = df['DATE'].dt.strftime('%Y-%m')
    df['AY'] = df['DATE'].dt.month
    df['YIL'] = df['DATE'].dt.year
    
    df['TERRITORIES'] = df['TERRITORIES'].str.upper().str.strip()
    df['CITY'] = df['CITY'].str.strip()
    df['CITY_NORMALIZED'] = df['CITY'].apply(normalize_city_name_fixed)
    df['REGION'] = df['REGION'].str.upper().str.strip()
    df['MANAGER'] = df['MANAGER'].str.upper().str.strip()
    
    return df

@st.cache_data
def load_geojson_safe():
    """GeoJSON güvenli yükle"""
    paths = [
        '/mnt/user-data/uploads/turkey.geojson',
        'turkey.geojson',
        './turkey.geojson'
    ]
    
    for path in paths:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            continue
    
    return None

# =============================================================================
# ML FEATURE ENGINEERING
# =============================================================================

def create_ml_features(df):
    """ML için feature oluştur"""
    df = df.copy()
    df = df.sort_values('DATE').reset_index(drop=True)
    
    # Lag features
    df['lag_1'] = df['PF_Satis'].shift(1)
    df['lag_2'] = df['PF_Satis'].shift(2)
    df['lag_3'] = df['PF_Satis'].shift(3)
    
    # Rolling features
    df['rolling_mean_3'] = df['PF_Satis'].rolling(window=3, min_periods=1).mean()
    df['rolling_mean_6'] = df['PF_Satis'].rolling(window=6, min_periods=1).mean()
    df['rolling_std_3'] = df['PF_Satis'].rolling(window=3, min_periods=1).std()
    
    # Date features
    df['month'] = df['DATE'].dt.month
    df['quarter'] = df['DATE'].dt.quarter
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
    df['trend_index'] = range(len(df))
    
    # Fill NaN
    df = df.fillna(method='bfill').fillna(0)
    
    return df

def train_ml_models(df, forecast_periods=3):
    """GERÇEK ML modelleri ile tahmin"""
    df_features = create_ml_features(df)
    
    if len(df_features) < 10:
        return None, None, None
    
    feature_cols = ['lag_1', 'lag_2', 'lag_3', 'rolling_mean_3', 'rolling_mean_6',
                    'rolling_std_3', 'month', 'quarter', 'month_sin', 'month_cos', 'trend_index']
    
    # Train/Test split (zaman bazlı)
    split_idx = int(len(df_features) * 0.8)
    
    train_df = df_features.iloc[:split_idx]
    test_df = df_features.iloc[split_idx:]
    
    X_train = train_df[feature_cols]
    y_train = train_df['PF_Satis']
    X_test = test_df[feature_cols]
    y_test = test_df['PF_Satis']
    
    # Modeller
    models = {
        'Linear Regression': LinearRegression(),
        'Ridge Regression': Ridge(alpha=1.0),
        'Random Forest': RandomForestRegressor(n_estimators=100, random_state=42, max_depth=5)
    }
    
    results = {}
    
    for name, model in models.items():
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        mape = np.mean(np.abs((y_test - y_pred) / y_test)) * 100
        
        results[name] = {
            'model': model,
            'MAE': mae,
            'RMSE': rmse,
            'MAPE': mape
        }
    
    # En iyi model (MAPE'e göre)
    best_model_name = min(results.keys(), key=lambda x: results[x]['MAPE'])
    best_model = results[best_model_name]['model']
    
    # Gelecek tahmin
    forecast_data = []
    last_row = df_features.iloc[-1:].copy()
    
    for i in range(forecast_periods):
        next_date = last_row['DATE'].values[0] + pd.DateOffset(months=1)
        X_future = last_row[feature_cols]
        next_pred = best_model.predict(X_future)[0]
        
        forecast_data.append({
            'DATE': next_date,
            'YIL_AY': pd.to_datetime(next_date).strftime('%Y-%m'),
            'PF_Satis': max(0, next_pred),
            'Model': best_model_name
        })
        
        # Güncelle
        new_row = last_row.copy()
        new_row['DATE'] = next_date
        new_row['PF_Satis'] = next_pred
        new_row['lag_1'] = last_row['PF_Satis'].values[0]
        new_row['lag_2'] = last_row['lag_1'].values[0]
        new_row['lag_3'] = last_row['lag_2'].values[0]
        new_row['rolling_mean_3'] = (new_row['lag_1'] + new_row['lag_2'] + new_row['lag_3']) / 3
        new_row['month'] = pd.to_datetime(next_date).month
        new_row['quarter'] = pd.to_datetime(next_date).quarter
        new_row['month_sin'] = np.sin(2 * np.pi * new_row['month'] / 12)
        new_row['month_cos'] = np.cos(2 * np.pi * new_row['month'] / 12)
        new_row['trend_index'] = last_row['trend_index'].values[0] + 1
        
        last_row = new_row
    
    forecast_df = pd.DataFrame(forecast_data)
    
    return results, best_model_name, forecast_df

# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

def calculate_city_performance(df, product, date_filter=None):
    """Şehir bazlı performans"""
    cols = get_product_columns(product)
    
    if date_filter:
        df = df[(df['DATE'] >= date_filter[0]) & (df['DATE'] <= date_filter[1])]
    
    city_perf = df.groupby(['CITY_NORMALIZED']).agg({
        cols['pf']: 'sum',
        cols['rakip']: 'sum'
    }).reset_index()
    
    city_perf.columns = ['City', 'PF_Satis', 'Rakip_Satis']
    city_perf['Toplam_Pazar'] = city_perf['PF_Satis'] + city_perf['Rakip_Satis']
    city_perf['Pazar_Payi_%'] = safe_divide(city_perf['PF_Satis'], city_perf['Toplam_Pazar']) * 100
    
    return city_perf

def calculate_territory_performance(df, product, date_filter=None):
    """Territory bazlı performans"""
    cols = get_product_columns(product)
    
    if date_filter:
        df = df[(df['DATE'] >= date_filter[0]) & (df['DATE'] <= date_filter[1])]
    
    terr_perf = df.groupby(['TERRITORIES', 'REGION', 'CITY', 'MANAGER']).agg({
        cols['pf']: 'sum',
        cols['rakip']: 'sum'
    }).reset_index()
    
    terr_perf.columns = ['Territory', 'Region', 'City', 'Manager', 'PF_Satis', 'Rakip_Satis']
    terr_perf['Toplam_Pazar'] = terr_perf['PF_Satis'] + terr_perf['Rakip_Satis']
    terr_perf['Pazar_Payi_%'] = safe_divide(terr_perf['PF_Satis'], terr_perf['Toplam_Pazar']) * 100
    
    total_pf = terr_perf['PF_Satis'].sum()
    terr_perf['Agirlik_%'] = safe_divide(terr_perf['PF_Satis'], total_pf) * 100
    terr_perf['Goreceli_Pazar_Payi'] = safe_divide(terr_perf['PF_Satis'], terr_perf['Rakip_Satis'])
    
    return terr_perf.sort_values('PF_Satis', ascending=False)

def calculate_time_series(df, product, territory=None, date_filter=None):
    """Zaman serisi"""
    cols = get_product_columns(product)
    
    df_filtered = df.copy()
    if territory and territory != "TÜMÜ":
        df_filtered = df_filtered[df_filtered['TERRITORIES'] == territory]
    
    if date_filter:
        df_filtered = df_filtered[(df_filtered['DATE'] >= date_filter[0]) & 
                                   (df_filtered['DATE'] <= date_filter[1])]
    
    monthly = df_filtered.groupby('YIL_AY').agg({
        cols['pf']: 'sum',
        cols['rakip']: 'sum',
        'DATE': 'first'
    }).reset_index().sort_values('YIL_AY')
    
    monthly.columns = ['YIL_AY', 'PF_Satis', 'Rakip_Satis', 'DATE']
    monthly['Toplam_Pazar'] = monthly['PF_Satis'] + monthly['Rakip_Satis']
    monthly['Pazar_Payi_%'] = safe_divide(monthly['PF_Satis'], monthly['Toplam_Pazar']) * 100
    monthly['PF_Buyume_%'] = monthly['PF_Satis'].pct_change() * 100
    monthly['Rakip_Buyume_%'] = monthly['Rakip_Satis'].pct_change() * 100
    monthly['Goreceli_Buyume_%'] = monthly['PF_Buyume_%'] - monthly['Rakip_Buyume_%']
    monthly['MA_3'] = monthly['PF_Satis'].rolling(window=3, min_periods=1).mean()
    monthly['MA_6'] = monthly['PF_Satis'].rolling(window=6, min_periods=1).mean()
    
    return monthly

def calculate_competitor_analysis(df, product, date_filter=None):
    """Rakip analizi"""
    cols = get_product_columns(product)
    
    if date_filter:
        df = df[(df['DATE'] >= date_filter[0]) & (df['DATE'] <= date_filter[1])]
    
    monthly = df.groupby('YIL_AY').agg({
        cols['pf']: 'sum',
        cols['rakip']: 'sum'
    }).reset_index().sort_values('YIL_AY')
    
    monthly.columns = ['YIL_AY', 'PF', 'Rakip']
    monthly['PF_Pay_%'] = (monthly['PF'] / (monthly['PF'] + monthly['Rakip'])) * 100
    monthly['Rakip_Pay_%'] = 100 - monthly['PF_Pay_%']
    monthly['PF_Buyume'] = monthly['PF'].pct_change() * 100
    monthly['Rakip_Buyume'] = monthly['Rakip'].pct_change() * 100
    monthly['Fark'] = monthly['PF_Buyume'] - monthly['Rakip_Buyume']
    
    return monthly

def calculate_bcg_matrix(df, product, date_filter=None):
    """BCG Matrix"""
    cols = get_product_columns(product)
    
    if date_filter:
        df_filtered = df[(df['DATE'] >= date_filter[0]) & (df['DATE'] <= date_filter[1])]
    else:
        df_filtered = df.copy()
    
    terr_perf = calculate_territory_performance(df_filtered, product)
    
    df_sorted = df_filtered.sort_values('DATE')
    mid_point = len(df_sorted) // 2
    
    first_half = df_sorted.iloc[:mid_point].groupby('TERRITORIES')[cols['pf']].sum()
    second_half = df_sorted.iloc[mid_point:].groupby('TERRITORIES')[cols['pf']].sum()
    
    growth_rate = {}
    for terr in first_half.index:
        if terr in second_half.index and first_half[terr] > 0:
            growth_rate[terr] = ((second_half[terr] - first_half[terr]) / first_half[terr]) * 100
        else:
            growth_rate[terr] = 0
    
    terr_perf['Pazar_Buyume_%'] = terr_perf['Territory'].map(growth_rate).fillna(0)
    
    median_share = terr_perf['Goreceli_Pazar_Payi'].median()
    median_growth = terr_perf['Pazar_Buyume_%'].median()
    
    def assign_bcg(row):
        if row['Goreceli_Pazar_Payi'] >= median_share and row['Pazar_Buyume_%'] >= median_growth:
            return "⭐ Star"
        elif row['Goreceli_Pazar_Payi'] >= median_share and row['Pazar_Buyume_%'] < median_growth:
            return "🐄 Cash Cow"
        elif row['Goreceli_Pazar_Payi'] < median_share and row['Pazar_Buyume_%'] >= median_growth:
            return "❓ Question Mark"
        else:
            return "🐶 Dog"
    
    terr_perf['BCG_Kategori'] = terr_perf.apply(assign_bcg, axis=1)
    
    return terr_perf

# =============================================================================
# VISUALIZATION FUNCTIONS
# =============================================================================

def create_turkey_map_fixed(city_data, geojson, title="Türkiye Satış Haritası"):
    """Düzeltilmiş harita"""
    if geojson is None:
        st.error("❌ GeoJSON yüklenemedi")
        return None
    
    geojson_cities = [f['properties']['name'] for f in geojson['features']]
    data_cities = city_data['City'].unique()
    
    missing = set(data_cities) - set(geojson_cities)
    if missing:
        st.warning(f"⚠️ GeoJSON'da bulunamayan şehirler: {missing}")
    
    fig = px.choropleth_mapbox(
        city_data,
        geojson=geojson,
        locations='City',
        featureidkey="properties.name",
        color='PF_Satis',
        hover_name='City',
        hover_data={
            'PF_Satis': ':,.0f',
            'Pazar_Payi_%': ':.1f',
            'City': False
        },
        color_continuous_scale="YlOrRd",
        labels={'PF_Satis': 'PF Satış'},
        title=title,
        mapbox_style="carto-positron",
        center={"lat": 39.0, "lon": 35.0},
        zoom=5
    )
    
    fig.update_layout(height=600, margin=dict(l=0, r=0, t=50, b=0))
    
    return fig

def create_forecast_chart(historical_df, forecast_df):
    """Tahmin grafiği"""
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=historical_df['DATE'],
        y=historical_df['PF_Satis'],
        mode='lines+markers',
        name='Gerçek Satış',
        line=dict(color='#3B82F6', width=2),
        marker=dict(size=6)
    ))
    
    if forecast_df is not None and len(forecast_df) > 0:
        fig.add_trace(go.Scatter(
            x=forecast_df['DATE'],
            y=forecast_df['PF_Satis'],
            mode='lines+markers',
            name='Tahmin',
            line=dict(color='#EF4444', width=2, dash='dash'),
            marker=dict(size=6, symbol='diamond')
        ))
    
    fig.update_layout(
        title='Satış Trendi ve ML Tahmin',
        xaxis_title='Tarih',
        yaxis_title='PF Satış',
        height=400,
        hovermode='x unified'
    )
    
    return fig

def create_competitor_comparison_chart(comp_data):
    """Rakip karşılaştırma"""
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=comp_data['YIL_AY'],
        y=comp_data['PF'],
        name='PF',
        marker_color='#3B82F6'
    ))
    
    fig.add_trace(go.Bar(
        x=comp_data['YIL_AY'],
        y=comp_data['Rakip'],
        name='Rakip',
        marker_color='#EF4444'
    ))
    
    fig.update_layout(
        title='PF vs Rakip Satış',
        xaxis_title='Ay',
        yaxis_title='Satış',
        barmode='group',
        height=400
    )
    
    return fig

def create_market_share_trend(comp_data):
    """Pazar payı trend"""
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=comp_data['YIL_AY'],
        y=comp_data['PF_Pay_%'],
        mode='lines+markers',
        name='PF Pazar Payı',
        fill='tozeroy',
        line=dict(color='#3B82F6', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=comp_data['YIL_AY'],
        y=comp_data['Rakip_Pay_%'],
        mode='lines+markers',
        name='Rakip Pazar Payı',
        fill='tozeroy',
        line=dict(color='#EF4444', width=2)
    ))
    
    fig.update_layout(
        title='Pazar Payı Trendi (%)',
        xaxis_title='Ay',
        yaxis_title='Pazar Payı (%)',
        height=400,
        yaxis=dict(range=[0, 100])
    )
    
    return fig

def create_growth_comparison(comp_data):
    """Büyüme karşılaştırma"""
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=comp_data['YIL_AY'],
        y=comp_data['PF_Buyume'],
        mode='lines+markers',
        name='PF Büyüme',
        line=dict(color='#3B82F6', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=comp_data['YIL_AY'],
        y=comp_data['Rakip_Buyume'],
        mode='lines+markers',
        name='Rakip Büyüme',
        line=dict(color='#EF4444', width=2)
    ))
    
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    fig.update_layout(
        title='Büyüme Oranları Karşılaştırması (%)',
        xaxis_title='Ay',
        yaxis_title='Büyüme (%)',
        height=400
    )
    
    return fig

# =============================================================================
# MAIN APP
# =============================================================================

def main():
    st.markdown('<h1 class="main-header">🎯 GELİŞMİŞ TİCARİ PORTFÖY ANALİZ SİSTEMİ</h1>', unsafe_allow_html=True)
    st.markdown("**GERÇEK ML Tahminleme • Türkiye Haritası • Rakip Analizi • BCG Matrix**")
    
    st.sidebar.header("📂 Dosya Yükleme")
    uploaded_file = st.sidebar.file_uploader("Excel Dosyası Yükleyin", type=['xlsx', 'xls'])
    
    if not uploaded_file:
        st.info("👈 Lütfen sol taraftan Excel dosyasını yükleyin")
        st.stop()
    
    try:
        df = load_excel_data(uploaded_file)
        geojson = load_geojson_safe()
        st.sidebar.success(f"✅ {len(df)} satır veri yüklendi")
    except Exception as e:
        st.error(f"❌ Veri yükleme hatası: {str(e)}")
        st.stop()
    
    st.sidebar.markdown("---")
    st.sidebar.header("💊 Ürün Seçimi")
    selected_product = st.sidebar.selectbox("Ürün", ["TROCMETAM", "CORTIPOL", "DEKSAMETAZON", "PF IZOTONIK"])
    
    st.sidebar.markdown("---")
    st.sidebar.header("📅 Tarih Aralığı")
    
    min_date = df['DATE'].min()
    max_date = df['DATE'].max()
    
    date_option = st.sidebar.selectbox("Dönem Seçin", ["Tüm Veriler", "Son 3 Ay", "Son 6 Ay", "Son 1 Yıl", "2025", "2024", "Özel Aralık"])
    
    if date_option == "Tüm Veriler":
        date_filter = None
    elif date_option == "Son 3 Ay":
        start_date = max_date - pd.DateOffset(months=3)
        date_filter = (start_date, max_date)
    elif date_option == "Son 6 Ay":
        start_date = max_date - pd.DateOffset(months=6)
        date_filter = (start_date, max_date)
    elif date_option == "Son 1 Yıl":
        start_date = max_date - pd.DateOffset(years=1)
        date_filter = (start_date, max_date)
    elif date_option == "2025":
        date_filter = (pd.to_datetime('2025-01-01'), pd.to_datetime('2025-12-31'))
    elif date_option == "2024":
        date_filter = (pd.to_datetime('2024-01-01'), pd.to_datetime('2024-12-31'))
    else:
        col_date1, col_date2 = st.sidebar.columns(2)
        with col_date1:
            start_date = st.date_input("Başlangıç", min_date, min_value=min_date, max_value=max_date)
        with col_date2:
            end_date = st.date_input("Bitiş", max_date, min_value=min_date, max_value=max_date)
        date_filter = (pd.to_datetime(start_date), pd.to_datetime(end_date))
    
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filtreler")
    
    territories = ["TÜMÜ"] + sorted(df['TERRITORIES'].unique())
    selected_territory = st.sidebar.selectbox("Territory", territories)
    
    regions = ["TÜMÜ"] + sorted(df['REGION'].unique())
    selected_region = st.sidebar.selectbox("Bölge", regions)
    
    managers = ["TÜMÜ"] + sorted(df['MANAGER'].unique())
    selected_manager = st.sidebar.selectbox("Manager", managers)
    
    df_filtered = df.copy()
    if selected_territory != "TÜMÜ":
        df_filtered = df_filtered[df_filtered['TERRITORIES'] == selected_territory]
    if selected_region != "TÜMÜ":
        df_filtered = df_filtered[df_filtered['REGION'] == selected_region]
    if selected_manager != "TÜMÜ":
        df_filtered = df_filtered[df_filtered['MANAGER'] == selected_manager]
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 Genel Bakış",
        "🗺️ Türkiye Haritası",
        "🏢 Territory Analizi",
        "📈 Zaman Serisi & ML",
        "🎯 Rakip Analizi",
        "⭐ BCG & Strateji",
        "📥 Raporlar"
    ])
    
    # TAB 1: GENEL BAKIŞ
    with tab1:
        st.header("📊 Genel Performans Özeti")
        
        cols = get_product_columns(selected_product)
        
        if date_filter:
            df_period = df_filtered[(df_filtered['DATE'] >= date_filter[0]) & (df_filtered['DATE'] <= date_filter[1])]
        else:
            df_period = df_filtered
        
        total_pf = df_period[cols['pf']].sum()
        total_rakip = df_period[cols['rakip']].sum()
        total_market = total_pf + total_rakip
        market_share = (total_pf / total_market * 100) if total_market > 0 else 0
        active_territories = df_period['TERRITORIES'].nunique()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("💊 PF Satış", f"{total_pf:,.0f}")
        with col2:
            st.metric("🏪 Toplam Pazar", f"{total_market:,.0f}")
        with col3:
            st.metric("📊 Pazar Payı", f"%{market_share:.1f}")
        with col4:
            st.metric("🏢 Territory Sayısı", active_territories)
        
        st.markdown("---")
        
        st.subheader("🏆 Top 10 Territory")
        terr_perf = calculate_territory_performance(df_filtered, selected_product, date_filter)
        top10 = terr_perf.head(10)
        
        fig_top10 = go.Figure()
        
        fig_top10.add_trace(go.Bar(
            x=top10['Territory'],
            y=top10['PF_Satis'],
            name='PF Satış',
            marker_color='#3B82F6',
            text=top10['PF_Satis'].apply(lambda x: f'{x:,.0f}'),
            textposition='outside'
        ))
        
        fig_top10.add_trace(go.Bar(
            x=top10['Territory'],
            y=top10['Rakip_Satis'],
            name='Rakip Satış',
            marker_color='#EF4444',
            text=top10['Rakip_Satis'].apply(lambda x: f'{x:,.0f}'),
            textposition='outside'
        ))
        
        fig_top10.update_layout(
            title='Top 10 Territory - PF vs Rakip',
            xaxis_title='Territory',
            yaxis_title='Satış',
            barmode='group',
            height=500,
            xaxis=dict(tickangle=-45)
        )
        
        st.plotly_chart(fig_top10, use_container_width=True)
        
        display_cols = ['Territory', 'Region', 'City', 'Manager', 'PF_Satis', 'Pazar_Payi_%', 'Agirlik_%']
        top10_display = top10[display_cols].copy()
        top10_display.columns = ['Territory', 'Region', 'City', 'Manager', 'PF Satış', 'Pazar Payı %', 'Ağırlık %']
        top10_display.index = range(1, len(top10_display) + 1)
        
        st.dataframe(
            top10_display.style.format({
                'PF Satış': '{:,.0f}',
                'Pazar Payı %': '{:.1f}',
                'Ağırlık %': '{:.1f}'
            }),
            use_container_width=True
        )
    
    # TAB 2: TÜRKİYE HARİTASI
    with tab2:
        st.header("🗺️ Türkiye İl Bazlı Satış Haritası")
        
        city_data = calculate_city_performance(df_filtered, selected_product, date_filter)
        
        col1, col2, col3, col4 = st.columns(4)
        
        total_pf = city_data['PF_Satis'].sum()
        total_market = city_data['Toplam_Pazar'].sum()
        avg_share = city_data['Pazar_Payi_%'].mean()
        active_cities = len(city_data[city_data['PF_Satis'] > 0])
        
        with col1:
            st.metric("💊 Toplam PF Satış", f"{total_pf:,.0f}")
        with col2:
            st.metric("🏪 Toplam Pazar", f"{total_market:,.0f}")
        with col3:
            st.metric("📊 Ort. Pazar Payı", f"%{avg_share:.1f}")
        with col4:
            st.metric("🏙️ Aktif Şehir", active_cities)
        
        st.markdown("---")
        
        if geojson:
            st.subheader("📍 İl Bazlı Dağılım")
            
            city_data_fixed = city_data.copy()
            city_data_fixed['City'] = city_data_fixed['City'].apply(normalize_city_name_fixed)
            
            turkey_map = create_turkey_map_fixed(city_data_fixed, geojson, f"{selected_product} - Şehir Bazlı Satış Dağılımı")
            
            if turkey_map:
                st.plotly_chart(turkey_map, use_container_width=True)
            else:
                st.error("❌ Harita oluşturulamadı")
        else:
            st.warning("⚠️ turkey.geojson bulunamadı")
        
        st.markdown("---")
        
        st.subheader("🏆 Top 10 Şehir")
        top_cities = city_data.nlargest(10, 'PF_Satis')
        
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            fig_bar = px.bar(
                top_cities,
                x='City',
                y='PF_Satis',
                title='En Yüksek Satış Yapan Şehirler',
                color='Pazar_Payi_%',
                color_continuous_scale='Blues'
            )
            fig_bar.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_bar, use_container_width=True)
        
        with col_chart2:
            fig_pie = px.pie(
                top_cities,
                values='PF_Satis',
                names='City',
                title='Top 10 Şehir Satış Dağılımı'
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        st.markdown("---")
        st.subheader("📋 Detaylı Şehir Listesi")
        
        city_display = city_data.sort_values('PF_Satis', ascending=False).copy()
        city_display.index = range(1, len(city_display) + 1)
        
        st.dataframe(
            city_display.style.format({
                'PF_Satis': '{:,.0f}',
                'Rakip_Satis': '{:,.0f}',
                'Toplam_Pazar': '{:,.0f}',
                'Pazar_Payi_%': '{:.1f}'
            }).background_gradient(subset=['Pazar_Payi_%'], cmap='RdYlGn'),
            use_container_width=True,
            height=400
        )
    
    # TAB 3: TERRITORY ANALİZİ
    with tab3:
        st.header("🏢 Territory Bazlı Detaylı Analiz")
        
        terr_perf = calculate_territory_performance(df_filtered, selected_product, date_filter)
        
        col_f1, col_f2 = st.columns([1, 3])
        
        with col_f1:
            sort_by = st.selectbox(
                "Sıralama",
                ['PF_Satis', 'Pazar_Payi_%', 'Toplam_Pazar', 'Agirlik_%'],
                format_func=lambda x: {
                    'PF_Satis': 'PF Satış',
                    'Pazar_Payi_%': 'Pazar Payı %',
                    'Toplam_Pazar': 'Toplam Pazar',
                    'Agirlik_%': 'Ağırlık %'
                }[x]
            )
        
        with col_f2:
            show_n = st.slider("Gösterilecek Territory Sayısı", 10, 50, 20)
        
        terr_sorted = terr_perf.sort_values(sort_by, ascending=False).head(show_n)
        
        col_v1, col_v2 = st.columns(2)
        
        with col_v1:
            st.markdown("#### 📊 PF vs Rakip Satış")
            fig_bar = go.Figure()
            
            fig_bar.add_trace(go.Bar(
                x=terr_sorted['Territory'],
                y=terr_sorted['PF_Satis'],
                name='PF Satış',
                marker_color='#3B82F6'
            ))
            
            fig_bar.add_trace(go.Bar(
                x=terr_sorted['Territory'],
                y=terr_sorted['Rakip_Satis'],
                name='Rakip Satış',
                marker_color='#EF4444'
            ))
            
            fig_bar.update_layout(
                barmode='group',
                height=500,
                xaxis=dict(tickangle=-45)
            )
            
            st.plotly_chart(fig_bar, use_container_width=True)
        
        with col_v2:
            st.markdown("#### 🎯 Pazar Payı Dağılımı")
            fig_pie = px.pie(
                terr_sorted.head(10),
                values='PF_Satis',
                names='Territory',
                title='Top 10 Territory - PF Satış Dağılımı'
            )
            fig_pie.update_layout(height=500)
            st.plotly_chart(fig_pie, use_container_width=True)
        
        st.markdown("---")
        
        st.subheader("📋 Detaylı Territory Listesi")
        
        display_cols = ['Territory', 'Region', 'City', 'Manager', 'PF_Satis', 'Rakip_Satis', 'Toplam_Pazar', 'Pazar_Payi_%', 'Goreceli_Pazar_Payi', 'Agirlik_%']
        
        terr_display = terr_sorted[display_cols].copy()
        terr_display.columns = ['Territory', 'Region', 'City', 'Manager', 'PF Satış', 'Rakip Satış', 'Toplam Pazar', 'Pazar Payı %', 'Göreceli Pay', 'Ağırlık %']
        terr_display.index = range(1, len(terr_display) + 1)
        
        st.dataframe(
            terr_display.style.format({
                'PF Satış': '{:,.0f}',
                'Rakip Satış': '{:,.0f}',
                'Toplam Pazar': '{:,.0f}',
                'Pazar Payı %': '{:.1f}',
                'Göreceli Pay': '{:.2f}',
                'Ağırlık %': '{:.1f}'
            }).background_gradient(subset=['Pazar Payı %'], cmap='RdYlGn'),
            use_container_width=True
        )
    
    # TAB 4: ZAMAN SERİSİ & ML
    with tab4:
        st.header("📈 Zaman Serisi Analizi & GERÇEK ML Tahminleme")
        
        territory_for_ts = st.selectbox(
            "Territory Seçin",
            ["TÜMÜ"] + sorted(df_filtered['TERRITORIES'].unique()),
            key='ts_territory'
        )
        
        monthly_df = calculate_time_series(df_filtered, selected_product, territory_for_ts, date_filter)
        
        if len(monthly_df) == 0:
            st.warning("⚠️ Seçilen filtrelerde veri bulunamadı")
        else:
            st.subheader("📊 Zaman Serisi Analizi")
            
            col_ts1, col_ts2, col_ts3, col_ts4 = st.columns(4)
            
            with col_ts1:
                avg_pf = monthly_df['PF_Satis'].mean()
                st.metric("📊 Ort. Aylık PF", f"{avg_pf:,.0f}")
            
            with col_ts2:
                avg_growth = monthly_df['PF_Buyume_%'].mean()
                st.metric("📈 Ort. Büyüme", f"%{avg_growth:.1f}")
            
            with col_ts3:
                avg_share = monthly_df['Pazar_Payi_%'].mean()
                st.metric("🎯 Ort. Pazar Payı", f"%{avg_share:.1f}")
            
            with col_ts4:
                total_months = len(monthly_df)
                st.metric("📅 Veri Dönemi", f"{total_months} ay")
            
            st.markdown("---")
            
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                st.markdown("#### 📊 Satış Trendi")
                fig_ts = go.Figure()
                
                fig_ts.add_trace(go.Scatter(
                    x=monthly_df['DATE'],
                    y=monthly_df['PF_Satis'],
                    mode='lines+markers',
                    name='PF Satış',
                    line=dict(color='#3B82F6', width=3),
                    marker=dict(size=8)
                ))
                
                fig_ts.add_trace(go.Scatter(
                    x=monthly_df['DATE'],
                    y=monthly_df['Rakip_Satis'],
                    mode='lines+markers',
                    name='Rakip Satış',
                    line=dict(color='#EF4444', width=3),
                    marker=dict(size=8)
                ))
                
                fig_ts.add_trace(go.Scatter(
                    x=monthly_df['DATE'],
                    y=monthly_df['MA_3'],
                    mode='lines',
                    name='3 Aylık Ort.',
                    line=dict(color='#10B981', width=2, dash='dash')
                ))
                
                fig_ts.update_layout(
                    xaxis_title='Tarih',
                    yaxis_title='Satış',
                    height=400,
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig_ts, use_container_width=True)
            
            with col_chart2:
                st.markdown("#### 🎯 Pazar Payı Trendi")
                fig_share = go.Figure()
                
                fig_share.add_trace(go.Scatter(
                    x=monthly_df['DATE'],
                    y=monthly_df['Pazar_Payi_%'],
                    mode='lines+markers',
                    fill='tozeroy',
                    line=dict(color='#8B5CF6', width=2),
                    marker=dict(size=8)
                ))
                
                fig_share.update_layout(
                    xaxis_title='Tarih',
                    yaxis_title='Pazar Payı (%)',
                    height=400
                )
                
                st.plotly_chart(fig_share, use_container_width=True)
            
            st.markdown("---")
            
            st.markdown("#### 📈 Büyüme Analizi")
            
            col_growth1, col_growth2 = st.columns(2)
            
            with col_growth1:
                fig_growth = go.Figure()
                
                colors_pf = ['#10B981' if x > 0 else '#EF4444' for x in monthly_df['PF_Buyume_%']]
                
                fig_growth.add_trace(go.Bar(
                    x=monthly_df['DATE'],
                    y=monthly_df['PF_Buyume_%'],
                    name='PF Büyüme %',
                    marker_color=colors_pf,
                    text=monthly_df['PF_Buyume_%'].apply(lambda x: f'{x:.1f}%' if not pd.isna(x) else ''),
                    textposition='outside'
                ))
                
                fig_growth.update_layout(
                    title='Aylık Büyüme Oranları',
                    xaxis_title='Tarih',
                    yaxis_title='Büyüme (%)',
                    height=400
                )
                
                st.plotly_chart(fig_growth, use_container_width=True)
            
            with col_growth2:
                st.markdown("##### 📊 Büyüme İstatistikleri")
                
                growth_stats = monthly_df[['PF_Buyume_%', 'Rakip_Buyume_%', 'Goreceli_Buyume_%']].describe()
                
                st.dataframe(
                    growth_stats.style.format("{:.2f}"),
                    use_container_width=True
                )
            
            # ML BÖLÜMÜ
            st.markdown("---")
            st.subheader("🤖 GERÇEK Machine Learning Satış Tahmini")
            
            st.info("""
            **Kullanılan Modeller:**
            - Linear Regression
            - Ridge Regression
            - Random Forest Regressor
            
            **Özellikler:**
            - Gecikmeli değerler (lag 1-3)
            - Hareketli ortalamalar (3, 6 ay)
            - Mevsimsellik (sin/cos encoding)
            - Trend index
            """)
            
            forecast_months = st.slider("Tahmin Periyodu (Ay)", 1, 6, 3)
            
            if len(monthly_df) < 10:
                st.warning("⚠️ Tahmin için yeterli veri yok (en az 10 ay gerekli)")
            else:
                with st.spinner("ML modelleri eğitiliyor..."):
                    ml_results, best_model_name, forecast_df = train_ml_models(monthly_df, forecast_months)
                
                if ml_results is None:
                    st.error("❌ Model eğitimi başarısız")
                else:
                    st.markdown("#### 📊 Model Performans Karşılaştırması")
                    
                    perf_data = []
                    for name, metrics in ml_results.items():
                        perf_data.append({
                            'Model': name,
                            'MAE': metrics['MAE'],
                            'RMSE': metrics['RMSE'],
                            'MAPE (%)': metrics['MAPE']
                        })
                    
                    perf_df = pd.DataFrame(perf_data)
                    perf_df = perf_df.sort_values('MAPE (%)')
                    
                    col_perf1, col_perf2 = st.columns([2, 1])
                    
                    with col_perf1:
                        st.dataframe(
                            perf_df.style.format({
                                'MAE': '{:.2f}',
                                'RMSE': '{:.2f}',
                                'MAPE (%)': '{:.2f}'
                            }).background_gradient(subset=['MAPE (%)'], cmap='RdYlGn_r'),
                            use_container_width=True
                        )
                    
                    with col_perf2:
                        st.success(f"**🏆 En İyi Model:**\n\n{best_model_name}")
                        
                        best_mape = ml_results[best_model_name]['MAPE']
                        
                        if best_mape < 10:
                            confidence = "🟢 YÜKSEK"
                        elif best_mape < 20:
                            confidence = "🟡 ORTA"
                        else:
                            confidence = "🔴 DÜŞÜK"
                        
                        st.metric("Güven Seviyesi", confidence)
                        st.metric("MAPE", f"{best_mape:.2f}%")
                    
                    st.markdown("---")
                    
                    col_ml1, col_ml2, col_ml3 = st.columns(3)
                    
                    last_actual = monthly_df['PF_Satis'].iloc[-1]
                    first_forecast = forecast_df['PF_Satis'].iloc[0]
                    change = ((first_forecast - last_actual) / last_actual * 100) if last_actual > 0 else 0
                    
                    with col_ml1:
                        st.metric("📊 Son Gerçek Satış", f"{last_actual:,.0f}")
                    with col_ml2:
                        st.metric("🔮 İlk Tahmin", f"{first_forecast:,.0f}", delta=f"%{change:.1f}")
                    with col_ml3:
                        avg_forecast = forecast_df['PF_Satis'].mean()
                        st.metric("📈 Ort. Tahmin", f"{avg_forecast:,.0f}")
                    
                    st.markdown("---")
                    
                    st.markdown("#### 📈 Gerçek vs ML Tahmini")
                    
                    fig_ml = create_forecast_chart(monthly_df, forecast_df)
                    st.plotly_chart(fig_ml, use_container_width=True)
                    
                    st.markdown("#### 📋 Tahmin Detayları")
                    
                    forecast_display = forecast_df[['YIL_AY', 'PF_Satis', 'Model']].copy()
                    forecast_display.columns = ['Ay', 'Tahmin Edilen Satış', 'Kullanılan Model']
                    forecast_display.index = range(1, len(forecast_display) + 1)
                    
                    st.dataframe(
                        forecast_display.style.format({
                            'Tahmin Edilen Satış': '{:,.0f}'
                        }),
                        use_container_width=True
                    )
                    
                    st.markdown("---")
                    with st.expander("ℹ️ Model Metrikleri Açıklaması"):
                        st.markdown("""
                        **MAE (Mean Absolute Error):**  
                        Ortalama mutlak hata. Düşük olması iyidir.
                        
                        **RMSE (Root Mean Squared Error):**  
                        Kök ortalama kare hata. Büyük hataları daha çok cezalandırır.
                        
                        **MAPE (Mean Absolute Percentage Error):**  
                        Yüzde bazında ortalama hata. En anlaşılır metrik.
                        - <10%: Mükemmel
                        - 10-20%: İyi
                        - >20%: Zayıf
                        
                        **Güven Seviyesi:**  
                        MAPE'e göre otomatik belirlenir.
                        """)
    
    # TAB 5: RAKİP ANALİZİ
    with tab5:
        st.header("📊 Detaylı Rakip Analizi")
        
        comp_data = calculate_competitor_analysis(df_filtered, selected_product, date_filter)
        
        if len(comp_data) == 0:
            st.warning("⚠️ Seçilen filtrelerde veri bulunamadı")
        else:
            col1, col2, col3, col4 = st.columns(4)
            
            avg_pf_share = comp_data['PF_Pay_%'].mean()
            avg_pf_growth = comp_data['PF_Buyume'].mean()
            avg_rakip_growth = comp_data['Rakip_Buyume'].mean()
            win_months = len(comp_data[comp_data['Fark'] > 0])
            
            with col1:
                st.metric("🎯 Ort. PF Pazar Payı", f"%{avg_pf_share:.1f}")
            with col2:
                st.metric("📈 Ort. PF Büyüme", f"%{avg_pf_growth:.1f}")
            with col3:
                st.metric("📉 Ort. Rakip Büyüme", f"%{avg_rakip_growth:.1f}")
            with col4:
                st.metric("🏆 Kazanılan Aylar", f"{win_months}/{len(comp_data)}")
            
            st.markdown("---")
            
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.subheader("💰 Satış Karşılaştırması")
                comp_chart = create_competitor_comparison_chart(comp_data)
                st.plotly_chart(comp_chart, use_container_width=True)
            
            with col_g2:
                st.subheader("📊 Pazar Payı Trendi")
                share_chart = create_market_share_trend(comp_data)
                st.plotly_chart(share_chart, use_container_width=True)
            
            st.markdown("---")
            
            st.subheader("📈 Büyüme Karşılaştırması")
            growth_chart = create_growth_comparison(comp_data)
            st.plotly_chart(growth_chart, use_container_width=True)
            
            st.markdown("---")
            st.subheader("📋 Aylık Performans Detayları")
            
            comp_display = comp_data[['YIL_AY', 'PF', 'Rakip', 'PF_Pay_%', 'PF_Buyume', 'Rakip_Buyume', 'Fark']].copy()
            comp_display.columns = ['Ay', 'PF Satış', 'Rakip Satış', 'PF Pay %', 'PF Büyüme %', 'Rakip Büyüme %', 'Fark %']
            
            def highlight_winner(row):
                if row['Fark %'] > 0:
                    return ['background-color: #d4edda'] * len(row)
                elif row['Fark %'] < 0:
                    return ['background-color: #f8d7da'] * len(row)
                else:
                    return [''] * len(row)
            
            st.dataframe(
                comp_display.style.format({
                    'PF Satış': '{:,.0f}',
                    'Rakip Satış': '{:,.0f}',
                    'PF Pay %': '{:.1f}',
                    'PF Büyüme %': '{:.1f}',
                    'Rakip Büyüme %': '{:.1f}',
                    'Fark %': '{:.1f}'
                }).apply(highlight_winner, axis=1),
                use_container_width=True,
                height=400
            )
            
            st.markdown("---")
            st.subheader("💡 Önemli İçgörüler")
            
            col_i1, col_i2 = st.columns(2)
            
            with col_i1:
                if avg_pf_growth > avg_rakip_growth:
                    st.success(f"✅ PF ortalama %{avg_pf_growth:.1f} büyüme ile rakipten daha hızlı büyüyor")
                else:
                    st.warning(f"⚠️ Rakip ortalama %{avg_rakip_growth:.1f} büyüme ile PF'den daha hızlı büyüyor")
            
            with col_i2:
                if avg_pf_share >= 50:
                    st.success(f"✅ PF %{avg_pf_share:.1f} pazar payı ile lider konumda")
                else:
                    st.warning(f"⚠️ Rakip pazar payında öne geçmiş (%{(100-avg_pf_share):.1f})")
    
    # TAB 6: BCG MATRIX
    with tab6:
        st.header("⭐ BCG Matrix & Yatırım Stratejisi")
        
        bcg_df = calculate_bcg_matrix(df_filtered, selected_product, date_filter)
        
        st.subheader("📊 Portföy Dağılımı")
        
        bcg_counts = bcg_df['BCG_Kategori'].value_counts()
        
        col_bcg1, col_bcg2, col_bcg3, col_bcg4 = st.columns(4)
        
        with col_bcg1:
            star_count = bcg_counts.get("⭐ Star", 0)
            star_pf = bcg_df[bcg_df['BCG_Kategori'] == "⭐ Star"]['PF_Satis'].sum()
            st.metric("⭐ Star", f"{star_count}", delta=f"{star_pf:,.0f} PF")
        
        with col_bcg2:
            cow_count = bcg_counts.get("🐄 Cash Cow", 0)
            cow_pf = bcg_df[bcg_df['BCG_Kategori'] == "🐄 Cash Cow"]['PF_Satis'].sum()
            st.metric("🐄 Cash Cow", f"{cow_count}", delta=f"{cow_pf:,.0f} PF")
        
        with col_bcg3:
            q_count = bcg_counts.get("❓ Question Mark", 0)
            q_pf = bcg_df[bcg_df['BCG_Kategori'] == "❓ Question Mark"]['PF_Satis'].sum()
            st.metric("❓ Question", f"{q_count}", delta=f"{q_pf:,.0f} PF")
        
        with col_bcg4:
            dog_count = bcg_counts.get("🐶 Dog", 0)
            dog_pf = bcg_df[bcg_df['BCG_Kategori'] == "🐶 Dog"]['PF_Satis'].sum()
            st.metric("🐶 Dog", f"{dog_count}", delta=f"{dog_pf:,.0f} PF")
        
        st.markdown("---")
        
        st.subheader("🎯 BCG Matrix")
        
        color_map = {
            "⭐ Star": "#FFD700",
            "🐄 Cash Cow": "#10B981",
            "❓ Question Mark": "#3B82F6",
            "🐶 Dog": "#9CA3AF"
        }
        
        fig_bcg = px.scatter(
            bcg_df,
            x='Goreceli_Pazar_Payi',
            y='Pazar_Buyume_%',
            size='PF_Satis',
            color='BCG_Kategori',
            color_discrete_map=color_map,
            hover_name='Territory',
            hover_data={
                'PF_Satis': ':,.0f',
                'Pazar_Payi_%': ':.1f',
                'Goreceli_Pazar_Payi': ':.2f',
                'Pazar_Buyume_%': ':.1f'
            },
            labels={
                'Goreceli_Pazar_Payi': 'Göreceli Pazar Payı (PF/Rakip)',
                'Pazar_Buyume_%': 'Pazar Büyüme Oranı (%)'
            },
            size_max=50
        )
        
        median_share = bcg_df['Goreceli_Pazar_Payi'].median()
        median_growth = bcg_df['Pazar_Buyume_%'].median()
        
        fig_bcg.add_hline(y=median_growth, line_dash="dash", line_color="rgba(255,255,255,0.4)")
        fig_bcg.add_vline(x=median_share, line_dash="dash", line_color="rgba(255,255,255,0.4)")
        
        fig_bcg.update_layout(
            title='BCG Matrix - Stratejik Konumlandırma',
            height=600,
            plot_bgcolor='#0f172a',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e2e8f0')
        )
        
        st.plotly_chart(fig_bcg, use_container_width=True)
        
        st.markdown("---")
        col_exp1, col_exp2 = st.columns(2)
        
        with col_exp1:
            st.info("""
            **⭐ STARS (Yıldızlar)**
            - Yüksek büyüme + Yüksek pazar payı
            - **Aksiyon:** Yatırımı artır, liderliği sürdür
            """)
            
            st.success("""
            **🐄 CASH COWS (Nakit İnekleri)**
            - Düşük büyüme + Yüksek pazar payı
            - **Aksiyon:** Koru, maliyeti optimize et
            """)
        
        with col_exp2:
            st.warning("""
            **❓ QUESTION MARKS (Soru İşaretleri)**
            - Yüksek büyüme + Düşük pazar payı
            - **Aksiyon:** Agresif yatırım yap veya çık
            """)
            
            st.error("""
            **🐶 DOGS (Köpekler)**
            - Düşük büyüme + Düşük pazar payı
            - **Aksiyon:** Minimal kaynak, çıkışı değerlendir
            """)
        
        st.markdown("---")
        st.subheader("📋 BCG Kategori Detayları")
        
        display_cols_bcg = ['Territory', 'Region', 'BCG_Kategori', 'PF_Satis', 'Pazar_Payi_%', 'Goreceli_Pazar_Payi', 'Pazar_Buyume_%']
        
        bcg_display = bcg_df[display_cols_bcg].copy()
        bcg_display.columns = ['Territory', 'Region', 'BCG', 'PF Satış', 'Pazar Payı %', 'Göreceli Pay', 'Büyüme %']
        bcg_display = bcg_display.sort_values('PF Satış', ascending=False)
        bcg_display.index = range(1, len(bcg_display) + 1)
        
        st.dataframe(
            bcg_display.style.format({
                'PF Satış': '{:,.0f}',
                'Pazar Payı %': '{:.1f}',
                'Göreceli Pay': '{:.2f}',
                'Büyüme %': '{:.1f}'
            }),
            use_container_width=True
        )
    
    # TAB 7: RAPORLAR
    with tab7:
        st.header("📥 Rapor İndirme")
        
        st.markdown("Detaylı analizlerin Excel raporlarını indirebilirsiniz.")
        
        if st.button("📥 Excel Raporu Oluştur", type="primary"):
            with st.spinner("Rapor hazırlanıyor..."):
                terr_perf = calculate_territory_performance(df_filtered, selected_product, date_filter)
                monthly_df = calculate_time_series(df_filtered, selected_product, None, date_filter)
                bcg_df = calculate_bcg_matrix(df_filtered, selected_product, date_filter)
                city_data = calculate_city_performance(df_filtered, selected_product, date_filter)
                comp_data = calculate_competitor_analysis(df_filtered, selected_product, date_filter)
                
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    terr_perf.to_excel(writer, sheet_name='Territory Performans', index=False)
                    monthly_df.to_excel(writer, sheet_name='Zaman Serisi', index=False)
                    bcg_df.to_excel(writer, sheet_name='BCG Matrix', index=False)
                    city_data.to_excel(writer, sheet_name='Şehir Analizi', index=False)
                    comp_data.to_excel(writer, sheet_name='Rakip Analizi', index=False)
                
                st.success("✅ Rapor hazır!")
                
                st.download_button(
                    label="💾 Excel Raporunu İndir",
                    data=output.getvalue(),
                    file_name=f"ticari_portfoy_raporu_{selected_product}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

if __name__ == "__main__":
    main()
