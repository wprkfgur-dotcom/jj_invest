import sys
sys.path.insert(0, '.')
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
from gui.account_manager import AccountManager

mgr = AccountManager()
acc = mgr.load_accounts()[0]
recs = [r for r in acc['trade_records'] if r['Date'] <= '2026-09-24']
for r in recs:
    if r['Date'] in ['2026-09-22', '2026-09-23', '2026-09-24']:
        r['Sold'] = False
        r['W'] = None
        r['X'] = None
acc_copy = dict(acc)
acc_copy['trade_records'] = recs
acc_copy['current_date'] = '2026-09-25'
details = mgr.compute_account_details(acc_copy)
sell_orders = details.get('sell_orders', [])

close_p = 151.45
unsold_lots = [r for r in recs if r.get('R', 0) > 0 and not r.get('Sold', False)]

target_reached_lots = []
for lot in unsold_lots:
    u_p = float(lot.get('U', 0.0)) if lot.get('U') is not None else 0.0
    if u_p > 0 and close_p >= u_p - 1e-4:
        target_reached_lots.append(lot)

auto_sell_qty = 0
filled_sells = []
for lot in target_reached_lots:
    q = int(lot['R'])
    u_p = float(lot['U'])
    auto_sell_qty += q
    filled_sells.append(f"{lot.get('Date')} 로트({q}주@목표${u_p:.2f})")

print('From target_reached_lots: auto_sell_qty =', auto_sell_qty)
print('Target reached lots:', [l['Date'] for l in target_reached_lots])

for s in sell_orders:
    p = float(s.get('price', 0.0))
    q = int(s.get('qty', 0))
    if p > 0 and q > 0 and close_p >= p - 1e-4:
        s_name = str(s.get('구분', '매도'))
        if not any(str(lot.get('Date', '')) in s_name for lot in target_reached_lots):
            total_unsold_shares = sum(int(l['R']) for l in unsold_lots)
            if auto_sell_qty + q <= total_unsold_shares:
                auto_sell_qty += q
                filled_sells.append(f"{s_name}({q}주@${p:.2f})")

print('After sell_orders: auto_sell_qty =', auto_sell_qty)
print('Filled sells:', filled_sells)
