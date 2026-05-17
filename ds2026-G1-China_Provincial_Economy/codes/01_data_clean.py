import pandas as pd
import numpy as np
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DATA_RAW = BASE / 'data_raw'
DATA_CLEAN = BASE / 'data_clean'
DATA_CLEAN.mkdir(exist_ok=True)

# ============================================================
# 1. 读取宽表 GDP 数据 (2011-2025)
# ============================================================
# 该文件为 UTF-8 CSV，字段用双引号包裹，内部含尾随制表符
df_wide = pd.read_csv(
    DATA_RAW / 'nbs_gdp_wide_2011_2025.csv',
    skiprows=2,
    nrows=31,
    dtype=str,
    encoding='utf-8',
)

# 清洗列名：去除尾随制表符和"年"字
col_rename = {}
for c in df_wide.columns:
    clean = c.strip().replace('\t', '')
    clean = clean.replace('年', '')
    col_rename[c] = clean
df_wide.rename(columns=col_rename, inplace=True)

# 清洗所有字符串值：去除首尾空格和制表符
for col in df_wide.columns:
    df_wide[col] = df_wide[col].apply(lambda x: x.strip().replace('\t', '') if pd.notna(x) and isinstance(x, str) else x)

# 省份标准化映射
province_map = {
    '北京市': '北京', '天津市': '天津', '河北省': '河北', '山西省': '山西',
    '内蒙古自治区': '内蒙古', '辽宁省': '辽宁', '吉林省': '吉林', '黑龙江省': '黑龙江',
    '上海市': '上海', '江苏省': '江苏', '浙江省': '浙江', '安徽省': '安徽',
    '福建省': '福建', '江西省': '江西', '山东省': '山东', '河南省': '河南',
    '湖北省': '湖北', '湖南省': '湖南', '广东省': '广东', '广西壮族自治区': '广西',
    '海南省': '海南', '重庆市': '重庆', '四川省': '四川', '贵州省': '贵州',
    '云南省': '云南', '西藏自治区': '西藏', '陕西省': '陕西', '甘肃省': '甘肃',
    '青海省': '青海', '宁夏回族自治区': '宁夏', '新疆维吾尔自治区': '新疆',
}

province_col = [c for c in df_wide.columns if c in province_map or c == '地区']
if province_col:
    old_name = province_col[0]
else:
    old_name = df_wide.columns[0]

df_wide['province'] = df_wide[old_name].map(province_map).fillna(df_wide[old_name])
df_wide.drop(columns=[old_name], inplace=True)

# 确认数值列并排除空值的2025列
year_cols = [c for c in df_wide.columns if c != 'province' and c.isdigit()]
year_cols = [c for c in year_cols if c != '2025']

for col in year_cols:
    df_wide[col] = pd.to_numeric(df_wide[col], errors='coerce')

# 宽表转长表
df_long = df_wide.melt(
    id_vars=['province'],
    value_vars=year_cols,
    var_name='year',
    value_name='gdp',
)
df_long['year'] = df_long['year'].astype(int)
df_long = df_long.sort_values(['province', 'year']).reset_index(drop=True)

# 计算同比增速
df_long['gdp_growth'] = df_long.groupby('province')['gdp'].pct_change() * 100

# 保留 2011-2024 面板（2025 为空无增速）
df_panel = df_long[df_long['year'] <= 2024].copy()

# ============================================================
# 2. 读取长表 GDP 数据（备份来源，tab分隔但表头用逗号）
# ============================================================
# 用纯文本方式解析该不规则文件
with open(DATA_RAW / 'nbs_gdp_long_2011_2025.csv', 'r', encoding='utf-8') as f:
    raw_lines = f.readlines()

records = []
for line in raw_lines[1:]:  # 跳过表头行
    line = line.strip()
    if not line:
        continue
    # 按第一个 tab 切分省份，剩余部分按逗号切分年份和 GDP
    parts = line.split('\t', maxsplit=2)
    if len(parts) >= 2:
        prov = parts[0].strip()
        rest = parts[1].strip()
        rest_parts = rest.split(',')
        if len(rest_parts) >= 2:
            yr = rest_parts[0].strip()
            gdp_val = rest_parts[1].strip()
            records.append({'province': prov, 'year': yr, 'gdp': gdp_val})

df_long_raw = pd.DataFrame(records)
df_long_raw['province'] = df_long_raw['province'].map(province_map).fillna(df_long_raw['province'])
df_long_raw['gdp'] = pd.to_numeric(df_long_raw['gdp'], errors='coerce')
df_long_raw['year'] = pd.to_numeric(df_long_raw['year'], errors='coerce', downcast='integer')
df_long_raw = df_long_raw.dropna(subset=['gdp']).sort_values(['province', 'year']).reset_index(drop=True)
df_long_raw['gdp_growth'] = df_long_raw.groupby('province')['gdp'].pct_change() * 100

# ============================================================
# 3. 处理 2025 年横截面数据
# ============================================================
df_cross = pd.read_csv(
    DATA_RAW / 'provincial_indicators_2025.csv',
    dtype=str,
    encoding='utf-8',
)

# 标准化省份名
df_cross['province'] = df_cross['省份'].map(province_map).fillna(df_cross['省份'])

# 数值列转换
value_cols = [c for c in df_cross.columns if c not in ('地区分类', '省份', 'province')]
for col in value_cols:
    df_cross[col] = pd.to_numeric(df_cross[col], errors='coerce')

df_cross.rename(columns={'地区分类': 'region'}, inplace=True)
if '省份' in df_cross.columns:
    df_cross.drop(columns=['省份'], inplace=True)

# ============================================================
# 4. 输出清洗文件
# ============================================================
# 从宽表清洗的面板（主要来源）
df_panel.to_csv(DATA_CLEAN / 'gdp_panel_long_2011_2024.csv', index=False, encoding='utf-8-sig')

# 宽表格式输出
df_wide_out = df_wide[['province'] + sorted(year_cols, key=int, reverse=True)]
df_wide_out.to_csv(DATA_CLEAN / 'gdp_panel_wide_2011_2024.csv', index=False, encoding='utf-8-sig')

# 2025 年横截面
df_cross.to_csv(DATA_CLEAN / 'provincial_indicators_2025_clean.csv', index=False, encoding='utf-8-sig')

# 最新年份对比表 (latest_year.csv)
df_latest = df_panel[df_panel['year'] == df_panel['year'].max()].copy()
df_latest = df_latest[['province', 'year', 'gdp', 'gdp_growth']].sort_values('gdp', ascending=False)
df_latest.to_csv(DATA_CLEAN / 'latest_year.csv', index=False, encoding='utf-8-sig')

# 合并面板（从长表备份补充的完整数据）
df_combined = df_panel.copy()
# 如需要整合长表来源的工业/消费数据可在此扩展
df_combined.to_csv(DATA_CLEAN / 'gdp_panel.csv', index=False, encoding='utf-8-sig')

# 数据字典
data_dict = pd.DataFrame({
    'variable': ['province', 'year', 'gdp', 'gdp_growth', 'region', 'gdp_100m'],
    'description': [
        '省份名称（标准化简写）',
        '年份',
        '地区生产总值（亿元）',
        'GDP同比增速（%）',
        '地区分类（东部/东北/中部/西部）',
        '地区生产总值（亿元，宽表用）',
    ],
    'source': [
        '国家统计局', '国家统计局', '国家统计局', '计算派生', '国家统计局', '国家统计局',
    ],
})
data_dict.to_csv(DATA_CLEAN / 'data_dictionary.csv', index=False, encoding='utf-8-sig')

# ============================================================
# 5. 质量报告
# ============================================================
print('=== 数据清洗完成 ===')
print(f'GDP 面板（长表）: {df_panel.shape[0]} 行 × {df_panel.shape[1]} 列')
print(f'  年份范围: {df_panel["year"].min()} — {df_panel["year"].max()}')
print(f'  省份数: {df_panel["province"].nunique()}')
print(f'  GDP 缺失: {df_panel["gdp"].isna().sum()}')
print(f'  增速缺失: {df_panel["gdp_growth"].isna().sum()}')
print()
print(f'GDP 面板（宽表）: {df_wide_out.shape[0]} 行 × {df_wide_out.shape[1]} 列')
print(f'2025 横截面: {df_cross.shape[0]} 行 × {df_cross.shape[1]} 列')
print(f'  数值列: {[c for c in df_cross.columns if c not in ("province", "region")]}')
print()
print('输出文件:')
for f in ['gdp_panel_long_2011_2024.csv', 'gdp_panel_wide_2011_2024.csv',
          'provincial_indicators_2025_clean.csv', 'latest_year.csv',
          'gdp_panel.csv', 'data_dictionary.csv']:
    print(f'  ✓ data_clean/{f}')
