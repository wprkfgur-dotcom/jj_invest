import sys, os
sys.path.insert(0, os.path.abspath('.'))
sys.stdout.reconfigure(encoding='utf-8')

from core.data import fetch_market_data
from strategies.jongjong import JongJongStrategy

strat = JongJongStrategy(initial_capital=150000.0)
df = fetch_market_data('SOXL', '2026-01-01', '2026-09-25')
df_prep = strat.prepare_indicators(df, '2026-01-02')

# Let's inspect the exact formulas for 2026-09-22 (db_idx for 09-22)
idx_0922 = df_prep[df_prep['Date'] == '2026-09-22'].index[0]

yest_close = df_prep.loc[idx_0922 - 1, 'Close'] # 141.93
close_p = df_prep.loc[idx_0922, 'Close']       # 151.95

# On 09-22:
# ar_val = 215,539.22
# p_budget = ar_val / 8.0 = 26,942.40
AU1 = 26942.40
AU2 = yest_close # 141.93
C2 = 0.128
C4 = 5
C6 = 0.7

BB3 = 141.93 * 1.128 # 160.097
# No unsold lots, so AU3 = None, AV3 = 0, AV7 = 0
AY2 = round(AU2 * (1.0 + C2) - 0.01, 4) # 160.087
AZ2 = int(AU1 / AY2) # int(26942.40 / 160.087) = 168주!
AY3 = round(AU2 * (1.0 - C2), 4) # 123.763

AY4 = C4 - 1 # 4
ay_list = [AY2]
for i_seq in range(AY4 - 1):
    denom = AY3 + ((AY4 - 2.0 - i_seq) / (AY4 - 2.0)) ** C6 * (AY2 - AY3)
    val = round(denom, 2)
    ay_list.append(val)

az_list = [AZ2]
for k in range(1, len(ay_list)):
    az_list.append(int(AU1 / ay_list[k]) - int(AU1 / ay_list[k-1]))

print("ay_list (prices):", ay_list)
print("az_list (quantities):", az_list)
print(f"1st order: Price {ay_list[0]}, Qty {az_list[0]}")
if close_p <= ay_list[0]:
    print(f"Close {close_p} <= {ay_list[0]} -> FILLED! Qty: {az_list[0]} shares!")
