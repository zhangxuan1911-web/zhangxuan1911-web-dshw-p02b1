import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'FangSong']
plt.rcParams['axes.unicode_minus'] = False

import seaborn as sns
import plotly.graph_objects as go
from plotly.subplots import make_subplots

BASE = Path(__file__).resolve().parents[1]
DATA_RAW = BASE / 'data_raw'
DATA_CLEAN = BASE / 'data_clean'
OUTPUT = BASE / 'output'
OUTPUT.mkdir(exist_ok=True)

# ============================================================
# 颜色
# ============================================================
MORANDI_BLUES = [
    '#C5D4E0', '#B0C4D8', '#9AB4CC', '#85A3BB',
    '#7093AA', '#5A7A8A', '#456A7A', '#305A6A', '#1B4A5A',
]
DIVERGING = [
    [0.0, '#C97C6A'],
    [0.25, '#E8C5B8'],
    [0.5, '#F5F0EB'],
    [0.75, '#9AB4CC'],
    [1.0, '#5A7A8A'],
]
REGION_LABEL_COLORS = {'东部': '#5A7A8A', '东北': '#7093AA', '中部': '#9AB4CC', '西部': '#C5D4E0'}

# 官方四大板块
REGIONS = {
    '东部': ['北京', '天津', '河北', '上海', '江苏', '浙江', '福建', '山东', '广东', '海南'],
    '东北': ['辽宁', '吉林', '黑龙江'],
    '中部': ['山西', '安徽', '江西', '河南', '湖北', '湖南'],
    '西部': ['内蒙古', '广西', '重庆', '四川', '贵州', '云南', '西藏', '陕西', '甘肃', '青海', '宁夏', '新疆'],
}

# ============================================================
# 加载数据
# ============================================================
df = pd.read_csv(DATA_CLEAN / 'gdp_panel_long_2011_2024.csv', encoding='utf-8-sig')
df_cross = pd.read_csv(DATA_CLEAN / 'provincial_indicators_2025_clean.csv', encoding='utf-8-sig')

with open(DATA_RAW / 'china_provinces.geojson', 'r', encoding='utf-8') as f:
    china_geojson = json.load(f)

# GeoJSON 名称映射
geojson_short_to_full = {}
for feat in china_geojson['features']:
    full = feat['properties']['name']
    short = full
    for suf in ['省', '市', '壮族自治区', '回族自治区', '维吾尔自治区', '自治区', '特别行政区']:
        if short.endswith(suf):
            short = short[:-len(suf)]
            break
    geojson_short_to_full[short] = full
overrides = {'内蒙古': '内蒙古自治区', '广西': '广西壮族自治区',
             '宁夏': '宁夏回族自治区', '新疆': '新疆维吾尔自治区',
             '西藏': '西藏自治区', '香港': '香港特别行政区', '澳门': '澳门特别行政区'}
geojson_short_to_full.update(overrides)

df['name_geojson'] = df['province'].map(geojson_short_to_full)

# 省份中心点
province_centers = {}
for feat in china_geojson['features']:
    p = feat['properties']
    matched_short = None
    for s, f in geojson_short_to_full.items():
        if f == p['name']:
            matched_short = s
            break
    if matched_short:
        province_centers[matched_short] = {'lon': float(p['cp'][0]), 'lat': float(p['cp'][1])}

years_all = sorted(df['year'].unique())
years_heat = [y for y in years_all if y >= 2013]

# ============================================================
# 热力图数据准备：按地区分组
# ============================================================
# 计算各省平均增速
avg_growth = df[df['year'].isin(years_heat)].groupby('province')['gdp_growth'].mean()

ordered_provinces = []
region_boundaries = []
running_count = 0
for region, provs in REGIONS.items():
    # 只取在数据中存在的省份
    avail = [p for p in provs if p in avg_growth.index]
    avail.sort(key=lambda p: avg_growth[p], reverse=True)
    ordered_provinces.extend(avail)
    running_count += len(avail)
    region_boundaries.append((region, running_count))

growth_wide = df[df['year'].isin(years_heat)].pivot_table(
    index='province', columns='year', values='gdp_growth'
)
growth_wide = growth_wide.reindex(ordered_provinces)

z_vals = growth_wide.values
z_flat = z_vals[~np.isnan(z_vals)]
zmin_data = np.floor(z_flat.min())
zmax_data = np.ceil(z_flat.max())
zmid = round(np.median(z_flat), 1)

# 文本矩阵
text_mat = [[f'{v:.1f}' if not np.isnan(v) else '' for v in row] for row in z_vals]

# ============================================================
# 构建主 Figure (2 行 2 列)
# ============================================================
fig = make_subplots(
    rows=2, cols=2,
    column_widths=[0.6, 0.4],
    row_heights=[0.55, 0.45],
    specs=[
        [{'type': 'scattergeo'}, {'type': 'bar'}],
        [{'type': 'heatmap', 'colspan': 2}, None],
    ],
    subplot_titles=(
        '中国各省 GDP 分布',
        'GDP 排名',
        '各省 GDP 增速热力图（2013-2024）· 红色虚线框 = 滑块当前年份',
    ),
    horizontal_spacing=0.05,
    vertical_spacing=0.1,
)

# ===================== 第 1 行：地图 =====================
first = df[df['year'] == years_all[0]].sort_values('gdp', ascending=False)
label_df = first[first['province'].isin(province_centers)].copy()
label_df['lon'] = label_df['province'].map(lambda x: province_centers[x]['lon'])
label_df['lat'] = label_df['province'].map(lambda x: province_centers[x]['lat'])
gdp_max_all = df['gdp'].max()

choropleth = go.Choropleth(
    geojson=china_geojson,
    locations=first['name_geojson'],
    z=first['gdp'],
    featureidkey='properties.name',
    colorscale=MORANDI_BLUES,
    zmin=0,
    zmax=gdp_max_all * 1.05,
    colorbar_title='GDP（亿元）',
    colorbar=dict(thickness=14, len=0.55, x=0.44, y=0.68,
                  tickfont=dict(size=10), title_font=dict(size=11)),
    hovertemplate='<b>%{text}</b><br>GDP: %{z:.1f} 亿元<br><extra></extra>',
    text=first['province'],
    marker_line_width=0.5,
    marker_line_color='#F5F0EB',
)
fig.add_trace(choropleth, row=1, col=1)

# 省名标注
scatter_labels = go.Scattergeo(
    lon=label_df['lon'], lat=label_df['lat'],
    text=label_df['province'],
    mode='text',
    textfont=dict(family='Microsoft YaHei, SimHei', size=9, color='#2C3E50'),
    hoverinfo='skip',
)
fig.add_trace(scatter_labels, row=1, col=1)

# ===================== 第 1 行：柱状图 =====================
first_bar = first.sort_values('gdp', ascending=False)

bar_chart = go.Bar(
    x=first_bar['gdp'],
    y=first_bar['province'],
    orientation='h',
    marker=dict(
        color=first_bar['gdp'],
        colorscale=MORANDI_BLUES,
        cmin=0, cmax=gdp_max_all * 1.05,
        line=dict(width=0.3, color='#F5F0EB'),
    ),
    hovertemplate='<b>%{y}</b><br>GDP: %{x:.1f} 亿元<br><extra></extra>',
    showlegend=False,
)
fig.add_trace(bar_chart, row=1, col=2)

# ===================== 第 2 行：热力图 =====================
heatmap = go.Heatmap(
    z=z_vals,
    x=list(years_heat),
    y=ordered_provinces,
    text=text_mat,
    texttemplate='%{text}',
    textfont=dict(size=7.5, color='#2C3E50'),
    colorscale=DIVERGING,
    zmin=zmin_data,
    zmax=zmax_data,
    zmid=zmid,
    colorbar=dict(
        title='增速 (%)', thickness=12, len=0.4,
        x=1.01, y=0.22,
        tickfont=dict(size=9),
    ),
    hovertemplate='省份: %{y}<br>年份: %{x}<br>增速: %{z:.1f}%<extra></extra>',
)
fig.add_trace(heatmap, row=2, col=1)

# ===================== 热力区域分隔线 =====================
separator_shapes = []
for region, count in region_boundaries:
    if count < len(ordered_provinces):
        separator_shapes.append(dict(
            type='line',
            x0=-0.5, x1=len(years_heat) - 0.5,
            y0=count - 0.5, y1=count - 0.5,
            line=dict(color='#AAAAAA', width=1.2),
            xref='x3', yref='y3',
        ))

# 区域名称标注（在 y 轴左侧）
region_annotations = []
running = 0
for region, provs in REGIONS.items():
    avail = [p for p in provs if p in avg_growth.index]
    mid_idx = running + len(avail) // 2
    running += len(avail)
    region_annotations.append(dict(
        x=-0.8, y=mid_idx,
        text=f'<b>{region}</b>',
        showarrow=False,
        xref='x3', yref='y3',
        font=dict(size=10, color='#5A7A8A'),
        xanchor='right', yanchor='middle',
    ))

# ===================== Frames =====================
frames = []
for y in years_all:
    sub = df[df['year'] == y].sort_values('gdp', ascending=False)
    bar_sub = sub.sort_values('gdp', ascending=False)
    data = [
        go.Choropleth(
            locations=sub['name_geojson'], z=sub['gdp'],
            text=sub['province'], zmin=0, zmax=gdp_max_all * 1.05,
            colorscale=MORANDI_BLUES,
            marker_line_width=0.5, marker_line_color='#F5F0EB',
        ),
        go.Bar(
            x=bar_sub['gdp'], y=bar_sub['province'],
            orientation='h',
            marker=dict(
                color=bar_sub['gdp'],
                colorscale=MORANDI_BLUES,
                cmin=0, cmax=gdp_max_all * 1.05,
                line=dict(width=0.3, color='#F5F0EB'),
            ),
        ),
    ]

    # 年份高亮矩形
    shapes = list(separator_shapes)
    if y in years_heat:
        yi = years_heat.index(y)
        shapes.append(dict(
            type='rect',
            x0=yi - 0.5, x1=yi + 0.5,
            y0=-0.5, y1=len(ordered_provinces) - 0.5,
            line=dict(color='#C0392B', width=2.5, dash='dash'),
            fillcolor='rgba(0,0,0,0)',
            xref='x3', yref='y3',
        ))

    frame = go.Frame(
        name=str(y), traces=[0, 2],
        data=data,
        layout=go.Layout(shapes=shapes),
    )
    frames.append(frame)

fig.frames = frames

# ===================== Slider =====================
slider_steps = []
for y in years_all:
    slider_steps.append(dict(
        method='animate',
        args=[[str(y)], dict(mode='immediate', frame=dict(duration=300, redraw=True),
                              transition=dict(duration=200))],
        label=str(y),
    ))

sliders = [dict(
    active=0, steps=slider_steps,
    currentvalue=dict(prefix='年份: ', font=dict(size=14, color='#2C3E50')),
    pad=dict(t=20, b=10), len=0.7, x=0.15,
    bgcolor='#EEEEEE', activebgcolor='#5A7A8A',
)]

# ===================== 布局 =====================
fig.update_layout(
    title=dict(
        text='中国省级 GDP 时空演变与增速热力图（2011-2024）',
        font=dict(size=16, family='Microsoft YaHei, SimHei', color='#2C3E50'),
        x=0.5, y=0.98,
    ),
    sliders=sliders,
    geo=dict(
        scope='asia',
        projection=dict(type='natural earth'),
        center=dict(lat=35, lon=105),
        fitbounds='locations',
        showframe=False, showcountries=False,
        coastlinecolor='rgba(0,0,0,0)',
        landcolor='rgba(0,0,0,0)',
        bgcolor='#F5F0EB',
    ),
    width=1200, height=850,
    paper_bgcolor='#F5F0EB',
    hovermode='closest',
    font=dict(family='Microsoft YaHei, SimHei, Arial'),
    margin=dict(t=70, b=60, l=40, r=40),
    annotations=[
        # 区域标注（热力图左侧）
        *region_annotations,
        # GDP 单位说明
        dict(
            x=0.22, y=0.06,
            text='单位：亿元（当年价）',
            showarrow=False,
            font=dict(size=9, color='#888888'),
            xref='paper', yref='paper',
        ),
    ],
)

# ---- 柱状图 x 轴 ----
fig.update_xaxes(
    row=1, col=2,
    title_text='GDP（亿元）',
    title_font=dict(size=11),
    gridcolor='#E0DCD5',
    zeroline=False,
    range=[0, gdp_max_all * 1.08],
    tickformat=',.0f',
)
fig.update_yaxes(
    row=1, col=2,
    gridcolor='#E0DCD5',
    zeroline=False,
)

# ---- 热力图坐标轴 ----
fig.update_xaxes(row=2, col=1, title_text='年份', tickvals=years_heat,
                 gridcolor='#E0DCD5')
fig.update_yaxes(row=2, col=1, gridcolor='#E0DCD5',
                 tickvals=ordered_provinces, ticktext=ordered_provinces)

# ===================== 输出 =====================
fig.write_html(
    OUTPUT / 'china_provincial_economy_dashboard.html',
    include_plotlyjs='cdn',
    auto_open=False,
)
print(f'  -> output/china_provincial_economy_dashboard.html  ({fig}...saved)')


# ============================================================
# 以下为单独输出的静态图（保持不变）
# ============================================================
print('>>> 生成静态图（共 8 张）...')

# --- C1：东中西折线图 ---
east_reg = ['北京','天津','河北','上海','江苏','浙江','福建','山东','广东','海南','辽宁']
central_reg = ['山西','吉林','黑龙江','安徽','江西','河南','湖北','湖南']
west_reg = ['内蒙古','广西','重庆','四川','贵州','云南','西藏','陕西','甘肃','青海','宁夏','新疆']

def region_of(p):
    if p in east_reg: return '东部'
    if p in central_reg: return '中部'
    if p in west_reg: return '西部'
    return '其他'

df_reg = df.copy()
df_reg['region'] = df_reg['province'].apply(region_of)
region_avg = df_reg.groupby(['region', 'year'])['gdp_growth'].mean().reset_index()
region_avg = region_avg[region_avg['year'].between(2011, 2024)]

fig_l, ax_l = plt.subplots(figsize=(11, 5))
colors_line = {'东部': '#5A7A8A', '中部': '#8DA8BF', '西部': '#A0B8CC'}
markers = {'东部': 'o', '中部': 's', '西部': '^'}
for region, grp in region_avg.groupby('region'):
    ax_l.plot(grp['year'], grp['gdp_growth'], label=region,
              color=colors_line[region], linewidth=2,
              marker=markers[region], markersize=5,
              markerfacecolor='white', markeredgewidth=1.5)
ax_l.set_title('东中西部 GDP 平均增速对比（2011-2024）', fontsize=13)
ax_l.set_xlabel('年份'); ax_l.set_ylabel('GDP 增速（%）')
ax_l.legend(frameon=True, fancybox=True, fontsize=11)
ax_l.grid(True, alpha=0.3); ax_l.set_xlim(2010.5, 2024.5)
fig_l.tight_layout()
fig_l.savefig(OUTPUT / 'fig_coastal_inland.png', dpi=200, bbox_inches='tight')
plt.close(fig_l)

# --- C2：GDP Top15 ---
top15 = df_cross.sort_values('GDP(亿元)', ascending=False).head(15)
fig_t, ax_t = plt.subplots(figsize=(10, 6))
colors_top = ['#5A7A8A', '#6B8AA3', '#7A9AB5', '#8DA8BF', '#A0B8CC', '#B0C4D8',
              '#C5D4E0', '#B0C4D8', '#9AB4CC', '#85A3BB', '#7093AA', '#5A7A8A',
              '#456A7A', '#305A6A', '#1B4A5A'][:15]
ax_t.barh(range(len(top15)), top15['GDP(亿元)'].values, color=colors_top, edgecolor='white', height=0.7)
ax_t.set_yticks(range(len(top15)))
ax_t.set_yticklabels(top15['province'].values, fontsize=10)
ax_t.invert_yaxis(); ax_t.set_xlabel('GDP（亿元）', fontsize=12)
ax_t.set_title('2025 年各省 GDP Top15', fontsize=14)
ax_t.grid(axis='x', alpha=0.3)
for i, (_, row) in enumerate(top15.iterrows()):
    ax_t.text(row['GDP(亿元)'] + 200, i, f'{row["GDP(亿元)"]:,.0f}',
              va='center', fontsize=9, color='#555')
fig_t.tight_layout()
fig_t.savefig(OUTPUT / 'fig01_2025_gdp_top15.png', dpi=200, bbox_inches='tight')
plt.close(fig_t)

# --- C3：区域占比 ---
region_gdp = df_cross.groupby('region')['GDP(亿元)'].sum().sort_values(ascending=False)
fig_p, ax_p = plt.subplots(figsize=(7, 7))
colors_pie = [REGION_LABEL_COLORS[r] for r in region_gdp.index]
wedges, texts, autotexts = ax_p.pie(
    region_gdp.values, labels=region_gdp.index, autopct='%1.1f%%',
    startangle=90, colors=colors_pie,
    wedgeprops=dict(edgecolor='white', linewidth=2), textprops=dict(fontsize=12))
for at in autotexts: at.set_fontsize(11); at.set_color('white')
ax_p.set_title('2025 年四大区域 GDP 占比', fontsize=14)
fig_p.tight_layout()
fig_p.savefig(OUTPUT / 'fig02_2025_region_gdp_share.png', dpi=200, bbox_inches='tight')
plt.close(fig_p)

# --- C4：产业结构 ---
sector_cols = ['第一产业(亿元)', '第二产业(亿元)', '第三产业(亿元)']
sector_labels = ['第一产业', '第二产业', '第三产业']
sector_colors = ['#C5D4E0', '#8DA8BF', '#5A7A8A']
df_sector = df_cross.sort_values('GDP(亿元)', ascending=True)
fig_s, ax_s = plt.subplots(figsize=(12, 8))
bottom = np.zeros(len(df_sector))
for i, col in enumerate(sector_cols):
    vals = df_sector[col].fillna(0).values
    ax_s.barh(range(len(df_sector)), vals, left=bottom,
              label=sector_labels[i], color=sector_colors[i],
              edgecolor='white', linewidth=0.3, height=0.7)
    bottom += vals
ax_s.set_yticks(range(len(df_sector)))
ax_s.set_yticklabels(df_sector['province'].values, fontsize=9)
ax_s.invert_yaxis(); ax_s.set_xlabel('GDP（亿元）', fontsize=12)
ax_s.set_title('2025 年各省产业结构', fontsize=14)
ax_s.legend(loc='lower right', fontsize=11); ax_s.grid(axis='x', alpha=0.2)
fig_s.tight_layout()
fig_s.savefig(OUTPUT / 'fig03_2025_sector_structure.png', dpi=200, bbox_inches='tight')
plt.close(fig_s)

# --- C5：GDP-收入散点 ---
fig_sc, ax_sc = plt.subplots(figsize=(9, 7))
ax_sc.scatter(df_cross['GDP(亿元)'], df_cross['全体居民可支配收入(元)'],
              c=range(len(df_cross)), cmap='Blues', s=80,
              edgecolors='white', linewidth=0.8, alpha=0.85, zorder=3)
for _, row in df_cross.iterrows():
    ax_sc.annotate(row['province'], (row['GDP(亿元)'], row['全体居民可支配收入(元)']),
                   fontsize=8, alpha=0.8, xytext=(5, 5), textcoords='offset points')
ax_sc.set_xlabel('GDP（亿元）', fontsize=12)
ax_sc.set_ylabel('全体居民可支配收入（元）', fontsize=12)
ax_sc.set_title('2025 年各省 GDP 与居民收入水平', fontsize=14)
ax_sc.grid(True, alpha=0.3)
fig_sc.tight_layout()
fig_sc.savefig(OUTPUT / 'fig04_2025_gdp_income_scatter.png', dpi=200, bbox_inches='tight')
plt.close(fig_sc)

# --- C6：Top8 趋势 ---
top8_provs = df[df['year'] == years_all[-1]].sort_values('gdp', ascending=False).head(8)['province'].tolist()
df_top8 = df[df['province'].isin(top8_provs)]
fig_t8, ax_t8 = plt.subplots(figsize=(12, 6))
for i, prov in enumerate(top8_provs):
    pdata = df_top8[df_top8['province'] == prov]
    ax_t8.plot(pdata['year'], pdata['gdp'], label=prov,
               color=MORANDI_BLUES[i % len(MORANDI_BLUES)],
               linewidth=2, marker='o', markersize=4)
ax_t8.set_title('GDP 总量 Top8 省份趋势（2011-2024）', fontsize=14)
ax_t8.set_xlabel('年份'); ax_t8.set_ylabel('GDP（亿元）')
ax_t8.legend(fontsize=10, ncol=2)
ax_t8.grid(True, alpha=0.3)
fig_t8.tight_layout()
fig_t8.savefig(OUTPUT / 'fig05_2011_2024_gdp_trends_top8.png', dpi=200, bbox_inches='tight')
plt.close(fig_t8)

# --- C7：排名变化 ---
key_years = [2011, 2015, 2020, 2024]
rank_wide = df[df['year'].isin(key_years)].pivot_table(
    index='province', columns='year', values='gdp'
).rank(ascending=False, method='min')
rank_wide = rank_wide.sort_values(2024, ascending=True)
fig_r, ax_r = plt.subplots(figsize=(10, 14))
sns.heatmap(rank_wide, annot=True, fmt='.0f',
            cmap=sns.light_palette('#5A7A8A', as_cmap=True, reverse=False),
            linewidths=0.5, ax=ax_r,
            cbar_kws={'label': '排名', 'shrink': 0.5},
            annot_kws={'size': 8})
ax_r.set_title('各省 GDP 排名变化（2011/2015/2020/2024）', fontsize=14)
fig_r.tight_layout()
fig_r.savefig(OUTPUT / 'fig06_gdp_rank_change.png', dpi=200, bbox_inches='tight')
plt.close(fig_r)

# ============================================================
print()
print('=' * 50)
print('  可视化完成！')
print('=' * 50)
for f in sorted(OUTPUT.iterdir()):
    sz = f.stat().st_size / 1024
    print(f'  {f.name:45s} {sz:>8.1f} KB')
