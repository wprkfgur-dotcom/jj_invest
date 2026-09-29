import sys
sys.path.insert(0, '.')
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
import os
from gui.account_manager import AccountManager

mgr = AccountManager()
accounts = mgr.load_accounts()
original_acc = accounts[0]

# 1. Export CSV
export_path = 'scratch/test_soxl_export.csv'
ok = mgr.export_trade_records_csv(original_acc['id'], export_path)
assert ok, "Export failed"
print("1. Exported CSV successfully to", export_path)

# 2. Parse CSV
parsed = mgr.parse_trade_records_csv(export_path)
print("2. Parsed CSV:")
print(f"   Name: {parsed['account_name']}")
print(f"   Ticker: {parsed['ticker']}")
print(f"   Strategy: {parsed['strategy']}")
print(f"   Records: {parsed['record_count']}")
print(f"   Period: {parsed['start_date']} ~ {parsed['current_date']}")
print(f"   Final Hold: {parsed['current_hold']} shares")
print(f"   Final Cash: ${parsed['current_cash']:,.2f}")
print(f"   Final Asset: ${parsed['total_asset']:,.2f}")

assert parsed['record_count'] == 184
assert parsed['current_hold'] == 318

# 3. Create New Account from CSV data
new_acc = mgr.add_account(
    name="SOXL CSV 복원 2호",
    strategy=parsed['strategy'],
    ticker=parsed['ticker'],
    start_date=parsed['start_date'],
    initial_seed=parsed['initial_seed'],
    memo="CSV에서 불러온 복원 계좌",
    trade_records=parsed['trade_records'],
    current_date=parsed['current_date']
)
print("3. Created new account:", new_acc['id'], new_acc['name'])

# 4. Compute details for new account
details = mgr.compute_account_details(new_acc)
print("4. New Account Computed Details:")
print(f"   Current date: {details['current_date']}")
print(f"   Current Hold: {details['current_hold']} shares")
print(f"   Current Cash: ${details['current_cash']:,.2f}")
print(f"   Current Asset: ${details['current_asset']:,.2f}")
print(f"   Pending sell slots: {details['pending_sell_count']}")
print(f"   Sell orders count: {len(details['sell_orders'])}")
print(f"   Buy orders count: {len(details['buy_orders'])}")

assert details['current_hold'] == 318
assert details['pending_sell_count'] == 2
assert len(details['sell_orders']) == 2

# Clean up: delete test account so accounts.json remains tidy
mgr.delete_account(new_acc['id'])
print("5. Test account cleaned up.")
print("\nALL INTEGRATION TESTS PASSED 100%!")
