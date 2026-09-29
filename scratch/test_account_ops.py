import sys
sys.path.insert(0, '.')
import json
import pandas as pd
from core.market_calendar import get_next_trading_day, parse_date
from gui.account_manager import AccountManager
from core.data import fetch_market_data

mgr = AccountManager()
accs = mgr.load_accounts()
acc = accs[0]

# 1. Initialize trade_records if empty
df = fetch_market_data(acc['ticker'], acc['start_date'], '2026-09-25')
details = mgr.compute_account_details(acc, df)
accs = mgr.load_accounts()
acc = accs[0]
print("After compute_account_details, trade_records count:", len(acc.get('trade_records', [])))
print("Current Date:", acc.get('current_date'))
print("Operational State:", acc.get('operational_state'))

# 2. Test advance_next_day
acc_after_next = mgr.advance_next_day(acc['id'])
print("\nAfter advance_next_day:")
print("New Current Date:", acc_after_next.get('current_date'))
print("New State:", acc_after_next.get('operational_state'))
assert acc_after_next.get('current_date') == '2026-09-28'

# 3. Test record_daily_close (simulate 09.28 close: 151.45, buy 168 shares)
res_close = mgr.record_daily_close(
    acc_id=acc['id'],
    close_price=151.45,
    buy_qty=168,
    buy_price=151.45,
    sell_qty=0,
    sell_price=0.0,
    memo="09.28 1차 LOC 순매수 체결 테스트"
)
print("\nAfter record_daily_close:")
print("Total records now:", len(res_close.get('trade_records', [])))
last_rec = res_close['trade_records'][-1]
print("Last record Date:", last_rec['Date'], "Hold:", last_rec['Hold'], "Cash:", last_rec['Cash'], "Asset:", last_rec['Asset'])
assert last_rec['Hold'] == 336 + 168
assert last_rec['Date'] == '2026-09-28'

# 4. Test delete_last_day_record (Undo)
undone = mgr.delete_last_day_record(acc['id'])
print("\nAfter delete_last_day_record (Undo):", undone)
accs = mgr.load_accounts()
acc = accs[0]
print("Records count after undo:", len(acc['trade_records']))
print("Restored Date:", acc.get('current_date'))
assert acc['trade_records'][-1]['Date'] == '2026-09-25'
assert acc['current_date'] == '2026-09-25'
assert acc['trade_records'][-1]['Hold'] == 336
print("\nALL OPERATIONS TESTED AND PASSED PERFECTLY!")
