# Test netting on user screenshot scenario

raw_sell_orders = [
    {'price': 155.62, 'qty': 338, 'type': 'LOC 매도'}
]

raw_buy_orders = [
    {'price': 170.83, 'qty': 39, 'type': 'LOC 매수'},
    {'price': 170.82, 'qty': 39, 'type': 'LOC 매수'},
    {'price': 155.92, 'qty': 39, 'type': 'LOC 매수'},
    {'price': 132.06, 'qty': 39, 'type': 'LOC 매수'},
]

print("=== RAW ORDERS ===")
for s in raw_sell_orders:
    print(f"SELL: {s['qty']}주 if Close >= ${s['price']:.2f}")
for b in raw_buy_orders:
    print(f"BUY:  {b['qty']}주 if Close <= ${b['price']:.2f}")

# Critical price points:
# Let's collect all prices and test demand/supply at prices around the cutoffs
cutoffs = sorted(set([s['price'] for s in raw_sell_orders] + [b['price'] for b in raw_buy_orders]), reverse=True)
print("\nCutoff prices:", cutoffs)

def get_demand(price):
    return sum(b['qty'] for b in raw_buy_orders if price <= b['price'])

def get_supply(price):
    return sum(s['qty'] for s in raw_sell_orders if price >= s['price'])

print("\n=== AT KEY PRICE LEVELS ===")
for p in [175.0, 170.83, 170.82, 160.0, 155.92, 155.62, 155.0, 132.06, 120.0]:
    d = get_demand(p)
    s = get_supply(p)
    net = d - s
    self_trade = min(d, s)
    action = f"NET BUY {net}주" if net > 0 else (f"NET SELL {-net}주" if net < 0 else "0주 (완전상계)")
    print(f"Price ${p:6.2f} -> Gross Buy: {d:3d}주, Gross Sell: {s:3d}주 | Self-Trade(상계): {self_trade:3d}주 | Net: {action}")
