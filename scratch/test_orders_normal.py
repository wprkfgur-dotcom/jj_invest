import sys, os
sys.path.insert(0, os.path.abspath('.'))
sys.stdout.reconfigure(encoding='utf-8')

from gui.order_netting import generate_jongjong_orders
from strategies.jongjong import JongJongStrategy

strat = JongJongStrategy(initial_capital=150000.0)

# On 2026-09-21:
# close = 141.93
# cash = 241,418.43
# AR = 215,539.22 (or 204,013.40)
# p_budget = AR / 8.0 = 26,942.40 (or 25,501.68)
p_budget = 215539.22 / 8.0

orders_normal = generate_jongjong_orders(
    unsold_lots=[],
    yest_close=141.93,
    p_budget=p_budget,
    mode='Normal',
    C2=0.128,
    C3=-0.17,
    C4=5,
    C6=0.7,
    target_yield=0.0275
)

print("=== Orders with mode='Normal' ===")
for b in orders_normal['net_buy_orders']:
    print(b)

# Now check fill if close = 151.95
close_p = 151.95
filled_buys = [b for b in orders_normal['net_buy_orders'] if close_p <= b['price']]
print(f"\nIf close is {close_p}:")
print("Filled buys count:", len(filled_buys))
for b in filled_buys:
    print("  Filled:", b)
