import sys, os
sys.path.insert(0, os.path.abspath('.'))
sys.stdout.reconfigure(encoding='utf-8')

# Mock test of record_daily_close with sort key on 09.25
records = [
    {'Date': '2026-09-22', 'R': 159, 'Close': 151.95, 'S': 24184.20, 'U': 156.13, 'Sold': False, 'Profit': 0.0},
    {'Date': '2026-09-23', 'R': 159, 'Close': 146.25, 'S': 23277.72, 'U': 150.28, 'Sold': False, 'Profit': 0.0},
    {'Date': '2026-09-24', 'R': 159, 'Close': 146.33, 'S': 23290.46, 'U': 150.36, 'Sold': False, 'Profit': 0.0}
]

close_p = 151.45
sell_p = 151.45
sell_q = 318
shares_to_sell = sell_q
fee_rate = 0.001
sec_fee = 0.0000278

unsold_lots = [r for r in records if r.get('R', 0) > 0 and not r.get('Sold', False)]

def get_sort_key(lot):
    u_val = float(lot.get('U', 999999.0)) if lot.get('U') is not None else 999999.0
    is_target_reached = (close_p >= u_val - 1e-4)
    priority = 0 if is_target_reached else 1
    return (priority, u_val)

sorted_unsold_lots = sorted(unsold_lots, key=get_sort_key)

total_profit = 0.0
net_sell_proceeds = 0.0

for lot in sorted_unsold_lots:
    if shares_to_sell <= 0:
        break
    lot_r = int(lot['R'])
    if lot_r <= shares_to_sell:
        lot['Sold'] = True
        lot['W'] = '2026-09-25'
        lot['X'] = sell_p
        gross_s = sell_p * lot_r
        net_s = gross_s - gross_s * (fee_rate + sec_fee)
        lot['Z'] = round(net_s, 2)
        p_amt = net_s - float(lot.get('S', 0.0))
        lot['Profit'] = round(p_amt, 2)
        total_profit += p_amt
        net_sell_proceeds += net_s
        shares_to_sell -= lot_r

print("Total profit from sell:", total_profit)
print("Net sell proceeds:", net_sell_proceeds)
print("\nLots status after sell:")
for r in records:
    print(f"Date: {r['Date']}, Sold: {r['Sold']}, Profit: ${r['Profit']:.2f}")
