import sys, os
sys.path.insert(0, os.path.abspath('.'))
from core.data import fetch_market_data
from strategies.jongjong import JongJongStrategy

df_soxl = fetch_market_data('SOXL', '2018-01-01', '2026-09-25')
strat = JongJongStrategy(initial_capital=150000.0)
df_res = strat.run(df_soxl, start_date='2026-01-02', end_date='2026-09-25')

tail = df_res.tail(10)
for idx, r in tail.iterrows():
    u_val = f"{r['U']:6.2f}" if r['U'] is not None else "  None"
    print(f"{r['Date'].strftime('%m.%d.')} Close: {r['Close']:6.2f} Mode: {r['Mode']:7} R: {r['R']:3} U: {u_val} Sold: {str(r['Sold']):5} Hold: {r['Hold']:3}")
