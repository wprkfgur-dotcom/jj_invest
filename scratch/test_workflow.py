import sys, os
sys.path.insert(0, os.path.abspath('.'))
sys.stdout.reconfigure(encoding='utf-8')

from gui.account_manager import AccountManager

mgr = AccountManager()
acc = mgr.load_accounts()[0]
acc_id = acc['id']

print("=== 1. BEFORE Next Day ===")
print("Current date:", acc.get('current_date'))
print("Op state:", acc.get('operational_state'))
print("Hold:", acc['trade_records'][-1]['Hold'])

print("\n=== 2. Click [Next Day] ===")
acc = mgr.advance_next_day(acc_id)
print("Current date after Next Day:", acc.get('current_date'))
print("Op state after Next Day:", acc.get('operational_state'))

details = mgr.compute_account_details(acc)
print("Display status:", details['display_status'])
print("Target order date:", details['target_order_date'])

print("\n=== 3. Simulate End of Day (5:00 AM KST) Close Entry ===")
# Suppose close on 09-28 was 152.00, so 09-22 lot didn't reach 156.13, 09-25 lot didn't reach 155.62,
# but buy 155.61 filled for 168 shares!
acc = mgr.record_daily_close(
    acc_id=acc_id,
    close_price=152.00,
    buy_qty=168,
    buy_price=152.00,
    sell_qty=0,
    sell_price=152.00,
    memo="테스트 정상 체결"
)
print("Current date after record close:", acc.get('current_date'))
print("Op state after record close:", acc.get('operational_state'))
last_rec = acc['trade_records'][-1]
print("New record date:", last_rec['Date'])
print("New record close:", last_rec['Close'])
print("New record hold:", last_rec['Hold'])
print("New record cash:", last_rec['Cash'])

print("\n=== 4. Test Undo / Delete Last Day ===")
ok = mgr.delete_last_day_record(acc_id)
print("Undo successful:", ok)
acc = mgr.load_accounts()[0]
print("Current date after Undo:", acc.get('current_date'))
print("Op state after Undo:", acc.get('operational_state'))
print("Last record date after Undo:", acc['trade_records'][-1]['Date'])
print("Last record hold after Undo:", acc['trade_records'][-1]['Hold'])
