import sys
sys.path.insert(0, '.')
from gui.account_manager import AccountManager

mgr = AccountManager()
accounts = mgr.load_accounts()
acc = accounts[0]
today_orders = mgr.compute_account_details(acc)

close_p = 151.95
sell_orders = today_orders.get('sell_orders', [])
buy_orders = today_orders.get('buy_orders', [])
records = acc.get('trade_records', [])
unsold_lots = [r for r in records if r.get('R', 0) > 0 and not r.get('Sold', False)]

print('unsold_lots:', len(unsold_lots))

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
    filled_sells.append(f"{lot.get('Date', '')} 로트({q}주@목표${u_p:.2f})")

auto_buy_qty = 0
filled_buys = []
for b in buy_orders:
    p = float(b.get('price', 0.0))
    q = int(b.get('qty', 0))
    if p > 0 and q > 0:
        if close_p <= p + 1e-4:
            auto_buy_qty += q
            filled_buys.append(f"{b.get('호가단계', '매수')}({q}주@${p:.2f})")

print('auto_sell_qty:', auto_sell_qty)
print('filled_sells:', filled_sells)
print('auto_buy_qty:', auto_buy_qty)
print('filled_buys:', filled_buys)
