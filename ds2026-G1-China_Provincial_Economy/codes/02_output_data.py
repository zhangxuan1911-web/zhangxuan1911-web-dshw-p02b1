import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path(__file__).resolve().parents[1]
DATA_CLEAN = BASE / 'data_clean'
OUTPUT = BASE / 'output'
OUTPUT.mkdir(exist_ok=True)

df = pd.read_csv(DATA_CLEAN / 'gdp_panel_long_2011_2024.csv', encoding='utf-8-sig')

YEARS = sorted(df['year'].unique())

FULL_NAMES = {
    '北京':'北京市','天津':'天津市','河北':'河北省','山西':'山西省','内蒙古':'内蒙古自治区',
    '辽宁':'辽宁省','吉林':'吉林省','黑龙江':'黑龙江省','上海':'上海市','江苏':'江苏省',
    '浙江':'浙江省','安徽':'安徽省','福建':'福建省','江西':'江西省','山东':'山东省',
    '河南':'河南省','湖北':'湖北省','湖南':'湖南省','广东':'广东省','广西':'广西壮族自治区',
    '海南':'海南省','重庆':'重庆市','四川':'四川省','贵州':'贵州省','云南':'云南省',
    '西藏':'西藏自治区','陕西':'陕西省','甘肃':'甘肃省','青海':'青海省','宁夏':'宁夏回族自治区',
    '新疆':'新疆维吾尔自治区',
}

# ============================================================
# 数据计算
# ============================================================
# GDP 数据：全部年份
all_gdp = {}
for y in YEARS:
    sub = df[df['year'] == y][['province','gdp']].set_index('province')['gdp'].to_dict()
    all_gdp[int(y)] = {k: round(v, 1) for k, v in sub.items()}

# 增速数据：全部年份
all_growth = {}
for y in YEARS:
    sub = df[df['year'] == y][['province','gdp_growth']].set_index('province')['gdp_growth'].to_dict()
    cleaned = {}
    for k, v in sub.items():
        if pd.notna(v):
            cleaned[k] = round(v, 1)
    all_growth[int(y)] = cleaned

# 东中西趋势数据
east_list = ['北京','天津','河北','上海','江苏','浙江','福建','山东','广东','海南','辽宁']
central_list = ['山西','吉林','黑龙江','安徽','江西','河南','湖北','湖南']
west_list = ['内蒙古','广西','重庆','四川','贵州','云南','西藏','陕西','甘肃','青海','宁夏','新疆']

def region_of(p):
    if p in east_list: return '东部'
    if p in central_list: return '中部'
    if p in west_list: return '西部'
    return '其他'

df_r = df.copy()
df_r['region'] = df_r['province'].apply(region_of)
trend = df_r.groupby(['region','year'])['gdp_growth'].mean().reset_index()
trend_data = {'years': [int(y) for y in YEARS], '东部': [], '中部': [], '西部': []}
for _, row in trend.iterrows():
    if row['region'] in trend_data:
        v = round(row['gdp_growth'], 1) if pd.notna(row['gdp_growth']) else None
        trend_data[row['region']].append(v)

# ============================================================
# 人均 GDP 数据
# ============================================================
df_ind = pd.read_csv(DATA_CLEAN / 'provincial_indicators_2025_clean.csv', encoding='utf-8-sig')
pop_dict = dict(zip(df_ind['province'], df_ind['常住人口(万人)']))
region_dict = dict(zip(df_ind['province'], df_ind['region']))

all_per_capita = {}
for y in YEARS:
    sub = df[df['year'] == y][['province','gdp']].set_index('province')['gdp']
    per_cap = {}
    for prov, gdp_val in sub.items():
        pop = pop_dict.get(prov)
        if pop and pop > 0:
            per_cap[prov] = round(gdp_val / pop, 2)
    all_per_capita[int(y)] = per_cap

# ============================================================
# JSON 序列化
# ============================================================
payload = {
    'allGdp': {str(k): v for k, v in all_gdp.items()},
    'allGrowth': {str(k): v for k, v in all_growth.items()},
    'allPerCapita': {str(k): v for k, v in all_per_capita.items()},
    'allPop': pop_dict,
    'allRegion': region_dict,
    'fullNames': FULL_NAMES,
    'years': [int(y) for y in YEARS],
    'trend': trend_data,
}
json_str = json.dumps(payload, ensure_ascii=False, default=str)

# ============================================================
# 生成 HTML
# ============================================================
SCATTER_JS = r'''
// ===== 第5节: 散点图 (GDP总量 vs 人均GDP) =====
var scatterChart;
var scatterYear = 2024;

function computeMedian(arr) {
  var sorted = arr.slice().sort(function(a,b) { return a - b; });
  var mid = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 0) {
    return (sorted[mid-1] + sorted[mid]) / 2;
  }
  return sorted[mid];
}

function getScatterData(year) {
  var east = [], central = [], west = [], northeast = [];
  var all = [];
  Object.keys(D.allPop).forEach(function(p) {
    var gdp = D.allGdp[String(year)] && D.allGdp[String(year)][p];
    var pcap = D.allPerCapita[String(year)] && D.allPerCapita[String(year)][p];
    var pop = D.allPop[p];
    var region = D.allRegion[p];
    if (gdp == null || pcap == null) return;
    var item = { name: p, value: [gdp, pcap, pop] };
    all.push(item);
    if (region === '东部') east.push(item);
    else if (region === '中部') central.push(item);
    else if (region === '西部') west.push(item);
    else if (region === '东北') northeast.push(item);
  });
  return { east:east, central:central, west:west, northeast:northeast, all:all };
}

function getBigNotRich(year) {
  var d = getScatterData(year);
  var all = d.all;
  if (!all.length) return [];
  var gdps = all.map(function(x) { return x.value[0]; });
  var pcaps = all.map(function(x) { return x.value[1]; });
  var mg = computeMedian(gdps);
  var mp = computeMedian(pcaps);
  return all.filter(function(x) { return x.value[0] > mg && x.value[1] < mp; })
    .sort(function(a,b) { return b.value[0] - a.value[0]; });
}

function renderScatter(year) {
  var d = getScatterData(year);
  var all = d.all;
  if (!all.length) return;

  var gdps = all.map(function(x) { return x.value[0]; });
  var pcaps = all.map(function(x) { return x.value[1]; });
  var medGdp = computeMedian(gdps);
  var medPcap = computeMedian(pcaps);
  var maxGdp = Math.max.apply(null, gdps);
  var maxPcap = Math.max.apply(null, pcaps);

  var bnrSet = {};
  getBigNotRich(year).forEach(function(x) { bnrSet[x.name] = true; });

  var regionColors = { '东部':'#27496d', '中部':'#6f9f8f', '西部':'#c78b54', '东北':'#8e44ad' };
  var regionKeys = { '东部':'east', '中部':'central', '西部':'west', '东北':'northeast' };
  var isMobile = window.innerWidth < 900;

  var seriesList = [];
  var idx = 0;
  ['东部','中部','西部','东北'].forEach(function(region) {
    var points = d[regionKeys[region]];
    var s = {
      name: region,
      type: 'scatter',
      data: points,
      symbolSize: function(val) { return Math.max(5, Math.sqrt(val[2]) * 0.9); },
      itemStyle: { color: regionColors[region] },
      label: { show: true,
        formatter: function(params) {
          if (bnrSet[params.data.name]) return '{bnr|' + params.data.name + '}';
          return '{all|' + params.data.name + '}';
        },
        rich: { bnr: { color:'#c0392b', fontWeight:'bold', fontSize: isMobile ? 9 : 11 },
                all: { color:'#666', fontSize: isMobile ? 8 : 10 } },
        position: 'right'
      },
      labelLayout: { hideOverlap: true },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.3)' } }
    };
    if (idx === 0) {
      s.markArea = { silent: true,
        data: [[{ xAxis: medGdp, yAxis: 0, itemStyle: { color: 'rgba(192,57,43,0.06)' } },
                { xAxis: maxGdp * 1.1, yAxis: medPcap }]]
      };
      s.markLine = { silent: true, symbol: 'none',
        data: [
          { xAxis: medGdp, lineStyle: { type:'dashed', color:'#999', width:1 }, label: { formatter:'GDP中位数', fontSize:10, color:'#999' } },
          { yAxis: medPcap, lineStyle: { type:'dashed', color:'#999', width:1 }, label: { formatter:'人均中位数', fontSize:10, color:'#999' } }
        ]
      };
    }
    seriesList.push(s);
    idx++;
  });

  scatterChart.setOption({
    tooltip: { formatter: function(params) {
      var d = params.data;
      if (!d) return '';
      return '<b>' + d.name + '</b><br>GDP：' + fmt(d.value[0]) + ' 亿元<br>人均GDP：' + d.value[1].toFixed(2) + ' 万元<br>人口：' + fmt(d.value[2]) + ' 万人';
    }},
    legend: { data: ['东部','中部','西部','东北'], bottom: 5, left: 'center', textStyle: { fontSize: isMobile ? 10 : 12 } },
    grid: { left: isMobile ? 50 : 70, right: isMobile ? 30 : 50, top: 30, bottom: isMobile ? 65 : 80 },
    xAxis: { type: 'value', name: 'GDP总量（亿元）', nameLocation: 'center', nameGap: 30,
      nameTextStyle: { fontSize: isMobile ? 10 : 12 },
      axisLabel: { fontSize: isMobile ? 9 : 11, formatter: function(v) { return v >= 10000 ? (v/10000).toFixed(1)+'万' : fmt(v); } },
      splitLine: { show: true, lineStyle: { type:'dashed', color:'#eee' } },
      min: 0, max: maxGdp * 1.1
    },
    yAxis: { type: 'value', name: '人均GDP（万元/人）', nameLocation: 'center', nameGap: 40,
      nameTextStyle: { fontSize: isMobile ? 10 : 12 },
      axisLabel: { fontSize: isMobile ? 9 : 11 },
      splitLine: { show: true, lineStyle: { type:'dashed', color:'#eee' } },
      min: 0, max: maxPcap * 1.1
    },
    series: seriesList
  });

  // 更新表格
  var bnr = getBigNotRich(year);
  var tbody = document.getElementById('bnrTbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  if (bnr.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--muted);padding:20px">该年无明显「大而不富」省份</td></tr>';
  } else {
    bnr.forEach(function(item) {
      var rank = 0;
      for (var i = 0; i < all.length; i++) {
        if (all[i].name === item.name) { rank = i + 1; break; }
      }
      var row = '<tr><td><b>' + item.name + '</b></td><td>' + fmt(item.value[0]) + '</td><td>' + item.value[1].toFixed(2) + '</td><td>' + fmt(item.value[2]) + '</td><td>' + D.allRegion[item.name] + '</td><td>' + rank + '</td></tr>';
      tbody.innerHTML += row;
    });
  }

  // 更新 insight
  var bnrNames = bnr.map(function(x) { return x.name; }).join('、');
  document.getElementById('scatterInsight').innerHTML = bnr.length > 0
    ? '<strong>大而不富（GDP高于中位数、人均低于中位数）：</strong>' + bnrNames + ' —— 这些省份经济总量大但人均产出偏低，面临转型压力。'
    : '该年无明显「大而不富」省份。';
}

function initScatter() {
  if (window.innerWidth < 900) {
    document.getElementById('scatterChart').style.height = '380px';
  }
  scatterChart = echarts.init(document.getElementById('scatterChart'));
  renderScatter(2024);
}

function updateScatterYear(y) {
  scatterYear = y;
  document.getElementById('scatterSlider').value = y;
  document.getElementById('scatterYearDisplay').textContent = y;
  renderScatter(y);
}
'''

HTML = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>中国省级经济面板数据可视化</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
<style>
:root {{
  --primary:#27496d; --secondary:#4f7fa6; --accent:#6f9f8f; --warm:#c78b54;
  --bg:#f5f7fa; --card:#ffffff; --text:#263445; --muted:#6b7785; --border:#dfe6ee;
}}
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ font-family:'Microsoft YaHei','PingFang SC',Arial,sans-serif; color:var(--text); background:var(--bg); line-height:1.7; }}
.header {{
  background:linear-gradient(135deg,#27496d 0%,#1f3c58 58%,#315d69 100%);
  color:white; padding:32px 50px 28px;
}}
.header-meta {{ display:flex; flex-wrap:wrap; gap:14px; margin-bottom:10px; font-size:13px; opacity:.82; }}
.header h1 {{ margin:0 0 6px; font-size:28px; letter-spacing:.5px; }}
.header p {{ max-width:780px; margin:0; font-size:14px; opacity:.88; }}
.nav {{
  position:sticky; top:0; z-index:20; display:flex;
  padding:0 50px; background:var(--card); border-bottom:1px solid var(--border);
  box-shadow:0 2px 10px rgba(20,39,57,.07);
}}
.nav a {{
  display:block; padding:12px 16px 10px; color:var(--muted); text-decoration:none;
  font-size:14px; border-bottom:3px solid transparent; cursor:pointer;
}}
.nav a:hover,.nav a.active {{ color:var(--primary); border-bottom-color:var(--primary); }}
.container {{ max-width:1300px; margin:0 auto; padding:28px 36px; }}
.section {{ margin-bottom:36px; }}
.section-header {{ display:flex; gap:10px; align-items:center; margin-bottom:14px; }}
.section-num {{
  width:28px;height:28px;border-radius:50%;background:var(--primary);color:white;
  display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;
}}
.section-title {{ color:var(--primary); font-size:18px; font-weight:700; }}
.chart-card {{ background:var(--card); border:1px solid var(--border); border-radius:10px; padding:22px; box-shadow:0 2px 10px rgba(29,48,66,.045); }}
.controls {{ display:flex; gap:6px; flex-wrap:wrap; align-items:center; margin-bottom:10px; }}
.ctrl-btn {{
  border:1px solid var(--border); background:white; color:var(--text); border-radius:14px;
  padding:4px 12px; font-size:12px; cursor:pointer; transition:all .2s;
}}
.ctrl-btn:hover,.ctrl-btn.active {{ color:white; background:var(--primary); border-color:var(--primary); }}
.ctrl-btn.mode-a.active {{ background:#27496d; border-color:#27496d; }}
.ctrl-btn.mode-b.active {{ background:#d96c3a; border-color:#d96c3a; }}
.mode-b {{ color:#d96c3a; border-color:#d96c3a; }}
.mode-b.active {{ background:#d96c3a; color:white; }}
.map-bar-wrap {{ display:flex; gap:12px; height:580px; }}
.map-box {{ flex:7; min-width:0; }}
.bar-box {{ flex:3; min-width:220px; }}
.slider-row {{ display:flex; align-items:center; gap:12px; margin:10px 0 4px; }}
.slider-row input[type="range"] {{ flex:1; max-width:500px; accent-color:var(--primary); }}
.slider-year {{ font-size:18px; font-weight:700; color:var(--primary); min-width:50px; text-align:center; }}
.insight {{
  background:linear-gradient(135deg,#f0f6fb,#e9f2f8); border-left:4px solid var(--secondary);
  padding:12px 16px; margin:14px 0 0; border-radius:0 8px 8px 0; font-size:13px;
}}
.insight strong {{ color:var(--primary); }}
.footer {{ color:var(--muted); font-size:13px; text-align:center; padding:20px; border-top:1px solid var(--border); background:white; }}
@media (max-width:900px) {{
  .header,.nav,.container {{ padding-left:16px; padding-right:16px; }}
  .header {{ padding-top:24px; padding-bottom:20px; }}
  .header h1 {{ font-size:20px; }}
  .header-meta {{ font-size:11px; gap:8px; }}
  .header p {{ font-size:13px; }}
  .nav {{ padding:0 10px; overflow-x:auto; flex-wrap:nowrap; -webkit-overflow-scrolling:touch; gap:0; }}
  .nav a {{ padding:10px 12px 8px; font-size:12px; white-space:nowrap; flex-shrink:0; }}
  .map-bar-wrap {{ flex-direction:column; height:auto; }}
  .map-box {{ height:360px; }}
  .bar-box {{ height:300px; }}
  .slider-row {{ flex-wrap:wrap; gap:8px; }}
  .slider-row input[type="range"] {{ max-width:100%; }}
  #yearBtns {{ gap:2px !important; }}
  #yearBtns .ctrl-btn {{ font-size:11px; padding:3px 8px; }}
  .section-title {{ font-size:16px; }}
  .chart-card {{ padding:14px; }}
}}
@media (max-width:900px) {{
  #sec4 [style*="grid-template-columns"] {{ grid-template-columns:1fr !important; }}
  .stat-grid {{ grid-template-columns:1fr; }}
}}
@media (max-width:900px) {{
  .controls {{ gap:4px; }}
  .ctrl-btn {{ font-size:11px; padding:3px 10px; }}
  .chart-box {{ min-height:0; }}

.insight {{ font-size:12px; padding:10px 12px; }}
  .analysis-table {{ font-size:11px; }}
  .analysis-table th,.analysis-table td {{ padding:5px 6px; }}
}}
.stat-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin-bottom:18px; }}
.stat-card {{ background:var(--card); border:1px solid var(--border); border-radius:8px; padding:16px; box-shadow:0 1px 6px rgba(29,48,66,.04); }}
.stat-num {{ font-size:26px; font-weight:700; color:var(--primary); line-height:1.2; }}
.stat-label {{ font-size:12px; color:var(--muted); margin-top:4px; }}
.stat-sub {{ font-size:12px; color:var(--muted); margin-top:2px; }}
.analysis-table {{ width:100%; border-collapse:collapse; font-size:13px; }}
.analysis-table th {{ background:var(--primary); color:white; text-align:left; padding:8px 10px; white-space:nowrap; }}
.analysis-table td {{ padding:7px 10px; border-bottom:1px solid var(--border); }}
.analysis-table tr:hover td {{ background:#f0f6fb; }}
.tag-sustained {{ display:inline-block; background:#27496d; color:white; border-radius:10px; padding:1px 8px; font-size:11px; }}
.tag-majority {{ display:inline-block; background:#6f9f8f; color:white; border-radius:10px; padding:1px 8px; font-size:11px; }}
.tag-half {{ display:inline-block; background:#c78b54; color:white; border-radius:10px; padding:1px 8px; font-size:11px; }}
@media (max-width:900px) {{
  .stat-grid {{ grid-template-columns:1fr; }}
}}
</style>
</head>
<body>
<div class="header">
  <div class="header-meta">
    <span>作业编号：ex_Team01</span><span>小组：G01</span><span>T-B3 中国省级经济面板数据可视化</span>
    <span>2011-2024</span>
  </div>
  <h1>中国省级经济面板数据整理与可视化</h1>
  <p>基于国家统计局数据，整理 31 个省级行政区 GDP 面板数据</p>
</div>

<nav class="nav" id="nav">
  <a class="active" onclick="scrollToSec('sec1')">GDP 分析</a>
  <a onclick="scrollToSec('sec2')">增速趋势</a>
  <a onclick="scrollToSec('sec3')">增速解读</a>
  <a onclick="scrollToSec('sec4')">异常波动</a>
  <a onclick="scrollToSec('sec5')">总量vs人均</a>
</nav>

<div class="container">

<div id="sec1" class="section">
  <div class="section-header"><div class="section-num">1</div><div><div class="section-title">各省 GDP 分析</div><div class="section-desc">切换模式查看 GDP 总量或增速分布与排名</div></div></div>
  <div class="chart-card">
    <div class="controls" style="justify-content:space-between;flex-wrap:wrap">
      <div style="display:flex;gap:6px;align-items:center">
        <span class="ctrl-label">模式：</span>
        <button class="ctrl-btn mode-a active" onclick="setMode('gdp')">A: GDP 总量</button>
        <button class="ctrl-btn mode-b" onclick="setMode('growth')">B: GDP 增速</button>
      </div>
      <span style="font-size:12px;color:var(--muted)" id="modeLabel">单位：亿元</span>
    </div>

    <div class="map-bar-wrap">
      <div id="mapChart" class="map-box"></div>
      <div id="barChart" class="bar-box"></div>
    </div>

    <div class="slider-row">
      <input type="range" id="yearSlider" min="2011" max="2024" value="2024" step="1"
             oninput="updateYear(parseInt(this.value))">
      <span class="slider-year" id="yearDisplay">2024</span>
    </div>
    <div class="controls" id="yearBtns" style="gap:4px">
      {''.join(f'<button class="ctrl-btn{' active' if y==2024 else ''}" onclick="updateYear({y})">{y}</button>' for y in YEARS)}
    </div>

    <div id="insightBox" class="insight"><strong>经济集聚：</strong>东部沿海省份 GDP 长期领先，广东、江苏、山东、浙江稳居第一梯队。</div>
  </div>
</div>

<div id="sec2" class="section">
  <div class="section-header"><div class="section-num">2</div><div><div class="section-title">东中西 GDP 增速对比</div><div class="section-desc">2011-2024 年三大区域平均增速趋势</div></div></div>
    <div class="chart-card">
    <div id="trendChart" class="chart-box" style="height:400px"></div>
    <div class="gap-bar" style="display:flex;justify-content:space-between;padding:4px 6% 0 6%;font-size:13px;font-weight:bold">
      <span style="color:#c78b54"></span>
      <span style="color:#27496d"></span>
    </div>
    <div class="insight"><strong>差距收敛：</strong>西部增速持续高于东部，但领先幅度从 2012 年的 3.9 个百分点收窄至 2024 年的 0.5 个百分点，区域经济差距呈显著缩小趋势。中部增速自 2017 年后超过东部，追赶效应显现。</div>
  </div>
</div>

<div id="sec3" class="section">
  <div class="section-header"><div class="section-num">3</div><div><div class="section-title">重点年份GDP增速深度解读</div><div class="section-desc">近10年各省增速对比、驱动因素与区域经济格局</div></div></div>

  <div class="stat-grid">
    <div class="stat-card">
      <div class="stat-num">7~8</div>
      <div class="stat-label">高于全国均值的年数（持续领先组）</div>
      <div class="stat-sub">10 个省份在 7+/10 年中增速超全国平均</div>
    </div>
    <div class="stat-card">
      <div class="stat-num">7 : 3</div>
      <div class="stat-label">中西部 vs 东部领先省份数</div>
      <div class="stat-sub">持续领先的省份中，中西部占 7 席</div>
    </div>
    <div class="stat-card">
      <div class="stat-num">3.9% → 0.5%</div>
      <div class="stat-label">东西部增速差距变化（2012 → 2024）</div>
      <div class="stat-sub">区域经济差距呈显著缩小趋势</div>
    </div>
  </div>

  <div class="chart-card">
    <div class="chart-title">各省近10年（2015-2024）增速表现分级</div>
    <div class="chart-subtitle">按高于全国均值的年数分级</div>
    <div style="overflow-x:auto">
    <table class="analysis-table">
      <thead><tr><th>级别</th><th>省份</th><th>高于均值年数</th><th>10年平均增速</th><th>地区</th><th>驱动模式</th></tr></thead>
      <tbody>
        <tr><td><span class="tag-sustained">持续领先</span></td><td>西藏、贵州、四川、重庆</td><td>7-8/10年</td><td>9.4%~11.4%</td><td>西部</td><td>基建投资+产业承接+能源禀赋</td></tr>
        <tr><td><span class="tag-sustained">持续领先</span></td><td>湖北、安徽、江西</td><td>7-8/10年</td><td>7.7%~8.3%</td><td>中部</td><td>长三角产业外溢+交通枢纽</td></tr>
        <tr><td><span class="tag-sustained">持续领先</span></td><td>浙江、福建、海南</td><td>7-8/10年</td><td>8.3%~8.6%</td><td>东部</td><td>数字经济+民营经济+自贸港</td></tr>
        <tr><td><span class="tag-majority">多数领先</span></td><td>云南、广西、新疆、湖南、山东、上海</td><td>6/10年</td><td>6.7%~8.3%</td><td>混合</td><td>周期性波动较大</td></tr>
        <tr><td><span class="tag-half">半数以上</span></td><td>广东、江苏、北京等 15 省</td><td>1-5/10年</td><td>3.0%~8.3%</td><td>混合</td><td>基数效应/结构转型/东北困境</td></tr>
      </tbody>
    </table>
    </div>

    <div class="insight" style="margin-top:14px">
      <strong>核心发现：</strong>持续高增长省份呈现三类驱动模式 ——
      ① <strong>后发追赶型</strong>（西部）：基建投资+产业转移承接，与「西部大开发」政策预期一致；
      ② <strong>产业承接型</strong>（中部）：承接长三角产业外溢，制造业崛起，印证「中部崛起」战略成效；
      ③ <strong>结构升级型</strong>（东部浙江、福建）：数字经济与民营经济驱动。
    </div>

    <div class="insight" style="margin-top:8px;border-left-color:#c78b54;background:linear-gradient(135deg,#fdf6ee,#faf0e5)">
      <strong>东部&东北全面落后的结构性原因：</strong><br>
      <strong>东部</strong>并非真正「落后」，而是基数效应（广东 14 万亿 vs 西藏 2800 亿，同等增速需要的新增量相差 50 倍）+ 率先面临房地产下行、制造业外迁、消费降级等多重调整压力。<br>
      <strong>东北三省</strong>（辽宁、吉林、黑龙江，平均增速仅 3%~5%）则面临产业结构锁定（重工业为主）、人口持续外流、民营经济薄弱、创新投入不足等深层结构性矛盾，「振兴东北」政策效果远不如「西部大开发」和「中部崛起」。
    </div>
  </div>
</div>

<div id="sec4" class="section">
  <div class="section-header"><div class="section-num">4</div><div><div class="section-title">异常负增长年份深度解析</div><div class="section-desc">三个年份、三种冲击——疫情·产业周期·能源转型</div></div></div>

  <div class="chart-card">
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;margin-bottom:18px">
      <div class="stat-card" style="border-left:3px solid #c0392b;padding:18px">
        <div class="stat-label" style="font-size:14px;font-weight:bold;color:#c0392b;margin-bottom:10px">2020 湖北 → 2024</div>
        <div style="display:flex;align-items:baseline;gap:6px;margin-bottom:10px">
          <span style="font-size:30px;font-weight:700;color:#c0392b">-5.6%</span>
          <span style="font-size:16px;color:var(--muted);margin:0 4px">→</span>
          <span style="font-size:30px;font-weight:700;color:var(--primary)">+5.0%</span>
        </div>
        <div style="font-size:13px;line-height:1.7">
          COVID-19 是一场<strong>短暂冲击</strong>。武汉封城 76 天导致 2020 年经济负增长，但 2021 年不仅恢复，更<strong>超越了 2019 年 GDP 绝对水平</strong>（45,557 亿→50,093 亿，多出 4,536 亿）。这是教科书级的 V 型复苏，2024 年稳定在 5.0%，冲击已完全消化。
        </div>
      </div>

      <div class="stat-card" style="border-left:3px solid #8e44ad;padding:18px">
        <div class="stat-label" style="font-size:14px;font-weight:bold;color:#8e44ad;margin-bottom:10px">2022 吉林 → 2024</div>
        <div style="display:flex;align-items:baseline;gap:6px;margin-bottom:10px">
          <span style="font-size:30px;font-weight:700;color:#8e44ad">-2.3%</span>
          <span style="font-size:16px;color:var(--muted);margin:0 4px">→</span>
          <span style="font-size:30px;font-weight:700;color:var(--primary)">+2.6%</span>
        </div>
        <div style="font-size:13px;line-height:1.7">
          2022 年负增长源于<strong>长春封城导致一汽停产</strong>，属短期冲击。但更深层的结构问题是<strong>一汽以燃油车为主</strong>（红旗、大众/丰田合资），中国新能源渗透率从 2020 年的 5% 飙升至 2024 年的 40%，燃油车市场持续萎缩。<strong>更严重的是产业结构问题</strong>。
        </div>
      </div>

      <div class="stat-card" style="border-left:3px solid #e67e22;padding:18px">
        <div class="stat-label" style="font-size:14px;font-weight:bold;color:#e67e22;margin-bottom:10px">2021 峰值 vs 2024 山西</div>
        <div style="display:flex;align-items:baseline;gap:6px;margin-bottom:10px">
          <span style="font-size:30px;font-weight:700;color:#e67e22">+26.8%</span>
          <span style="font-size:16px;color:var(--muted);margin:0 4px">→</span>
          <span style="font-size:30px;font-weight:700;color:var(--primary)">-2.7%</span>
        </div>
        <div style="font-size:13px;line-height:1.7">
          山西 GDP 是煤价的影子。2021 年<strong>全球经济刺激 + 俄乌战争推波助澜</strong>推高煤价至 2,600 元/吨，GDP 暴涨；2024 年新能源替代 + 房地产收缩致煤价回落到 800 元/吨，GDP 随之下行。山西的 GDP 增长与全球煤价变动密不可分。
        </div>
      </div>
    </div>

    <div class="insight" style="border-left-color:#c0392b;background:linear-gradient(135deg,#fdf0ef,#f8e8e5)">
      <strong>三种冲击，三种性质：</strong>湖北的负增长是<strong>外部疫情冲击</strong>（短期，V 型复苏完成）；吉林的负增长夹杂<strong>外伤与内伤</strong>（COVID 已过，燃油车结构困境才是长期挑战）；山西的负增长是<strong>资源型经济周期</strong>（能源价格大起大落下的固有属性）。
    </div>
  </div>
</div>

<div id="sec5" class="section">
  <div class="section-header">
    <div class="section-num">5</div>
    <div>
      <div class="section-title">GDP总量 vs 人均GDP：谁大而不富？</div>
      <div class="section-desc">散点图直观识别「大而不富」省份——GDP总量高但人均水平偏低</div>
    </div>
  </div>
  <div class="chart-card">
    <div class="controls" style="justify-content:space-between;flex-wrap:wrap">
      <span style="font-size:13px;color:var(--muted)">每个气泡代表一个省份，大小表示人口规模；<span style="color:#c0392b;font-weight:bold">红色区域</span> = 「大而不富」象限</span>
      <div style="display:flex;gap:6px;align-items:center">
        <span style="font-size:12px;color:var(--muted)">年份：</span>
        <input type="range" id="scatterSlider" min="2011" max="2024" value="2024" step="1"
               oninput="updateScatterYear(parseInt(this.value))" style="width:120px;accent-color:var(--primary)">
        <span class="slider-year" id="scatterYearDisplay" style="font-size:16px;min-width:40px">2024</span>
      </div>
    </div>
    <div id="scatterChart" style="height:500px"></div>
    <div id="scatterInsight" class="insight" style="margin-top:10px">
      <strong>大而不富典型：</strong>河南、四川、河北、湖南——GDP总量位居全国前十，但人均GDP低于全国中位数。
    </div>
  </div>
  <div class="chart-card" style="margin-top:14px;overflow-x:auto">
    <table class="analysis-table" id="bnrTable">
      <thead>
        <tr><th>省份</th><th>GDP总量（亿元）</th><th>人均GDP（万元）</th><th>人口（万人）</th><th>地区</th><th>GDP排名</th></tr>
      </thead>
      <tbody id="bnrTbody">
      </tbody>
    </table>
  </div>
</div>

</div>

<div class="footer">中国省级经济面板数据整理与可视化 · G01 · T-B3 · ex_Team01</div>

<script>
const D = {json_str};
const YEARS = D.years;
let currentYear = 2024;
let currentMode = 'gdp';
let mapChart, barChart, trendChart;
let mapLoaded = false;

// ----- 工具 -----
function fmt(v, d=0) {{
  if (v == null || isNaN(v)) return '—';
  return Number(v).toLocaleString('zh-CN', {{maximumFractionDigits:d,minimumFractionDigits:d}});
}}

function scrollToSec(id) {{
  document.getElementById(id).scrollIntoView({{behavior:'smooth'}});
  document.querySelectorAll('.nav a').forEach(a=>a.classList.remove('active'));
  event.target.classList.add('active');
}}

function getProvinceData(year, mode) {{
  const src = mode === 'gdp' ? D.allGdp : D.allGrowth;
  const raw = src[String(year)] || {{}};
  return Object.entries(raw).map(([name,val]) => ({{
    name: (D.fullNames[name] || name), shortName: name, value: val
  }})).sort((a,b) => b.value - a.value);
}}

// ----- 模式 -----
function setMode(mode) {{
  currentMode = mode;
  document.querySelectorAll('#sec1 .mode-a, #sec1 .mode-b').forEach(b => b.classList.toggle('active',
    (b.textContent.includes('A') && mode==='gdp') || (b.textContent.includes('B') && mode==='growth')));
  document.getElementById('modeLabel').textContent = mode==='gdp' ? '单位：亿元' : '单位：%';
  renderAll();
}}

// ----- 年份 -----
function updateYear(y) {{
  currentYear = y;
  document.getElementById('yearSlider').value = y;
  document.getElementById('yearDisplay').textContent = y;
  document.querySelectorAll('#yearBtns .ctrl-btn').forEach(b =>
    b.classList.toggle('active', parseInt(b.textContent)===y));
  renderAll();
}}

// ----- 加载地图 -----
async function loadMap() {{
  try {{
    const r = await fetch('https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json');
    const geo = await r.json();
    echarts.registerMap('china', geo);
    mapLoaded = true;
    initCharts();
  }} catch(e) {{
    document.getElementById('mapChart').innerHTML =
      '<div style="padding:40px;text-align:center;color:var(--muted)">地图加载失败，请检查网络后刷新</div>';
  }}
}}

// ----- 初始化图表 -----
function initCharts() {{
  var w = window.innerWidth;
  if (w < 900) {{
    document.getElementById('mapChart').style.height = '360px';
    document.getElementById('barChart').style.height = '300px';
    document.getElementById('trendChart').style.height = '300px';
  }} else {{
    document.getElementById('trendChart').style.height = '400px';
  }}
  mapChart = echarts.init(document.getElementById('mapChart'));
  barChart = echarts.init(document.getElementById('barChart'));
  trendChart = echarts.init(document.getElementById('trendChart'));
  renderAll();
  initTrend();
  setupHover();
}}

// ----- 渲染地图 + 柱状图 -----
function renderAll() {{
  if (!mapLoaded) return;
  renderMapBar(currentYear, currentMode);
}}

function renderMapBar(year, mode) {{
  const data = getProvinceData(year, mode);
  if (!data.length) return;

  const maxVal = data[0].value;
  const minVal = data[data.length-1].value;

  // 颜色配置
  const isGdp = mode === 'gdp';
  const mapColors = isGdp
    ? ['#dfeaf3','#9fbcd1','#5f8fb6','#27496d']
    : ['#fff5eb','#fdd49a','#fdae61','#d96c3a','#b3301a'];
  const barColor = isGdp ? '#27496d' : '#d96c3a';
  const valueLabel = isGdp ? 'GDP' : '增速';

  // 地图
  mapChart.setOption({{
    tooltip: {{
      trigger: 'item',
      formatter: p => {{
        if (!p.data) return '';
        const sn = p.data.shortName;
        const v = p.data.value;
        const lab = isGdp ? fmt(v) + ' 亿元' : v.toFixed(1) + '%';
        return '<b>' + sn + '</b><br>' + valueLabel + '：' + lab;
      }}
    }},
    visualMap: {{
      min: isGdp ? 0 : Math.floor(minVal),
      max: maxVal * (isGdp ? 1.05 : 1),
      left: 8, bottom: 16,
      text: ['高','低'],
      inRange: {{ color: mapColors }},
      textStyle: {{ color:'#6b7785', fontSize:10 }},
      itemWidth: 12, itemHeight: 80,
      show: true,
    }},
    series: [{{
      type: 'map', map: 'china', roam: false, zoom: 1.4, center: [103.5, 35],
      label: {{ show: true, fontSize: 13, color: '#263445' }},
      emphasis: {{ itemStyle: {{ areaColor: isGdp ? '#c78b54' : '#b3301a' }} }},
      data: data,
      itemStyle: {{ borderColor: '#ffffff', borderWidth: 0.5 }},
    }}]
  }});

  // 柱状图
  const isMobile = window.innerWidth < 900;
  const barYFont = isMobile ? 8 : 11;
  const barXFont = isMobile ? 10 : 14;
  const barValFont = isMobile ? 10 : 15;
  const barData = data.map(d => d.value);
  const barNames = data.map(d => d.shortName);
  barChart.setOption({{
    tooltip: {{
      trigger: 'axis',
      axisPointer: {{ type: 'shadow' }},
      formatter: p => {{
        if (!p.length) return '';
        const d = p[0];
        const lab = isGdp ? fmt(d.value) + ' 亿元' : d.value.toFixed(1) + '%';
        return '<b>' + d.name + '</b><br>' + valueLabel + '：' + lab;
      }}
    }},
    grid: {{ left: 70, right: 90, top: 5, bottom: 30 }},
    xAxis: {{
      type: 'value',
      axisLabel: {{ fontSize: barXFont, formatter: v => isGdp ? (v>=10000 ? (v/10000).toFixed(1)+'万' : fmt(v)) : v.toFixed(0) }},
      splitLine: {{ show: false }},
    }},
    yAxis: {{
      type: 'category', data: barNames, inverse: true,
      axisLabel: {{ fontSize: barYFont, fontWeight: 'bold' }},
      axisTick: {{ show: false }},
      splitLine: {{ show: false }},
    }},
    series: [{{
      type: 'bar', data: barData,
      barWidth: '60%',
      itemStyle: {{ color: barColor, borderRadius: [0,2,2,0] }},
      label: {{
        show: true, position: 'right', fontSize: barValFont,
        formatter: p => isGdp ? fmt(p.value) : p.value.toFixed(1),
      }},
    }}]
  }});

  // 更新 insight
  const top3 = data.slice(0,3).map(d => d.shortName).join('、');
  document.getElementById('insightBox').innerHTML = isGdp
    ? '<strong>经济集聚：</strong>' + currentYear + '年 GDP 前三：' + top3 + '，东部沿海省份长期领先。'
    : '<strong>增长态势：</strong>' + currentYear + '年增速前三：' + top3 + '，中西部追赶效应显著。';
}}

// ----- 悬停联动 -----
function setupHover() {{
  // map hover → bar highlight
  mapChart.on('mouseover', function(params) {{
    if (!params.data) return;
    const name = params.data.shortName;
    barChart.dispatchAction({{
      type: 'highlight', seriesIndex: 0, name: name
    }});
  }});
  mapChart.on('mouseout', function() {{
    barChart.dispatchAction({{ type: 'downplay', seriesIndex: 0 }});
  }});

  // bar hover → map highlight
  barChart.on('mouseover', function(params) {{
    const name = D.fullNames[params.name] || params.name;
    mapChart.dispatchAction({{
      type: 'highlight', seriesIndex: 0, name: name
    }});
  }});
  barChart.on('mouseout', function() {{
    mapChart.dispatchAction({{ type: 'downplay', seriesIndex: 0 }});
  }});
}}

// ----- 趋势折线图 -----
function initTrend() {{
  const td = D.trend;
  // 过滤掉无增速数据的年份（2011）
  const years = [], west = [], east = [], central = [];
  for (let i = 0; i < td.years.length; i++) {{
    if (td['西部'][i] != null && td['东部'][i] != null) {{
      years.push(td.years[i]);
      west.push(td['西部'][i]);
      east.push(td['东部'][i]);
      central.push(td['中部'][i]);
    }}
  }}
  const gapStart = (west[0] - east[0]).toFixed(1);
  const gapEnd = (west[west.length-1] - east[east.length-1]).toFixed(1);

  trendChart.setOption({{
    tooltip: {{
      trigger: 'axis',
      formatter: p => {{
        let s = '<b>' + (p[0].axisValue || p[0].name) + '年</b>';
        p.forEach(i => {{
          if (i.seriesName) s += '<br>' + i.marker + ' ' + i.seriesName + ': ' + (i.value!=null ? i.value.toFixed(1)+'%' : '—');
        }});
        var yr = parseInt(p[0].axisValue || p[0].name, 10);
        if (yr > 0) {{
          var yi = years.indexOf(yr);
          if (yi < 0) yi = years.indexOf(String(yr));
          if (yi >= 0) {{
            var gap = (west[yi] - east[yi]).toFixed(1);
            s += '<br><span style="color:#c78b54;font-weight:bold">西部-东部差距: ' + gap + '%</span>';
          }}
        }}
        return s;
      }}
    }},
    legend: {{ data: ['东部','中部','西部'], bottom: 0, left: 'center', textStyle: {{ fontSize: 12 }} }},
    grid: {{ left: '6%', right: '8%', top: '12%', bottom: '14%' }},
    xAxis: {{ type: 'category', data: years, boundaryGap: false, axisLabel: {{ fontSize: 11 }} }},
    yAxis: {{ type: 'value', name: '增速（%）', nameTextStyle: {{ fontSize: 11 }},
             axisLabel: {{ fontSize: 10 }}, splitLine: {{ lineStyle: {{ type:'dashed', color:'#eee' }} }} }},
    series: [
      {{ name:'东部', type:'line', data:east, smooth:true,
         lineStyle:{{ width:2.5, color:'#27496d' }}, itemStyle:{{ color:'#27496d' }}, symbol:'circle', symbolSize:6 }},
      {{ name:'中部', type:'line', data:central, smooth:true,
         lineStyle:{{ width:2.5, color:'#2e7d32' }}, itemStyle:{{ color:'#2e7d32' }}, symbol:'square', symbolSize:6 }},
      {{ name:'西部', type:'line', data:west, smooth:true,
         lineStyle:{{ width:2.5, color:'#c78b54' }}, itemStyle:{{ color:'#c78b54' }}, symbol:'diamond', symbolSize:6 }},
    ],
  }});
}}
''' + SCATTER_JS + f'''
// ===== 启动 =====
window.addEventListener('load', function() {{
  loadMap().then(function() {{
    initScatter();
  }});
}});
window.addEventListener('resize', function() {{
  if (mapChart) mapChart.resize();
  if (barChart) barChart.resize();
  if (trendChart) trendChart.resize();
  if (scatterChart) scatterChart.resize();
}});
</script>
</body>
</html>
'''

out_path = OUTPUT / 'china_provincial_economy_dashboard.html'
out_path.write_text(HTML, encoding='utf-8')
print(f'  -> output/china_provincial_economy_dashboard.html')
print(f'  Size: {out_path.stat().st_size/1024:.1f} KB')
