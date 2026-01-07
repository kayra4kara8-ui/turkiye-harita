import plotly.express as px
import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, MultiLineString
import warnings

warnings.filterwarnings("ignore")

# ============================================================
# BÖLGE RENKLERİ (SADECE 5 BÖLGE)
# ============================================================
region_colors = {
    "KUZEY ANADOLU": "#2E8B57",        # yeşil
    "MARMARA": "#2F6FD6",              # mavi
    "İÇ ANADOLU": "#8B6B4A",           # açık kahve
    "BATI ANADOLU": "#2BB0A6",         # turkuaz
    "GÜNEY DOĞU ANADOLU": "#A05A2C"    # koyu kahve
}

# ============================================================
# DATA HAZIR (df ve turkey_map zaten yüklü varsayılıyor)
# turkey_map: GeoJSON -> CITY_CLEAN kolonu var
# df: Şehir, Bölge, Ticaret Müdürü, Kutu Adet
# ============================================================

# Şehir–Geo eşleşmesi
merged_region = turkey_map.merge(
    df[["Şehir", "Bölge", "Ticaret Müdürü", "Kutu Adet"]].drop_duplicates(),
    left_on="CITY_CLEAN",
    right_on="Şehir",
    how="left"
)

merged_region["Kutu Adet"] = merged_region["Kutu Adet"].fillna(0)
merged_region["Bölge"] = merged_region["Bölge"].fillna("DİĞER")

# SADECE 5 BÖLGEYİ TUT
merged_region = merged_region[
    merged_region["Bölge"].isin(region_colors.keys())
]

# ============================================================
# BÖLGE HARİTASI (DISSOLVE)
# ============================================================
region_map = (
    merged_region
    .dissolve(by="Bölge", aggfunc={"Kutu Adet": "sum"})
    .reset_index()
)

# ============================================================
# CHOROPLETH (BÖLGELER)
# ============================================================
fig = px.choropleth(
    region_map,
    geojson=region_map.__geo_interface__,
    locations="Bölge",
    featureidkey="properties.Bölge",
    color="Bölge",
    color_discrete_map=region_colors,
    hover_name="Bölge",
    hover_data={"Kutu Adet": ":,"}
)

fig.update_geos(fitbounds="locations", visible=False)
fig.update_layout(coloraxis_showscale=False)

# ============================================================
# BÖLGE LABEL (MERKEZ)
# ============================================================
region_proj = region_map.to_crs(3857)
region_proj["centroid"] = region_proj.geometry.centroid
region_lbl = region_proj.to_crs(region_map.crs)

fig.add_scattergeo(
    lon=region_lbl.centroid.x,
    lat=region_lbl.centroid.y,
    text=[
        f"<b>{r['Bölge']}</b><br>{int(r['Kutu Adet']):,}"
        for _, r in region_lbl.iterrows()
    ],
    mode="text",
    textfont=dict(size=14, color="black", family="Arial Black"),
    showlegend=False,
    hoverinfo="skip"
)

# ============================================================
# ŞEHİR HOVER NOKTALARI
# ============================================================
city_proj = merged_region.to_crs(3857)
city_proj["centroid"] = city_proj.geometry.centroid
city_pts = city_proj.to_crs(merged_region.crs)

fig.add_scattergeo(
    lon=city_pts.centroid.x,
    lat=city_pts.centroid.y,
    mode="markers",
    marker=dict(size=6, color="rgba(0,0,0,0)"),
    hoverinfo="text",
    text=[
        f"<b>{r['CITY_CLEAN']}</b><br>"
        f"Bölge: {r['Bölge']}<br>"
        f"Ticaret Müdürü: {r['Ticaret Müdürü']}<br>"
        f"Kutu Adet: {int(r['Kutu Adet']):,}"
        for _, r in city_pts.iterrows()
    ],
    showlegend=False
)

# ============================================================
# ŞEHİR SINIRLARI
# ============================================================
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

all_lons, all_lats = [], []
for g in merged_region.geometry.boundary:
    lo, la = lines_to_lonlat(g)
    all_lons += lo
    all_lats += la

fig.add_scattergeo(
    lon=all_lons,
    lat=all_lats,
    mode="lines",
    line=dict(width=0.8, color="rgba(60,60,60,0.7)"),
    hoverinfo="skip",
    showlegend=False
)

# ============================================================
# BAŞLIK
# ============================================================
fig.update_layout(
    title="Türkiye – Bölge Bazlı Kutu Adetleri",
    margin=dict(l=0, r=0, t=60, b=0),
    paper_bgcolor="white",
    plot_bgcolor="white"
)

fig.show()
