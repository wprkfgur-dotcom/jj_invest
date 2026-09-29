import sys
sys.path.insert(0, '.')
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import tkinter as tk
from gui.account_manager import AccountManager
from gui.dialogs.trade_entry_dialog import RecordCloseDialog

root = tk.Tk()
root.withdraw()

mgr = AccountManager()
accounts = mgr.load_accounts()
acc = accounts[0]

# Simulate 9/25 state: records up to 9/24, where 9/22, 9/23, 9/24 are unsold
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

today_orders = {
    'sell_orders': details.get('sell_orders', []),
    'buy_orders': details.get('buy_orders', []),
    'last_price': details.get('current_price', 0.0),
    'mode': details.get('mode', 'Normal'),
    'netting_info': details.get('netting_info', {})
}

dlg = RecordCloseDialog(root, account=acc_copy, today_orders=today_orders, on_success_callback=lambda *args: None)
dlg.close_var.set("151.45")
dlg._on_close_price_changed()

print("Analysis Sell Text:", dlg.lbl_analysis_sell.cget("text"))
print("Analysis Buy Text:", dlg.lbl_analysis_buy.cget("text"))
print("Sell Qty Entry:", dlg.entry_sell_qty.get())
print("Buy Qty Entry:", dlg.entry_buy_qty.get())

assert dlg.entry_sell_qty.get() == "318", f"Expected 318, got {dlg.entry_sell_qty.get()}"
assert "2026-09-23" in dlg.lbl_analysis_sell.cget("text")
assert "2026-09-24" in dlg.lbl_analysis_sell.cget("text")
assert "2026-09-22" not in dlg.lbl_analysis_sell.cget("text")
print("SUCCESS: 9/22 slot is strictly protected and only 9/23 and 9/24 (318 shares) are sold!")

dlg.destroy()
root.destroy()
