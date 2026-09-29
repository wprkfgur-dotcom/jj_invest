import sys, os
sys.path.insert(0, os.path.abspath('.'))
sys.stdout.reconfigure(encoding='utf-8')

from gui.order_netting import generate_jongjong_orders
from strategies.jongjong import JongJongStrategy
from strategies.jongjong import safe_round4, round_down, excel_round

# Let's test the improved generate_jongjong_orders formula without tung_lot
AU1 = 26942.40  # p_budget
AU2 = 141.93    # yest_close
mode = 'Normal'
is_normal = (mode == 'Normal')
is_riskoff = (mode == 'Riskoff')
C2 = 0.128
C3 = -0.17
C4 = 5
C6 = 0.7
O4 = -0.055

a_val = C2 if is_normal else (O4 if is_riskoff else 0.0)
AY2 = safe_round4(AU2 * (1.0 + a_val) - 0.01)
AZ2 = int(AU1 / AY2) if AY2 > 0 else 0
AY3 = safe_round4(AU2 * (1.0 - C2))

AY4 = C4 - 1
ay_list = [AY2]
for i_seq in range(AY4 - 1):
    denom = AY3 + ((AY4 - 2.0 - i_seq) / (AY4 - 2.0)) ** C6 * (AY2 - AY3)
    val = round_down(denom, 2)
    ay_list.append(val)

az_list = [AZ2]
for k in range(1, len(ay_list)):
    diff = int(AU1 / ay_list[k]) - int(AU1 / ay_list[k-1])
    az_list.append(max(0, diff))

print("AY2:", AY2)
print("AZ2:", AZ2)
for idx, (p, q) in enumerate(zip(ay_list, az_list)):
    print(f"  {idx+1}차: ${p:.2f}, {q}주")

# Crash order:
BE4 = round_down(AU2 * (1.0 + C3), 2)
BF4 = excel_round(AU1 / BE4, 0)
print(f"  폭락: ${BE4:.2f}, {BF4}주")

# If close is 151.95:
close_p = 151.95
auto_buy_qty = sum(q for p, q in zip(ay_list, az_list) if close_p <= p)
if close_p < BE4:
    auto_buy_qty += BF4

print(f"\nWhen close_p = {close_p}:")
print(f"Auto buy qty: {auto_buy_qty}주 (Expected: 168주)")
