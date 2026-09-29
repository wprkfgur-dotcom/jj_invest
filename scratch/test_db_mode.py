import sys, os
sys.path.insert(0, os.path.abspath('.'))
sys.stdout.reconfigure(encoding='utf-8')

from core.data import fetch_market_data
from strategies.jongjong import JongJongStrategy

strat = JongJongStrategy(initial_capital=150000.0)
df = fetch_market_data('SOXL', '2026-01-01', '2026-09-25')
df = strat.prepare_indicators(df, '2026-01-02')

idx_0921 = df[df['Date'] == '2026-09-21'].index[0]
idx_0922 = df[df['Date'] == '2026-09-22'].index[0]

print('09-21 DB_Mode:', df.loc[idx_0921, 'DB_Mode'])
print('09-22 DB_Mode:', df.loc[idx_0922, 'DB_Mode'])
