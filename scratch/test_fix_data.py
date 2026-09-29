import sys
sys.path.insert(0, '.')
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import json
from gui.account_manager import AccountManager

mgr = AccountManager()
accounts = mgr.load_accounts()
acc = accounts[0]

# Let's inspect current state
records = acc.get('trade_records', [])
r22 = next(r for r in records if r['Date'] == '2026-09-22')
r23 = next(r for r in records if r['Date'] == '2026-09-23')
r24 = next(r for r in records if r['Date'] == '2026-09-24')
r25 = next(r for r in records if r['Date'] == '2026-09-25')

# Fix r22 (remain unsold)
r22['Sold'] = False
r22['W'] = None
r22['X'] = None
r22['Profit'] = None
r22['StatusText'] = "🟢 매도 대기 (159주 / 보유)"
r22['Tag'] = "tag_active"

# r23 (sold on 09-25)
r23['Sold'] = True
r23['W'] = '2026-09-25'
r23['X'] = 151.45
r23['Profit'] = 778.80
r23['StatusText'] = "🔴 익절 완료 (+$779)"
r23['Tag'] = "tag_profit_pos"

# r24 (sold on 09-25)
r24['Sold'] = True
r24['W'] = '2026-09-25'
r24['X'] = 151.45
r24['Profit'] = 766.06
r24['StatusText'] = "🔴 익절 완료 (+$766)"
r24['Tag'] = "tag_profit_pos"

# r25 (bought on 09-25, 318 shares sold)
r25['Sold'] = False
r25['W'] = None
r25['X'] = None
r25['SellQty'] = 318
r25['Profit'] = 1544.86
r25['Hold'] = 318  # 09-22 (159) + 09-25 (159)
r25['Cash'] = 194674.49
r25['Asset'] = round(194674.49 + 318 * 151.45, 2)
r25['StatusText'] = "🟢 매수(159주) / 🔴 익절(318주, +$1,545)"
r25['Tag'] = "tag_profit_pos"

acc['current_holdings'] = 318
acc['current_cash'] = 194674.49
acc['total_asset'] = r25['Asset']

details = mgr.compute_account_details(acc)
print("Updated Details:")
print("Current Holdings:", details.get('current_holdings'))
print("Current Cash:", details.get('current_cash'))
print("Total Asset:", details.get('total_asset'))
print("Unsold lots count:", len([r for r in acc['trade_records'] if r.get('R', 0) > 0 and not r.get('Sold', False)]))
for r in [r for r in acc['trade_records'] if r.get('R', 0) > 0 and not r.get('Sold', False)]:
    print("  Holding Lot:", r['Date'], "Qty:", r['R'], "BuyPrice:", r['BuyPrice'], "U:", r['U'], "Sold:", r['Sold'])

print("\nSell Orders generated for tomorrow (Next Day):")
for s in details.get('sell_orders', []):
    print(" ", s)
