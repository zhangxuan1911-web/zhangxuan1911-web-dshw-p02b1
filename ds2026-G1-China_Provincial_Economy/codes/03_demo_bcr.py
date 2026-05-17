import pandas as pd
import bar_chart_race as bcr
import os
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

df = pd.read_csv(
    os.path.join(os.path.dirname(__file__), '..', 'data_clean', 'gdp_panel_long_2011_2024.csv')
)

df_wide = df.pivot(index='year', columns='province', values='gdp')

df_wide.index = df_wide.index.astype(int)

year_labels = [str(y) for y in df_wide.index]

out_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
os.makedirs(out_dir, exist_ok=True)

bcr.bar_chart_race(
    df=df_wide,
    n_bars=15,
    sort='desc',
    title='中国各省GDP总量排名动态变化 (2011-2024)',
    filename=os.path.join(out_dir, 'gdp_bar_chart_race.html'),
    figsize=(7, 5),
    period_length=800,
    bar_size=0.85,
    bar_label_size=9,
    tick_label_size=9,
)

print('Done! Output: output/gdp_bar_chart_race.html')
