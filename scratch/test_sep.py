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
    if d_str in ['2026-09-18', '2026-09-21', '2026-09-22', '2026-09-23', '2026-09-24', '2026-09-25']:
        print(f"{d_str} | Close: {r['Close']} | Mode: {r['Mode']} | R: {r['R']} | U: {r['U']} | Cash: {r['Cash']:,.2f} | AR: {r['AR']:,.2f} | P: {r['P']:,.2f}")
