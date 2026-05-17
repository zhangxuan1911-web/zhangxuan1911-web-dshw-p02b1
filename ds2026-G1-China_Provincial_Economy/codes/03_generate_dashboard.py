import json, math
from pathlib import Path
import pandas as pd
import numpy as np

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, (np.ndarray,)): return obj.tolist()
        if isinstance(obj, (np.bool_,)): return bool(obj)
        return super().default(obj)

BASE = Path(__file__).resolve().parents[1]
DATA_CLEAN = BASE / 'data_clean'
OUTPUT = BASE / 'output'
OUTPUT.mkdir(exist_ok=True)

df = pd.read_csv(DATA_CLEAN / 'gdp_panel_long_2011_2024.csv', encoding='utf-8-sig')
cross = pd.read_csv(DATA_CLEAN / 'provincial_indicators_2025_clean.csv', encoding='utf-8-sig')

# ============================================================
# 准备 JS 数据
# ============================================================
years = sorted(df['year'].unique())
provinces = sorted(df['province'].unique())

# GDP_DATA: { year: { province: gdp } }
gdp_data = {}
for y in years:
    sub = df[df['year'] == y]
    gdp_data[str(y)] = {row['province']: row['gdp'] for _, row in sub.iterrows()}

# TABLE_DATA
regions = {}
for _, row in cross.iterrows():
    regions[row['province']] = row['region']
    cross_data = row

# Build full cross table
table_data = []
for _, r in cross.iterrows():
    table_data.append({
        'province': r['province'],
        'region': r['region'],
        'gdp': None if pd.isna(r['GDP(亿元)']) else r['GDP(亿元)'],
        'growth': None if pd.isna(r['GDP增速(%)']) else r['GDP增速(%)'],
        'income': None if pd.isna(r['全体居民可支配收入(元)']) else r['全体居民可支配收入(元)'],
        'urban_income': None if pd.isna(r['城镇可支配收入(元)']) else r['城镇可支配收入(元)'],
        'rural_income': None if pd.isna(r['农村可支配收入(元)']) else r['农村可支配收入(元)'],
        'retail': None if pd.isna(r['社消零售总额(亿元)']) else r['社消零售总额(亿元)'],
        'retail_growth': None if pd.isna(r['社消增速(%)']) else r['社消增速(%)'],
        'population': None if pd.isna(r['常住人口(万人)']) else r['常住人口(万人)'],
        'urban_rate': None if pd.isna(r['城镇化率(%)']) else r['城镇化率(%)'],
        'primary': None if pd.isna(r['第一产业(亿元)']) else r['第一产业(亿元)'],
        'secondary': None if pd.isna(r['第二产业(亿元)']) else r['第二产业(亿元)'],
        'tertiary': None if pd.isna(r['第三产业(亿元)']) else r['第三产业(亿元)'],
    })

# 产业占比
for d in table_data:
    total = (d['primary'] or 0) + (d['secondary'] or 0) + (d['tertiary'] or 0)
    if total > 0:
        d['tertiary_pct'] = round(d['tertiary'] / total * 100, 2) if d['tertiary'] else 0
        d['secondary_pct'] = round(d['secondary'] / total * 100, 2) if d['secondary'] else 0
    else:
        d['tertiary_pct'] = 0
        d['secondary_pct'] = 0

# REGION_SUMMARY
region_order = ['东部', '东北', '中部', '西部']
region_summary = {}
for d in table_data:
    r = d['region']
    if r not in region_summary:
        region_summary[r] = {'gdp': 0, 'retail': 0, 'growth_sum': 0, 'growth_n': 0,
                             'primary': 0, 'secondary': 0, 'tertiary': 0, 'n': 0}
    rs = region_summary[r]
    rs['gdp'] += d['gdp'] or 0
    rs['retail'] += d['retail'] or 0
    rs['primary'] += d['primary'] or 0
    rs['secondary'] += d['secondary'] or 0
    rs['tertiary'] += d['tertiary'] or 0
    rs['n'] += 1
    if d['growth'] is not None:
        rs['growth_sum'] += d['growth']
        rs['growth_n'] += 1

region_data = []
for r in region_order:
    rs = region_summary.get(r, {})
    total = (rs.get('primary', 0) + rs.get('secondary', 0) + rs.get('tertiary', 0)) or 1
    region_data.append({
        'region': r,
        'gdp': round(rs.get('gdp', 0), 2),
        'provinces': rs.get('n', 0),
        'retail': round(rs.get('retail', 0), 2),
        'avgGrowth': round(rs.get('growth_sum', 0) / rs.get('growth_n', 1), 2) if rs.get('growth_n', 0) > 0 else 0,
        'primary': round(rs.get('primary', 0) / total * 100, 2),
        'secondary': round(rs.get('secondary', 0) / total * 100, 2),
        'tertiary': round(rs.get('tertiary', 0) / total * 100, 2),
    })

# MAP_NAMES (short -> full)
province_map = {
    '北京': '北京市', '天津': '天津市', '河北': '河北省', '山西': '山西省',
    '内蒙古': '内蒙古自治区', '辽宁': '辽宁省', '吉林': '吉林省', '黑龙江': '黑龙江省',
    '上海': '上海市', '江苏': '江苏省', '浙江': '浙江省', '安徽': '安徽省',
    '福建': '福建省', '江西': '江西省', '山东': '山东省', '河南': '河南省',
    '湖北': '湖北省', '湖南': '湖南省', '广东': '广东省', '广西': '广西壮族自治区',
    '海南': '海南省', '重庆': '重庆市', '四川': '四川省', '贵州': '贵州省',
    '云南': '云南省', '西藏': '西藏自治区', '陕西': '陕西省', '甘肃': '甘肃省',
    '青海': '青海省', '宁夏': '宁夏回族自治区', '新疆': '新疆维吾尔自治区',
}

# Heatmap data: growth rate matrix
heat_years = [int(y) for y in years if y >= 2013]
growth_wide = df[df['year'].isin(heat_years)].pivot_table(
    index='province', columns='year', values='gdp_growth'
)

# 地区分组 & 排序
region_provs = {
    '东部': ['北京','天津','河北','上海','江苏','浙江','福建','山东','广东','海南'],
    '东北': ['辽宁','吉林','黑龙江'],
    '中部': ['山西','安徽','江西','河南','湖北','湖南'],
    '西部': ['内蒙古','广西','重庆','四川','贵州','云南','西藏','陕西','甘肃','青海','宁夏','新疆'],
}
ordered_heat = []
region_breaks = []
for r in region_order:
    avail = [p for p in region_provs[r] if p in growth_wide.index]
    avail.sort(key=lambda p: growth_wide.loc[p].mean(), reverse=True)
    ordered_heat.extend(avail)
    region_breaks.append(len(ordered_heat))

heat_labels = ordered_heat
heat_data = []
for i, p in enumerate(ordered_heat):
    row = growth_wide.loc[p]
    for j, y in enumerate(heat_years):
        v = row[y]
        if not np.isnan(v):
            heat_data.append([j, i, round(v, 2)])

# 计算 heatmap 范围
all_vals = growth_wide.values.flatten()
all_vals = all_vals[~np.isnan(all_vals)]
heat_zmin = math.floor(all_vals.min())
heat_zmax = math.ceil(all_vals.max())
heat_zmid = round(float(np.median(all_vals)), 1)

# REGION_COLORS (用户指定的配色)
REGION_COLORS = {
    '东部': '#4f7fa6',   # 蓝色
    '东北': '#8e7aa8',   # 紫色
    '中部': '#6f9f8f',   # 绿色
    '西部': '#c78b54',   # 金色/黄色
}

# ============================================================
# 构建 HTML
# ============================================================
html = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>中国省级经济面板数据整理与可视化</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
<style>
:root {
  --primary: #27496d;
  --secondary: #4f7fa6;
  --accent: #6f9f8f;
  --warm: #c78b54;
  --bg: #f5f7fa;
  --card: #ffffff;
  --text: #263445;
  --muted: #6b7785;
  --border: #dfe6ee;
  --blue-1: #dfeaf3;
  --blue-2: #9fbcd1;
  --blue-3: #5f8fb6;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Microsoft YaHei','PingFang SC',Arial,sans-serif;
  color: var(--text); background: var(--bg); line-height: 1.7;
}
.header {
  background: linear-gradient(135deg,#27496d 0%,#1f3c58 58%,#315d69 100%);
  color: white; padding: 38px 60px 36px;
}
.header-meta {
  display: flex; flex-wrap: wrap; gap: 18px; margin-bottom: 14px;
  font-size: 13px; opacity: .82;
}
.header h1 { margin: 0 0 10px; font-size: 31px; letter-spacing: .5px; }
.header p { max-width: 820px; margin: 0; font-size: 15px; opacity: .9; }
.team-card {
  max-width: 980px; margin: 16px 0 12px; padding: 13px 16px;
  border: 1px solid rgba(255,255,255,.24);
  background: rgba(255,255,255,.10); border-radius: 8px; font-size: 14px; line-height: 1.9;
}
.badge {
  display: inline-block; margin-top: 15px; padding: 4px 12px; border-radius: 20px;
  border: 1px solid rgba(255,255,255,.32);
  background: rgba(255,255,255,.12); font-size: 12px;
}
.nav {
  position: sticky; top: 0; z-index: 20;
  display: flex; flex-wrap: wrap; padding: 0 60px;
  background: var(--card); border-bottom: 1px solid var(--border);
  box-shadow: 0 2px 10px rgba(20,39,57,.07);
}
.nav a {
  display: block; padding: 15px 18px 13px; color: var(--muted);
  text-decoration: none; font-size: 14px;
  border-bottom: 3px solid transparent; cursor: pointer;
}
.nav a:hover, .nav a.active { color: var(--primary); border-bottom-color: var(--primary); }
.container { max-width: 1400px; margin: 0 auto; padding: 38px 60px; }
.section { margin-bottom: 48px; }
.section-header { display: flex; gap: 12px; align-items: center; margin-bottom: 22px; }
.section-num {
  width: 32px; height: 32px; border-radius: 50%;
  background: var(--primary); color: white;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 14px; flex: 0 0 auto;
}
.section-title { color: var(--primary); font-size: 20px; font-weight: 700; }
.section-desc { color: var(--muted); font-size: 13px; margin-top: 2px; }
.chart-card {
  background: var(--card); border: 1px solid var(--border);
  border-radius: 10px; box-shadow: 0 2px 10px rgba(29,48,66,.045);
  padding: 26px; margin-bottom: 22px;
}
.chart-title { font-size: 16px; font-weight: 700; margin-bottom: 5px; }
.chart-subtitle { color: var(--muted); font-size: 13px; margin-bottom: 18px; }
.chart-box { width: 100%; }
.controls { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin-bottom: 14px; }
.ctrl-label { color: var(--muted); font-size: 13px; }
.ctrl-btn {
  border: 1px solid var(--border); background: white; color: var(--text);
  border-radius: 18px; padding: 6px 14px; font-size: 13px; cursor: pointer;
}
.ctrl-btn:hover, .ctrl-btn.active { color: white; background: var(--primary); border-color: var(--primary); }
.insight {
  background: linear-gradient(135deg,#f0f6fb,#e9f2f8);
  border-left: 4px solid var(--secondary); padding: 15px 18px;
  margin: 16px 0 0; border-radius: 0 8px 8px 0; font-size: 14px;
}
.insight strong { color: var(--primary); }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th {
  background: var(--primary); color: white; text-align: left;
  padding: 10px 12px; white-space: nowrap;
}
.data-table td { padding: 9px 12px; border-bottom: 1px solid var(--border); white-space: nowrap; }
.data-table tr:nth-child(even) td { background: #f8fbff; }
.data-table tr:hover td { background: #eef6ff; }
.rank-badge {
  display: inline-block; min-width: 24px; height: 24px; border-radius: 50%;
  line-height: 24px; text-align: center; color: white; font-weight: 700; font-size: 12px;
}
.rank-1 { background: #c79a2b; } .rank-2 { background: #8e99a3; }
.rank-3 { background: #9c6a45; } .rank-other { background: var(--secondary); }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 22px; }
.footer {
  color: var(--muted); font-size: 13px; text-align: center;
  padding: 28px; border-top: 1px solid var(--border); background: white;
}
@media (max-width: 900px) {
  .header, .nav, .container { padding-left: 22px; padding-right: 22px; }
  .grid-2 { grid-template-columns: 1fr; }
  .header h1 { font-size: 24px; }
}
</style>
</head>
<body>

<div class="header">
  <div class="header-meta">
    <span>项目编号：T-B3</span>
    <span>小组：G01</span>
    <span>作业编号：ex_Team01</span>
    <span>数据区间：2011-2025</span>
    <span>版本：v2</span>
  </div>
  <h1>中国省级经济面板数据整理与可视化</h1>
  <div class="team-card">
    <div><strong>作业类型：</strong>小组作业</div>
    <div><strong>小组成员：</strong>龙昊文（25210204）、潘福璋（25210218）、沈婷婷（25210230）、张璇（25210303）、许博东（25210269）、张梦洁（25210299）、吴小飞（25210261）、高一婷（25210134）</div>
    <div><strong>课程：</strong>数据分析与经济决策</div>
    <div><strong>仓库地址：</strong><a href="https://github.com/Chr1s-1in/ds2026-G1-China_Provincial_Economy" target="_blank" style="color:#fff">https://github.com/Chr1s-1in/ds2026-G1-China_Provincial_Economy</a></div>
  </div>
  <p>基于国家统计局国家数据平台数据，整理 31 个省级行政区的 GDP、产业结构、消费、收入与人口指标，展示区域经济分布、增长趋势和结构差异。</p>
  <span class="badge">数据来源：国家统计局  https://data.stats.gov.cn</span>
</div>

<nav class="nav">
  <a onclick="scrollToSection('overview')" class="active">总览</a>
  <a onclick="scrollToSection('gdp-map')">GDP分布</a>
  <a onclick="scrollToSection('heatmap')">增速热力图</a>
  <a onclick="scrollToSection('trend')">趋势分析</a>
  <a onclick="scrollToSection('industry')">产业结构</a>
  <a onclick="scrollToSection('comparison')">综合比较</a>
  <a onclick="scrollToSection('table')">数据表格</a>
</nav>

<div class="container">

<!-- ========== KPI ========== -->
<div id="overview" style="margin-bottom:42px">
  <div class="kpi-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(195px,1fr));gap:18px">
    <div class="chart-card" style="padding:22px">
      <div class="kpi-label" style="color:var(--muted);font-size:12px">31省GDP合计</div>
      <div class="kpi-value" style="color:var(--primary);font-size:28px;font-weight:700" id="kpi-total-gdp"></div>
      <div class="kpi-sub" style="color:var(--muted);font-size:12px;margin-top:3px" id="kpi-total-sub">亿元（2025年）</div>
    </div>
    <div class="chart-card" style="padding:22px">
      <div class="kpi-label" style="color:var(--muted);font-size:12px">GDP第一大省</div>
      <div class="kpi-value" style="color:var(--primary);font-size:28px;font-weight:700" id="kpi-top-province"></div>
      <div class="kpi-sub" style="color:var(--muted);font-size:12px;margin-top:3px" id="kpi-top-sub">亿元</div>
    </div>
    <div class="chart-card" style="padding:22px">
      <div class="kpi-label" style="color:var(--muted);font-size:12px">GDP增速最高</div>
      <div class="kpi-value" style="color:var(--primary);font-size:28px;font-weight:700" id="kpi-top-growth"></div>
      <div class="kpi-sub" style="color:var(--muted);font-size:12px;margin-top:3px" id="kpi-growth-sub">省份</div>
    </div>
    <div class="chart-card" style="padding:22px">
      <div class="kpi-label" style="color:var(--muted);font-size:12px">覆盖省份</div>
      <div class="kpi-value" style="color:var(--primary);font-size:28px;font-weight:700">31</div>
      <div class="kpi-sub" style="color:var(--muted);font-size:12px;margin-top:3px">不含港澳台</div>
    </div>
    <div class="chart-card" style="padding:22px">
      <div class="kpi-label" style="color:var(--muted);font-size:12px">收入最高</div>
      <div class="kpi-value" style="color:var(--primary);font-size:28px;font-weight:700" id="kpi-top-income"></div>
      <div class="kpi-sub" style="color:var(--muted);font-size:12px;margin-top:3px" id="kpi-income-sub">元/年</div>
    </div>
  </div>
</div>

<!-- ========== Section 1: GDP Map ========== -->
<div id="gdp-map" class="section">
  <div class="section-header">
    <div class="section-num">1</div>
    <div>
      <div class="section-title">各省 GDP 空间分布</div>
      <div class="section-desc">切换年份观察省级经济总量的空间差异</div>
    </div>
  </div>
  <div class="chart-card">
    <div class="chart-title">省级 GDP 分布（亿元）</div>
    <div class="chart-subtitle">颜色越深表示 GDP 规模越大</div>
    <div class="controls">
      <span class="ctrl-label">选择年份：</span>
      <button class="ctrl-btn" onclick="updateMap(2011)">2011</button>
      <button class="ctrl-btn" onclick="updateMap(2015)">2015</button>
      <button class="ctrl-btn" onclick="updateMap(2020)">2020</button>
      <button class="ctrl-btn active" onclick="updateMap(2024)">2024</button>
    </div>
    <div id="map-chart" class="chart-box" style="height:520px"></div>
    <div class="insight"><strong>经济集聚：</strong>广东、江苏、山东、浙江持续处于第一梯队，东部沿海省份 GDP 总量遥遥领先。</div>
  </div>
</div>

<!-- ========== Section 2: Growth Heatmap ========== -->
<div id="heatmap" class="section">
  <div class="section-header">
    <div class="section-num">2</div>
    <div>
      <div class="section-title">各省 GDP 增速热力图</div>
      <div class="section-desc">按地区分组（蓝=东部 · 紫=东北 · 绿=中部 · 金=西部），颜色越蓝增速越高</div>
    </div>
  </div>
  <div class="chart-card">
    <div class="chart-title">GDP 同比增速（2013-2024，%）</div>
    <div class="chart-subtitle">区域色标：<span style="color:#4f7fa6;font-weight:700">东部</span> · <span style="color:#8e7aa8;font-weight:700">东北</span> · <span style="color:#6f9f8f;font-weight:700">中部</span> · <span style="color:#c78b54;font-weight:700">西部</span> | 蓝色=高增速，米色=中位，砖红=低增速</div>
    <div id="heatmap-chart" class="chart-box" style="height:700px"></div>
    <div class="insight"><strong>区域分化：</strong>西部省份近年增速普遍高于全国平均，东北三省增速持续低于均值，东部省份增速趋于稳定。</div>
  </div>
</div>

<!-- ========== Section 3: Trend ========== -->
<div id="trend" class="section">
  <div class="section-header">
    <div class="section-num">3</div>
    <div>
      <div class="section-title">主要省份 GDP 增长趋势</div>
      <div class="section-desc">追踪 2011-2024 年经济梯队演变</div>
    </div>
  </div>
  <div class="chart-card">
    <div class="chart-title">GDP 趋势折线图（2011-2024）</div>
    <div class="chart-subtitle">单位：亿元</div>
    <div class="controls">
      <span class="ctrl-label">显示组别：</span>
      <button class="ctrl-btn active" onclick="showTrend('top8')">TOP 8</button>
      <button class="ctrl-btn" onclick="showTrend('central')">中部六省</button>
      <button class="ctrl-btn" onclick="showTrend('west')">西部代表</button>
    </div>
    <div id="trend-chart" class="chart-box" style="height:460px"></div>
    <div class="insight"><strong>梯队变化：</strong>广东、江苏稳居前二；四川、湖北等中西部省份位次上升，区域竞争格局动态调整。</div>
  </div>
</div>

<!-- ========== Section 4: Industry ========== -->
<div id="industry" class="section">
  <div class="section-header">
    <div class="section-num">4</div>
    <div>
      <div class="section-title">产业结构分析</div>
      <div class="section-desc">利用 2025 年三次产业数据比较区域与省份结构</div>
    </div>
  </div>
  <div class="grid-2">
    <div class="chart-card">
      <div class="chart-title">四大区域平均产业结构</div>
      <div class="chart-subtitle">区域内各省产业占比的算术平均</div>
      <div id="region-industry-chart" class="chart-box" style="height:360px"></div>
    </div>
    <div class="chart-card">
      <div class="chart-title">省份第三产业结构</div>
      <div class="chart-subtitle">第三产业占比 Top 15</div>
      <div id="province-industry-chart" class="chart-box" style="height:360px"></div>
    </div>
  </div>
  <div class="insight"><strong>服务化差异：</strong>北京、上海第三产业占比超 75%；制造业强省保持较高第二产业占比。</div>
</div>

<!-- ========== Section 5: Comparison ========== -->
<div id="comparison" class="section">
  <div class="section-header">
    <div class="section-num">5</div>
    <div>
      <div class="section-title">经济规模与收入水平综合比较</div>
      <div class="section-desc">横轴=GDP总量，纵轴=居民可支配收入，气泡大小=社消总额</div>
    </div>
  </div>
  <div class="chart-card">
    <div class="chart-title">2025 年各省综合比较气泡图</div>
    <div class="chart-subtitle">颜色代表区域板块</div>
    <div id="bubble-chart" class="chart-box" style="height:500px"></div>
    <div class="insight"><strong>规模与质量：</strong>广东、江苏 GDP 总量领先；北京、上海在居民收入上更为突出。</div>
  </div>
</div>

<!-- ========== Section 6: Table ========== -->
<div id="table" class="section">
  <div class="section-header">
    <div class="section-num">6</div>
    <div>
      <div class="section-title">2025 年省级核心指标表</div>
      <div class="section-desc">点击按钮排序、筛选</div>
    </div>
  </div>
  <div class="chart-card">
    <div class="controls">
      <span class="ctrl-label">排序：</span>
      <button class="ctrl-btn active" onclick="sortTable('gdp')">按GDP</button>
      <button class="ctrl-btn" onclick="sortTable('growth')">按增速</button>
      <button class="ctrl-btn" onclick="sortTable('income')">按收入</button>
      <button class="ctrl-btn" onclick="sortTable('retail')">按社消</button>
      <span class="ctrl-label" style="margin-left:18px">地区：</span>
      <button class="ctrl-btn active" onclick="filterRegion('all')">全部</button>
      <button class="ctrl-btn" onclick="filterRegion('东部')">东部</button>
      <button class="ctrl-btn" onclick="filterRegion('中部')">中部</button>
      <button class="ctrl-btn" onclick="filterRegion('西部')">西部</button>
      <button class="ctrl-btn" onclick="filterRegion('东北')">东北</button>
    </div>
    <div style="overflow-x:auto;margin-top:12px">
      <table class="data-table">
        <thead>
          <tr><th>排名</th><th>省份</th><th>区域</th><th>GDP（亿元）</th><th>GDP增速</th><th>居民收入（元）</th><th>社消总额（亿元）</th><th>常住人口（万人）</th><th>三产占比</th></tr>
        </thead>
        <tbody id="table-body"></tbody>
      </table>
    </div>
  </div>
</div>

</div>

<div class="footer">
  中国省级经济面板数据整理与可视化 · G01 · T-B3 · 数据来源：国家统计局  https://data.stats.gov.cn
</div>

<script>
// ============================================================
// DATA
// ============================================================
const GDP_DATA = ''' + json.dumps(gdp_data, ensure_ascii=False, cls=NpEncoder) + r''';
const TABLE_DATA = ''' + json.dumps(table_data, ensure_ascii=False, cls=NpEncoder) + r''';
const REGION_SUMMARY = ''' + json.dumps(region_data, ensure_ascii=False, cls=NpEncoder) + r''';
const REGION_COLORS = ''' + json.dumps(REGION_COLORS, ensure_ascii=False, cls=NpEncoder) + r''';
const MAP_NAMES = ''' + json.dumps(province_map, ensure_ascii=False, cls=NpEncoder) + r''';
const HEAT_DATA = ''' + json.dumps(heat_data, ensure_ascii=False, cls=NpEncoder) + r''';
const HEAT_LABELS = ''' + json.dumps(heat_labels, ensure_ascii=False, cls=NpEncoder) + r''';
const HEAT_YEARS = ''' + json.dumps(heat_years, ensure_ascii=False, cls=NpEncoder) + r''';
const REGION_BREAKS = ''' + json.dumps(region_breaks, ensure_ascii=False, cls=NpEncoder) + r''';
const HEAT_ZMIN = ''' + str(heat_zmin) + r''';
const HEAT_ZMAX = ''' + str(heat_zmax) + r''';
const HEAT_ZMID = ''' + str(heat_zmid) + r''';

const TREND_YEARS = ''' + json.dumps([int(y) for y in years], ensure_ascii=False, cls=NpEncoder) + r''';
const TREND_TOP8 = ''' + json.dumps(
    sorted(df[df['year'] == 2024].sort_values('gdp', ascending=False).head(8)['province'].tolist()), ensure_ascii=False, cls=NpEncoder) + r''';
const TREND_CENTRAL = ''' + json.dumps(['山西','安徽','江西','河南','湖北','湖南'], ensure_ascii=False, cls=NpEncoder) + r''';
const TREND_WEST = ''' + json.dumps(['四川','重庆','陕西','云南','广西','贵州'], ensure_ascii=False, cls=NpEncoder) + r''';

// Build trend series
const GDP_SERIES = {};
for (const [y, data] of Object.entries(GDP_DATA)) {
  for (const [prov, val] of Object.entries(data)) {
    if (!GDP_SERIES[prov]) GDP_SERIES[prov] = [];
    GDP_SERIES[prov].push(val);
  }
}
// Reorder: ensure each province has values ordered by TREND_YEARS
for (const prov of Object.keys(GDP_SERIES)) {
  const reordered = TREND_YEARS.map(y => (GDP_DATA[String(y)] || {})[prov] || 0);
  GDP_SERIES[prov] = reordered;
}

// KPI
const totalGDP = Object.values(GDP_DATA['2024']).reduce((a,b)=>a+b, 0);
document.getElementById('kpi-total-gdp').textContent = (totalGDP / 10000).toFixed(1) + ' 万亿';
document.getElementById('kpi-total-sub').textContent = '≈ GDP总量的绝大部分';
const topProv = Object.entries(GDP_DATA['2024']).sort((a,b)=>b[1]-a[1])[0];
document.getElementById('kpi-top-province').textContent = topProv[0];
document.getElementById('kpi-top-sub').textContent = topProv[1].toLocaleString() + ' 亿元';
const growthSorted = [...TABLE_DATA].filter(d=>d.growth!=null).sort((a,b)=>b.growth-a.growth);
document.getElementById('kpi-top-growth').textContent = growthSorted[0]?.growth + '%';
document.getElementById('kpi-growth-sub').textContent = growthSorted[0]?.province;
const incomeSorted = [...TABLE_DATA].filter(d=>d.income!=null).sort((a,b)=>b.income-a.income);
document.getElementById('kpi-top-income').textContent = incomeSorted[0]?.income?.toLocaleString();
document.getElementById('kpi-income-sub').textContent = incomeSorted[0]?.province;

// ============================================================
// Map (ECharts)
// ============================================================
let mapLoaded = false;
async function loadChinaMap() {
  try {
    const res = await fetch('https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json');
    echarts.registerMap('china', await res.json());
    mapLoaded = true;
  } catch(e) { mapLoaded = false; }
}

let mapChart = null;
function initMap() {
  mapChart = echarts.init(document.getElementById('map-chart'));
  updateMap(2024);
}
function updateMap(year) {
  document.querySelectorAll('#gdp-map .ctrl-btn').forEach(b => {
    b.classList.toggle('active', parseInt(b.textContent) === year);
  });
  const data = Object.entries(GDP_DATA[String(year)]).map(([name, value]) => ({
    name: MAP_NAMES[name] || name, value, shortName: name
  })).sort((a,b) => b.value - a.value);
  const maxVal = Math.max(...data.map(d => d.value));
  if (mapLoaded) {
    mapChart.setOption({
      tooltip: { trigger: 'item', formatter: p => p.name
        ? `<b>${p.data?.shortName || p.name}</b><br>GDP：${p.value?.toLocaleString()} 亿元`
        : '' },
      visualMap: { min: 0, max: maxVal, left: 10, bottom: 24,
        text: ['高','低'],
        inRange: { color: ['#dfeaf3','#9fbcd1','#5f8fb6','#27496d'] },
        textStyle: { color: '#6b7785' } },
      series: [{
        type: 'map', map: 'china', roam: true,
        label: { show: false },
        emphasis: { itemStyle: { areaColor: '#c78b54' } },
        data
      }]
    }, true);
  }
}

// ============================================================
// Heatmap (ECharts)
// ============================================================
let heatChart = null;
function initHeatmap() {
  heatChart = echarts.init(document.getElementById('heatmap-chart'));
  // Region color bars (yAxis index 0)
  const regionColors = HEAT_LABELS.map(p => {
    for (const [r, c] of Object.entries(REGION_COLORS)) {
      if (TABLE_DATA.find(d => d.province === p)?.region === r) return c;
    }
    return '#ccc';
  });
  heatChart.setOption({
    tooltip: { position: 'top',
      formatter: p => `<b>${p.data[1]}</b><br>年份：${HEAT_YEARS[p.data[0]]}<br>增速：${p.data[2]}%`
    },
    grid: { left: 70, right: 80, top: 10, bottom: 40 },
    xAxis: { type: 'category', data: HEAT_YEARS, splitArea: { show: true },
      axisLabel: { rotate: 0 } },
    yAxis: { type: 'category', data: HEAT_LABELS, splitArea: { show: true },
      axisLabel: {
        fontSize: 11, fontWeight: 'bold',
        color: function(v) {
          for (const [r, c] of Object.entries(REGION_COLORS)) {
            if (TABLE_DATA.find(d => d.province === v)?.region === r) return c;
          }
          return '#333';
        }
      }
    },
    visualMap: { min: HEAT_ZMIN, max: HEAT_ZMAX, calculable: true,
      orient: 'vertical', right: 5, top: 'center', bottom: 40,
      inRange: { color: ['#c97c6a','#e8c5b8','#f5f0eb','#9fbcd1','#4f7fa6'] },
      textStyle: { color: '#6b7785' }
    },
    series: [{
      type: 'heatmap',
      data: HEAT_DATA,
      label: { show: true, fontSize: 9, color: '#2c3e50' },
      emphasis: { itemStyle: { shadowBlur: 8 } }
    }]
  }, true);
  // Add region separator lines using markLine
  for (const brk of REGION_BREAKS.slice(0, -1)) {
    heatChart.setOption({
      series: [{
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { color: '#999', width: 1.5, type: 'solid' },
          data: [{ yAxis: HEAT_LABELS[brk - 0.5] }],
        }
      }]
    }, true);
  }
}

// ============================================================
// Trend Line
// ============================================================
let trendChart = null;
const TREND_SERIES = {};
function buildTrendSeries() {
  for (const prov of Object.keys(GDP_SERIES)) {
    TREND_SERIES[prov] = GDP_SERIES[prov];
  }
}
function initTrend() {
  trendChart = echarts.init(document.getElementById('trend-chart'));
  showTrend('top8');
}
function showTrend(group) {
  document.querySelectorAll('#trend .ctrl-btn').forEach(b => {
    b.classList.toggle('active', b.textContent.includes(
      group === 'top8' ? 'TOP' : group === 'central' ? '中部' : '西部'));
  });
  const provs = group === 'top8' ? TREND_TOP8 : group === 'central' ? TREND_CENTRAL : TREND_WEST;
  const colors = ['#27496d','#4f7fa6','#6f9f8f','#c78b54','#8e7aa8','#5b9279','#a87157','#7e9eb8'];
  const series = provs.map((p, i) => ({
    name: p, type: 'line', smooth: true, symbolSize: 5,
    lineStyle: { width: 2 },
    itemStyle: { color: colors[i % colors.length] },
    data: TREND_SERIES[p] || []
  }));
  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { top: 0, type: 'scroll' },
    grid: { left: 78, right: 35, top: 55, bottom: 55 },
    xAxis: { type: 'category', data: TREND_YEARS },
    yAxis: { type: 'value', name: '亿元', axisLabel: { formatter: v => (v / 10000).toFixed(0) + '万' } },
    series
  }, true);
}

// ============================================================
// Industry Charts
// ============================================================
function initIndustry() {
  const rChart = echarts.init(document.getElementById('region-industry-chart'));
  const pChart = echarts.init(document.getElementById('province-industry-chart'));
  rChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0 },
    grid: { left: 65, right: 25, top: 45, bottom: 35 },
    xAxis: { type: 'value', max: 100, axisLabel: { formatter: v => v + '%' } },
    yAxis: { type: 'category', data: REGION_SUMMARY.map(d => d.region) },
    series: [
      { name: '第一产业', type: 'bar', stack: 'total',
        data: REGION_SUMMARY.map(d => d.primary), itemStyle: { color: '#8fb98d' } },
      { name: '第二产业', type: 'bar', stack: 'total',
        data: REGION_SUMMARY.map(d => d.secondary), itemStyle: { color: '#6c9ec1' } },
      { name: '第三产业', type: 'bar', stack: 'total',
        data: REGION_SUMMARY.map(d => d.tertiary), itemStyle: { color: '#27496d' } },
    ]
  });
  const topT = [...TABLE_DATA].sort((a,b) => (b.tertiary_pct||0) - (a.tertiary_pct||0)).slice(0, 15).reverse();
  pChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0 },
    grid: { left: 65, right: 25, top: 45, bottom: 35 },
    xAxis: { type: 'value', max: 100, axisLabel: { formatter: v => v + '%' } },
    yAxis: { type: 'category', data: topT.map(d => d.province) },
    series: [
      { name: '第一产业', type: 'bar', stack: 'total',
        data: topT.map(d => d.primary), itemStyle: { color: '#8fb98d' } },
      { name: '第二产业', type: 'bar', stack: 'total',
        data: topT.map(d => d.secondary), itemStyle: { color: '#6c9ec1' } },
      { name: '第三产业', type: 'bar', stack: 'total',
        data: topT.map(d => d.tertiary), itemStyle: { color: '#27496d' } },
    ]
  });
}

// ============================================================
// Bubble Chart
// ============================================================
function initBubble() {
  const chart = echarts.init(document.getElementById('bubble-chart'));
  const regions = ['东部','中部','西部','东北'];
  const series = regions.map(r => ({
    name: r, type: 'scatter',
    data: TABLE_DATA.filter(d => d.region === r)
      .map(d => ({ name: d.province, value: [d.gdp, d.income, d.retail || 500, d.population || 0] })),
    symbolSize: v => Math.max(14, Math.sqrt(v[2]) * 0.45),
    itemStyle: { color: REGION_COLORS[r], opacity: .78, borderColor: '#fff', borderWidth: 1 },
    label: { show: true, formatter: p => p.name, position: 'top', fontSize: 10, color: '#263445' }
  }));
  chart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: p => `<b>${p.name}</b><br>GDP：${p.value[0]?.toLocaleString()} 亿元<br>收入：${p.value[1]?.toLocaleString()} 元<br>社消：${p.value[2]?.toLocaleString()} 亿元`
    },
    legend: { top: 0 },
    grid: { left: 82, right: 42, top: 48, bottom: 60 },
    xAxis: { type: 'value', name: 'GDP（亿元）', axisLabel: { formatter: v => (v/10000).toFixed(0) + '万' } },
    yAxis: { type: 'value', name: '居民可支配收入（元）' },
    series
  });
}

// ============================================================
// Data Table
// ============================================================
let currentSort = 'gdp';
let currentFilter = 'all';
function renderTable() {
  let data = TABLE_DATA.filter(d => currentFilter === 'all' || d.region === currentFilter);
  data = data.sort((a,b) => (b[currentSort] || -Infinity) - (a[currentSort] || -Infinity));
  document.getElementById('table-body').innerHTML = data.map((d,i) => {
    const cls = i === 0 ? 'rank-1' : i === 1 ? 'rank-2' : i === 2 ? 'rank-3' : 'rank-other';
    return `<tr>
      <td><span class="rank-badge ${cls}">${i+1}</span></td>
      <td><strong>${d.province}</strong></td>
      <td><span style="color:${REGION_COLORS[d.region]};font-weight:700">${d.region}</span></td>
      <td>${d.gdp?.toLocaleString() ?? '—'}</td>
      <td>${d.growth != null ? d.growth + '%' : '—'}</td>
      <td>${d.income?.toLocaleString() ?? '—'}</td>
      <td>${d.retail?.toLocaleString() ?? '—'}</td>
      <td>${d.population?.toLocaleString() ?? '—'}</td>
      <td>${d.tertiary_pct ? d.tertiary_pct + '%' : '—'}</td>
    </tr>`;
  }).join('');
}
function sortTable(field) {
  currentSort = field;
  document.querySelectorAll('#table .ctrl-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('#table .ctrl-btn').forEach(b => {
    const fn = b.getAttribute('onclick') || '';
    if (fn.includes('sortTable') && fn.includes(`'${field}'`)) b.classList.add('active');
    if (fn.includes('filterRegion') && fn.includes(`'${currentFilter}'`)) b.classList.add('active');
  });
  renderTable();
}
function filterRegion(region) {
  currentFilter = region;
  document.querySelectorAll('#table .ctrl-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('#table .ctrl-btn').forEach(b => {
    const fn = b.getAttribute('onclick') || '';
    if (fn.includes('filterRegion') && fn.includes(`'${region}'`)) b.classList.add('active');
    if (fn.includes('sortTable') && fn.includes(`'${currentSort}'`)) b.classList.add('active');
  });
  renderTable();
}

// ============================================================
// Nav
// ============================================================
function scrollToSection(id) {
  const el = document.getElementById(id);
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ============================================================
// Init
// ============================================================
async function init() {
  buildTrendSeries();
  await loadChinaMap();
  initMap();
  initHeatmap();
  initTrend();
  initIndustry();
  initBubble();
  renderTable();
  const charts = document.querySelectorAll('[id$="-chart"]');
  const chartInstances = [];
  charts.forEach(id => {
    const inst = echarts.getInstanceByDom(id);
    if (inst) chartInstances.push(inst);
  });
  window.addEventListener('resize', () => {
    chartInstances.forEach(c => c?.resize());
  });
  // Nav highlight on scroll
  const navLinks = document.querySelectorAll('.nav a');
  window.addEventListener('scroll', () => {
    let current = '';
    document.querySelectorAll('.section,[id="overview"]').forEach(s => {
      if (window.scrollY >= s.offsetTop - 125) current = s.id;
    });
    navLinks.forEach(a => a.classList.toggle('active', a.getAttribute('onclick')?.includes(`'${current}'`)));
  });
}
init();
</script>
</body>
</html>'''

# ============================================================
# 输出
# ============================================================
out_path = OUTPUT / 'china_provincial_economy_dashboard.html'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'生成完成: {out_path.name} ({len(html)/1024:.1f} KB)')
