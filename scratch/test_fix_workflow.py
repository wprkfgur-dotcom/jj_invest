import sys, os
sys.path.insert(0, os.path.abspath('.'))
sys.stdout.reconfigure(encoding='utf-8')

from gui.account_manager import AccountManager

mgr = AccountManager()
acc = mgr.load_accounts()[0]
acc_id = acc['id']

print("=== 1. Current State in accounts.json ===")
print("Current date:", acc.get('current_date'))
for r in acc['trade_records'][-4:]:
    print(f"  {r['Date']} | R: {r['R']} | Sold: {r['Sold']} | Profit: {r['Profit']} | Status: {r.get('StatusText')}")

print("\n=== 2. Call Undo (delete_last_day_record) ===")
ok = mgr.delete_last_day_record(acc_id)
print("Undo ok:", ok)
acc = mgr.load_accounts()[0]
print("Current date after undo:", acc.get('current_date'))
for r in acc['trade_records'][-4:]:
    print(f"  {r['Date']} | R: {r['R']} | Sold: {r['Sold']} | Profit: {r['Profit']} | Status: {r.get('StatusText')}")

print("\n=== 3. Advance to 2026-09-25 (Next Day) ===")
acc = mgr.advance_next_day(acc_id)
print("Current date after next day:", acc.get('current_date'))
print("Op state:", acc.get('operational_state'))

print("\n=== 4. Record Close on 2026-09-25 with close=151.45, buy_q=159, sell_q=318 ===")
acc = mgr.record_daily_close(
    acc_id=acc_id,
    close_price=151.45,
    buy_qty=159,
    buy_price=151.45,
    sell_qty=318,
    sell_price=151.45,
    memo="09.25 정상 익절 및 신규 매수"
)

print("\n=== 5. Final State in accounts.json ===")
for r in acc['trade_records'][-5:]:
    print(f"  {r['Date']} | R: {r['R']} | Sold: {r['Sold']} | W: {r.get('W')} | Profit: ${r['Profit']:.2f} | Status: {r.get('StatusText')}")
