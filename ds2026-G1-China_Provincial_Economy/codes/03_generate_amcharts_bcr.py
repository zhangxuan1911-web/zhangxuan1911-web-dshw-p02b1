import pandas as pd
import json
import os

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
df = pd.read_csv(os.path.join(base, 'data_clean', 'gdp_panel_long_2011_2024.csv'))

years = sorted(df['year'].unique())
provinces = sorted(df['province'].unique())

all_data = {}
for year in years:
    year_df = df[df['year'] == year]
    all_data[int(year)] = {}
    for _, row in year_df.iterrows():
        all_data[int(year)][row['province']] = float(row['gdp'])

N_BARS = 15
STEP_DURATION = 1500

data_json = json.dumps(all_data, ensure_ascii=False, indent=2)
provinces_json = json.dumps(provinces, ensure_ascii=False)
years_list = sorted(years)

html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>中国各省GDP排名动态变化 (2011-2024)</title>
<script src="https://cdn.amcharts.com/lib/5/index.js"></script>
<script src="https://cdn.amcharts.com/lib/5/xy.js"></script>
<script src="https://cdn.amcharts.com/lib/5/themes/Animated.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: #F5F0EB; font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", sans-serif; }}
  .header {{ text-align: center; padding: 28px 20px 8px; }}
  .header h1 {{ font-size: 24px; color: #4a5b6b; font-weight: 600; letter-spacing: 1px; }}
  .header p {{ font-size: 13px; color: #8899aa; margin-top: 6px; }}
  #chartdiv {{ width: 100%; height: 680px; }}
  @media (max-width: 768px) {{
    .header h1 {{ font-size: 18px; }}
    #chartdiv {{ height: 500px; }}
  }}
</style>
</head>
<body>

<div class="header">
  <h1>中国各省GDP排名动态变化</h1>
  <p>2011 — 2024 &nbsp;|&nbsp; 单位：亿元 &nbsp;|&nbsp; 显示前 {N_BARS} 名</p>
</div>
<div id="chartdiv"></div>

<script>
var allData = {data_json};

var root = am5.Root.new("chartdiv");

root.numberFormatter.setAll({{
  numberFormat: "#,###.#",
}});

root.fontFamily = '"Microsoft YaHei", "PingFang SC", "Noto Sans SC", sans-serif';

root.setThemes([am5themes_Animated.new(root)]);

var chart = root.container.children.push(am5xy.XYChart.new(root, {{
  panX: true,
  panY: true,
  wheelX: "none",
  wheelY: "none",
  paddingLeft: 0,
  paddingRight: 20,
  layout: root.verticalLayout
}}));

chart.zoomOutButton.set("forceHidden", true);

var yRenderer = am5xy.AxisRendererY.new(root, {{
  minGridDistance: 24,
  inversed: true,
  minorGridEnabled: true
}});
yRenderer.grid.template.set("visible", false);
yRenderer.labels.template.setAll({{
  fontSize: 13,
  fontWeight: "600",
  fill: am5.color(0x4a5b6b)
}});

var yAxis = chart.yAxes.push(am5xy.CategoryAxis.new(root, {{
  maxDeviation: 0,
  categoryField: "province",
  renderer: yRenderer
}}));

var xRenderer = am5xy.AxisRendererX.new(root, {{}});
xRenderer.labels.template.setAll({{
  fontSize: 11,
  fill: am5.color(0x8899aa)
}});

var xAxis = chart.xAxes.push(am5xy.ValueAxis.new(root, {{
  maxDeviation: 0,
  min: 0,
  strictMinMax: true,
  extraMax: 0.15,
  renderer: xRenderer
}}));
xAxis.set("interpolationDuration", {STEP_DURATION} / 10);
xAxis.set("interpolationEasing", am5.ease.linear);

var series = chart.series.push(am5xy.ColumnSeries.new(root, {{
  xAxis: xAxis,
  yAxis: yAxis,
  valueXField: "value",
  categoryYField: "province"
}}));

series.columns.template.setAll({{
  cornerRadiusBR: 4,
  cornerRadiusTR: 4,
  strokeOpacity: 0
}});

series.columns.template.adapters.add("fill", function(fill, target) {{
  return chart.get("colors").getIndex(series.columns.indexOf(target));
}});

series.bullets.push(function() {{
  return am5.Bullet.new(root, {{
    locationX: 1,
    sprite: am5.Label.new(root, {{
      text: "{{valueXWorking.formatNumber('#,###.#')}}",
      fill: am5.color(0x3a4a5a),
      fontSize: 12,
      fontWeight: "500",
      centerX: am5.p100,
      centerY: am5.p50,
      populateText: true
    }})
  }});
}});

var yearLabel = chart.plotContainer.children.push(am5.Label.new(root, {{
  text: "2011",
  fontSize: "7em",
  opacity: 0.12,
  x: am5.p100,
  y: am5.p100,
  centerY: am5.p100,
  centerX: am5.p100,
  fill: am5.color(0x4a5b6b)
}}));

var stepDuration = {STEP_DURATION};
var years = {json.dumps([int(y) for y in years_list])};
var yearIndex = 0;

function getSeriesItem(category) {{
  for (var i = 0; i < series.dataItems.length; i++) {{
    if (series.dataItems[i].get("categoryY") == category) {{
      return series.dataItems[i];
    }}
  }}
}}

function sortCategoryAxis() {{
  series.dataItems.sort(function(x, y) {{
    return y.get("valueX") - x.get("valueX");
  }});

  am5.array.each(yAxis.dataItems, function(dataItem) {{
    var seriesDataItem = getSeriesItem(dataItem.get("category"));
    if (seriesDataItem) {{
      var index = series.dataItems.indexOf(seriesDataItem);
      var deltaPosition = (index - dataItem.get("index", 0)) / series.dataItems.length;
      if (dataItem.get("index") != index) {{
        dataItem.set("index", index);
        dataItem.set("deltaPosition", -deltaPosition);
        dataItem.animate({{
          key: "deltaPosition",
          to: 0,
          duration: stepDuration / 2,
          easing: am5.ease.out(am5.ease.cubic)
        }});
      }}
    }}
  }});

  yAxis.dataItems.sort(function(x, y) {{
    return x.get("index") - y.get("index");
  }});
}}

function updateData() {{
  var year = years[yearIndex];
  if (!allData[year]) return;

  yearLabel.set("text", year.toString());

  var itemsWithNonZero = 0;
  am5.array.each(series.dataItems, function(dataItem) {{
    var category = dataItem.get("categoryY");
    var value = allData[year][category] || 0;
    if (value > 0) itemsWithNonZero++;
    dataItem.animate({{
      key: "valueX",
      to: value,
      duration: stepDuration,
      easing: am5.ease.linear
    }});
    dataItem.animate({{
      key: "valueXWorking",
      to: value,
      duration: stepDuration,
      easing: am5.ease.linear
    }});
  }});

  yAxis.zoom(0, Math.min({N_BARS}, itemsWithNonZero) / yAxis.dataItems.length);

  yearIndex++;
  if (yearIndex >= years.length) {{
    yearIndex = 0;
  }}
}}

function setInitialData() {{
  var year = years[0];
  var d = allData[year];
  for (var n in d) {{
    series.data.push({{ province: n, value: d[n] }});
    yAxis.data.push({{ province: n }});
  }}
}}

setInitialData();

setTimeout(function() {{
  yearIndex = 1;
  updateData();
}}, 100);

var dataInterval = setInterval(updateData, stepDuration);
var sortInterval = setInterval(sortCategoryAxis, 100);

series.appear(1000);
chart.appear(1000, 100);

window.addEventListener("resize", function() {{
  root.resize();
}});
</script>
</body>
</html>'''

out_path = os.path.join(base, 'output', 'amcharts_bcr.html')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(html)
print('Done:', out_path)
