import sys, os
sys.path.insert(0, os.path.abspath('.'))
sys.stdout.reconfigure(encoding='utf-8')

from core.data import fetch_market_data
from strategies.jongjong import JongJongStrategy

strat = JongJongStrategy(initial_capital=150000.0)
df = fetch_market_data('SOXL', '2026-01-01', '2026-09-25')

# Let's inspect step by step on 09-22
df_prep = strat.prepare_indicators(df, '2026-01-02')
idx_0921 = df_prep[df_prep['Date'] == '2026-09-21'].index[0]
idx_0922 = df_prep[df_prep['Date'] == '2026-09-22'].index[0]

# Let's run simulation and inspect exactly at 09-22
df_res = strat.run(df, '2026-01-02', '2026-09-25')
r_0922 = df_res[df_res['Date'] == '2026-09-22'].iloc[0]
print("09-22 Close:", r_0922['Close'])
print("09-22 R:", r_0922['R'])
print("09-22 ay_valid:", r_0922.get('ay_valid'))
print("09-22 bb_valid:", r_0922.get('bb_valid'))
print("09-22 BE_col:", r_0922.get('BE_col'))
print("09-22 BF_col:", r_0922.get('BF_col'))
print("09-22 BH_orders:", r_0922.get('BH_orders'))
