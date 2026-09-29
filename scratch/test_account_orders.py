import sys, json, os
sys.path.insert(0, os.path.abspath('.'))
import pandas as pd
from gui.account_manager import AccountManager

sys.stdout.reconfigure(encoding='utf-8')

# First update accounts.json with the corrected hold/asset
with open('data/accounts.json', 'r', encoding='utf-8') as f:
    accounts = json.load(f)

records = accounts[0]['trade_records']
for i, r in enumerate(records):
    d_i = str(r['Date'])[:10]
    active_lots = [
        lot for lot in records[:i+1] 
        if lot.get('R', 0) > 0 and (
            not lot.get('Sold', False) or 
            (lot.get('W') is not None and str(lot.get('W'))[:10] > d_i)
        )
    ]
    true_hold = sum(int(lot.get('R', 0)) for lot in active_lots)
    r['Hold'] = true_hold
    r['Asset'] = round(float(r['Cash']) + float(r['Close']) * true_hold, 2)

accounts[0]['trade_records'] = records
accounts[0]['current_date'] = '2026-09-25'
accounts[0]['operational_state'] = 'DAY_COMPLETED'

with open('data/accounts.json', 'w', encoding='utf-8') as f:
    json.dump(accounts, f, indent=2, ensure_ascii=False)

print("Saved corrected accounts.json successfully.")

# Now test compute_account_details
mgr = AccountManager()
acc = mgr.load_accounts()[0]
details = mgr.compute_account_details(acc)

print(f"\nAccount: {details['account_name']}")
print(f"Current Date: {details['current_date']}")
print(f"Target Order Date: {details['target_order_date']}")
print(f"Operational State: {details['operational_state']}")
print(f"Display Status: {details['display_status']}")
print(f"Hold Shares: {details['current_hold']} shares")
print(f"Pending Sell Count: {details['pending_sell_count']} lots")
print(f"Cash: ${details['current_cash']:,.2f}")
print(f"Asset: ${details['current_asset']:,.2f}")

print("\n--- Sell Orders (매도 주문) ---")
for s in details['sell_orders']:
    print(f"  {s}")

print("\n--- Buy Orders (매수 주문) ---")
for b in details['buy_orders']:
    print(f"  {b}")
