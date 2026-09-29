import sys, os
sys.path.insert(0, os.path.abspath('.'))
sys.stdout.reconfigure(encoding='utf-8')

from core.data import fetch_market_data
from strategies.jongjong import JongJongStrategy

strat = JongJongStrategy(initial_capital=150000.0)
df = fetch_market_data('SOXL', '2026-01-01', '2026-09-25')
df_res = strat.run(df, '2026-01-02', '2026-09-25')

for idx, r in df_res.iterrows():
    d_str = r['Date'].strftime('%Y-%m-%d')
    if d_str in ['2026-09-18', '2026-09-21', '2026-09-22']:
        print(d_str, 'Mode:', r['Mode'], 'Flag:', r.get('Flag'), 'R:', r['R'], 'ay_valid:', r.get('ay_valid'))
