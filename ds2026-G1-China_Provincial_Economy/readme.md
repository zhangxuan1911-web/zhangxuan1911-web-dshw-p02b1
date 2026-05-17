# 中国省级经济面板数据整理与可视化

## 作业信息

- 作业类型：小组作业
- 小组：第一组（G01）
- 选题：中国省级经济面板数据整理与可视化
- 小组成员：
  - 龙昊文（25210204）
  - 潘福璋（25210218）
  - 沈婷婷（25210230）
  - 张璇（25210303）
  - 许博东（25210269）
  - 张梦洁（25210299）
  - 吴小飞（25210261）
  - 高一婷（25210134）
- 作业编号：ex_Team01
- 版本号：v1
- 课程：数据分析与经济决策
- 项目主题：中国省级经济面板数据整理与可视化
- 截止时间：2026-05-16 21:30
- GitHub 仓库：<https://github.com/xubodong/ds2026-G1-China_Provincial_Economy>
- GitHub Pages：<https://xubodong.github.io/ds2026-G1-China_Provincial_Economy/china_provincial_economy_dashboard.html>

## 项目说明

本项目使用桌面文件夹 `中国省级经济面板数据整理` 中的数据，整理中国 31 个省级行政区的经济面板与横截面指标，并生成可视化图表和课程报告。

由于桌面数据包含两类时间口径，本项目采用以下安排：

- 2011-2024 年：使用国家统计局国家数据平台口径整理 GDP 面板数据。
- 2025 年：使用国家统计局国家数据平台口径整理 31 省主要经济社会指标横截面数据。

## 目录结构

```text
.
├── codes
│   ├── 01_data_clean.py
│   └── 02_visualization.py
├── data_raw
├── data_clean
├── docs
├── output
├── prompts
├── .vscode
├── 01_get_data.ipynb
├── 02_data_clean.ipynb
├── 03_analysis_visualization.ipynb
├── environment.yml
├── requirements.txt
├── readme.md
└── Report.md
```

## 数据来源

国家统计局国家数据平台：<https://data.stats.gov.cn>

## Python 环境

本机已安装 Anaconda、VS Code 和课程要求的 VS Code 插件：

- Python
- Jupyter
- Pylance

已注册 Jupyter kernel：

- `Python (Anaconda base - ds2026)`

推荐运行方式：

```powershell
conda run -n base python codes/01_data_clean.py
conda run -n base python codes/02_visualization.py
```

如需新建独立环境，可运行：

```powershell
conda env create -f environment.yml
conda activate ds2026
python -m ipykernel install --user --name ds2026 --display-name "Python (ds2026)"
```

## 复现步骤

1. 检查 `data_raw/` 中是否包含原始数据：
   - `nbs_gdp_long_2011_2025.csv`
   - `nbs_gdp_wide_2011_2025.csv`
   - `provincial_indicators_2025.xlsx`
   - `provincial_indicators_2025.csv`
   - `经济数据_*.md`
2. 运行数据清洗脚本：

   ```powershell
   conda run -n base python codes/01_data_clean.py
   ```

3. 运行可视化脚本：

   ```powershell
   conda run -n base python codes/02_visualization.py
   ```

4. 查看输出：
   - 清洗数据：`data_clean/`
   - 图表：`output/`
   - 报告：`Report.md`

## 主要输出

- `data_clean/gdp_panel_long_2011_2024.csv`
- `data_clean/gdp_panel_wide_2011_2024.csv`
- `data_clean/provincial_indicators_2025_clean.csv`
- `data_clean/gdp_panel.csv`
- `data_clean/latest_year.csv`
- `data_clean/data_dictionary.csv`
- `output/fig_gdp_map.html`
- `output/fig_gdp_heatmap.png`
- `output/fig_growth_rank.png`
- `output/fig_coastal_inland.png`
- `output/fig01_2025_gdp_top15.png`
- `output/fig02_2025_region_gdp_share.png`
- `output/fig03_2025_sector_structure.png`
- `output/fig04_2025_gdp_income_scatter.png`
- `output/fig05_2011_2024_gdp_trends_top8.png`
- `output/fig06_gdp_rank_change.png`
- `output/fig07_gdp_growth_heatmap.png`
- `output/china_provincial_economy_dashboard.html`
- `output/data_quality_summary.md`

## 小组分工

| 成员 | 学号 | 分工 |
|---|---|---|
| 龙昊文 | 25210204 | 项目统筹、报告整合、结果审核 |
| 潘福璋 | 25210218 | 数据来源核对、原始数据整理 |
| 沈婷婷 | 25210230 | 数据清洗、变量字典与质量检查 |
| 张璇 | 25210303 | 探索性分析、指标解释 |
| 许博东 | 25210269 | 可视化图表设计与输出 |
| 张梦洁 | 25210299 | HTML 看板与报告排版 |
| 吴小飞 | 25210261 | 代码复现、环境检查 |
| 高一婷 | 25210134 | README、AI 使用记录与提交材料检查 |

## 数据质量说明

- 2011-2024 年 GDP 面板：31 省、434 条记录，GDP 无缺失。
- 2025 年横截面：31 省、24 个字段。部分省份未披露城镇化率、人口自然增长率、全体居民收入或社消总额，保留为空值，不做插值。
- 2025 年数据为初步统计数，正式口径以后续统计年鉴为准。

## AI 使用说明

本项目使用 AI 工具辅助项目结构设计、代码编写、报告润色和可视化方案设计。详细提示词记录见 `prompts/AI_PROMPTS.md`。
