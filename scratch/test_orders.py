import sys, os
sys.path.insert(0, os.path.abspath('.'))
from core.data import fetch_market_data
from strategies.jongjong import JongJongStrategy

df_soxl = fetch_market_data('SOXL', '2018-01-01', '2026-09-25')
strat = JongJongStrategy(initial_capital=150000.0)
df_res = strat.run(df_soxl, start_date='2026-01-02', end_date='2026-09-25')

last_row = df_res.iloc[-1]
print("Last row Date:", last_row['Date'], "Close:", last_row['Close'], "Hold:", last_row['Hold'], "Cash:", last_row['Cash'])

import math

def safe_round4(val):
    if val is None:
        return None
    return round(float(val), 4)

def round_down(val, dec):
    factor = 10.0 ** dec
    return math.floor(val * factor + 1e-9) / factor

def round_up(val, dec):
    factor = 10.0 ** dec
    return math.ceil(val * factor - 1e-9) / factor

def excel_round(val, dec):
    factor = 10.0 ** dec
    return math.floor(val * factor + 0.5) / factor

# Parameters
C2 = strat.range_normal      # 0.128
C3 = strat.range_crash       # -0.17
C4 = strat.order_split_count # 5
C6 = strat.order_curvature   # 0.7
O4 = strat.risk_buy_offset   # -0.055
M3 = strat.max_hold_days     # 10

mode = 'Normal'
is_normal = True
is_riskoff = False
yest_close = 151.45
ar_val = float(last_row['AR']) if 'AR' in last_row else 150000.0
div = strat.div_rounds[mode]
p_budget = min(ar_val / div, float(last_row['Cash']))
AU1 = max(0.0, p_budget)
AU2 = yest_close

# Unsold lots:
# t is current day index (184)
# Lot 1: t=180, R=169, U=156.29 -> 184 - 180 = 4 days (< 10)
# Lot 2: t=183, R=169, U=155.78 -> 184 - 183 = 1 day (< 10)
# Neither is MOC!
AV7 = 0
has_moc = False

BB3 = round_down(AU2 * (1.0 + C2), 2)
print("BB3 (Upper bound):", BB3)

min_u = 155.78 # Lot 2
AU3 = min_u if (is_normal and BB3 >= min_u) else None
AV3 = 169 if AU3 is not None else 0

print("AU3 (Min target):", AU3, "AV3 (Min target qty):", AV3)

a_val = C2
if is_normal and AU3 is not None and AU3 <= AU2 * (1.0 + a_val):
    AY2 = safe_round4(AU3 - 0.01)
else:
    AY2 = safe_round4(AU2 * (1.0 + a_val) - 0.01)

AZ2 = int(AU1 / AY2) if AY2 > 0 else 0
BB2 = safe_round4(AU2 * (1.0 + a_val)) if ((not is_normal) and has_moc) else AU3
BC2 = int(AU1 / BB2) if (is_normal and BB2 is not None and BB2 > 0) else 0
AY3 = safe_round4(AU2 * (1.0 - C2))

print("AY2:", AY2, "AZ2:", AZ2, "BB2:", BB2, "BC2:", BC2, "AY3:", AY3)

if AU3 is not None and (BB3 - AY3) != 0:
    AY4 = excel_round((AY2 - AY3) / (BB3 - AY3) * (C4 - 2) + 1.0, 0) - 1
else:
    AY4 = C4 - 1
BB4 = C4 - 2 - AY4
print("AY4:", AY4, "BB4:", BB4)

ay_list = [AY2]
if AY4 - 1 > 0:
    for i_seq in range(int(AY4 - 1)):
        if AY4 - 2 == 0:
            ay_list.append(None)
        else:
            denom = AY3 + ((AY4 - 2.0 - i_seq) / (AY4 - 2.0)) ** C6 * (AY2 - AY3)
            val = round_down(AU1 / (AU1 / denom), 2) if (AU1 > 0 and denom > 0) else None
            ay_list.append(val)

az_list = [AZ2 - AV7]
for k in range(1, len(ay_list)):
    if ay_list[k] is None or ay_list[k-1] is None or ay_list[k] <= 0 or ay_list[k-1] <= 0:
        az_list.append(None)
    else:
        az_list.append(int(AU1 / ay_list[k]) - int(AU1 / ay_list[k-1]))

if any(x is None for x in ay_list):
    AZ4 = 1
    ay_valid = [AY2] if (AZ2 - AV7) != 0 else []
else:
    AZ4 = len(ay_list)
    ay_valid = [ay_list[k] for k in range(len(ay_list)) if az_list[k] != 0]

print("ay_list:", ay_list)
print("az_list:", az_list)
print("ay_valid:", ay_valid)

bb_list, bc_list = [], []
if AU3 is not None or has_moc:
    bb_list.append(BB2)
    bc_list.append(AV3 + AV7 - BC2)
if AU3 is not None and BB4 - 1 > 0:
    for i_seq in range(int(BB4 - 1)):
        if BB4 - 2 == 0:
            bb_list.append(None)
            bc_list.append(None)
        else:
            denom = BB3 - ((BB4 - 2.0 - i_seq) / (BB4 - 2.0)) ** C6 * (BB3 - BB2)
            val = round_down(AU1 / (AU1 / denom), 2) if (AU1 > 0 and denom > 0) else None
            prev_p = bb_list[-1]
            bb_list.append(val)
            if val is None or prev_p is None or val <= 0 or prev_p <= 0:
                bc_list.append(None)
            else:
                bc_list.append(int(AU1 / prev_p) - int(AU1 / val))

if any(x is None for x in bb_list):
    BC4 = 1
    bb_valid = [bb_list[0]] if (len(bc_list) > 0 and bc_list[0] is not None and bc_list[0] != 0 and bb_list[0] is not None) else []
else:
    BC4 = len(bb_list)
    bb_valid = [bb_list[k] for k in range(len(bb_list)) if bc_list[k] != 0 and bb_list[k] is not None]

print("bb_list:", bb_list)
print("bc_list:", bc_list)
print("bb_valid:", bb_valid)

BE3 = round(round_down(AU1 / (AV3 + 1.0), 2) + 0.01, 2) if AV3 > 0 else None
BE4 = safe_round4(AU2 * (1.0 + C3))
BF4 = excel_round(AU1 / BE4, 0) if BE4 > 0 else 0

be_candidates = list(ay_valid) + list(bb_valid)
if BE3 is not None and AY3 <= BE3 <= BB3:
    be_candidates.append(BE3)
if AZ4 == 1:
    be_candidates.append(AY3)
if BC4 == 1:
    be_candidates.append(BB3)
BE_col = sorted(be_candidates, reverse=True)

BF_col = []
for p in BE_col:
    b_cond = 0 if ((not is_normal) and (BB2 is not None and BB2 <= p)) else 1
    a_calc = (int(AU1 / p) if p > 0 else 0) * b_cond * (1 if p < BB3 else 0) - AV7 - (AV3 if (AU3 is not None and p >= AU3) else 0)
    if AU3 is not None and p >= AU3 and a_calc > 0:
        bf_val = (int(AU1 / (p - 0.01)) if (p - 0.01) > 0 else 0) - AV7 - AV3
    else:
        bf_val = a_calc
    BF_col.append(bf_val)

print("\nBE_col (Prices):", BE_col)
print("BF_col (Net Demand):", BF_col)

BH_orders = []
for k in range(len(BE_col)):
    p, bf = BE_col[k], BF_col[k]
    bf_prev = BF_col[k-1] if k > 0 else None
    bf_next = BF_col[k+1] if k + 1 < len(BE_col) else 0
    p_next = BE_col[k+1] if k + 1 < len(BE_col) else None

    if bf > 0:
        if bf_prev is not None and bf_prev == 0:
            continue
        deduct = 0.01 if (AU3 is not None and p >= AU3 and p != BB2) else 0.0
        ord_q = bf - (bf_prev if (bf_prev is not None and bf_prev > 0) else 0)
        if ord_q != 0:
            BH_orders.append(("매수", safe_round4(p - deduct), ord_q))
    elif bf < 0:
        add = 0.01 if (p_next is not None and p == p_next and bf < 0 and bf_next > 0) else 0.0
        ord_q = (bf_next if bf_next < 0 else 0) - bf
        if ord_q != 0:
            BH_orders.append(("매도", safe_round4(p + add), ord_q))

print("\nBH_orders (Netted Orders):", BH_orders)

