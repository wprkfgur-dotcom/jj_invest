import sys, os
sys.path.insert(0, os.path.abspath('.'))
sys.stdout.reconfigure(encoding='utf-8')

from gui.order_netting import generate_jongjong_orders

# Lots before 9월 25일:
# 09.22 lot: bought at 151.95 -> U: 156.13, 159 shares
# 09.23 lot: bought at 146.25 -> U: 150.28, 159 shares
# 09.24 lot: bought at 146.33 -> U: 150.36, 159 shares
# Yesterday close (09.24): 146.33
yest_close = 146.33

unsold_lots = [
    {'date': '09.22', 'R': 159, 'U': 156.13, 'hold_days': 3, 't': 0},
    {'date': '09.23', 'R': 159, 'U': 150.28, 'hold_days': 2, 't': 1},
    {'date': '09.24', 'R': 159, 'U': 150.36, 'hold_days': 1, 't': 2}
]

res = generate_jongjong_orders(
    unsold_lots=unsold_lots,
    yest_close=yest_close,
    p_budget=25000.0,
    mode='Normal',
    C2=0.128,
    C3=-0.17,
    C4=5,
    C6=0.7,
    target_yield=0.0275
)

print("Sell orders on 09.25:")
for s in res['net_sell_orders']:
    print(s)

print("\nBuy orders on 09.25:")
for b in res['net_buy_orders']:
    print(b)

# Now check fill if close = 151.45
close_p = 151.45
print(f"\nWhen close_p = {close_p}:")
filled_sells = [s for s in res['net_sell_orders'] if close_p >= s['price'] - 1e-4]
print("Filled sells count:", len(filled_sells))
for s in filled_sells:
    print("  Filled sell:", s)
total_sell_qty = sum(s['qty'] for s in filled_sells)
print("Total sell qty:", total_sell_qty)

filled_buys = [b for b in res['net_buy_orders'] if close_p <= b['price'] + 1e-4]
print("Filled buys count:", len(filled_buys))
for b in filled_buys:
    print("  Filled buy:", b)
total_buy_qty = sum(b['qty'] for b in filled_buys)
print("Total buy qty:", total_buy_qty)
