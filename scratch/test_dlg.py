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
details = mgr.compute_account_details(acc)

today_orders = {
    'sell_orders': details.get('sell_orders', []),
    'buy_orders': details.get('buy_orders', []),
    'last_price': details.get('current_price', 0.0),
    'mode': details.get('mode', 'Normal'),
    'netting_info': details.get('netting_info', {})
}

dlg = RecordCloseDialog(root, account=acc, today_orders=today_orders, on_success_callback=lambda *args: None)
dlg.close_var.set("151.95")
dlg._on_close_price_changed()

print("Analysis Sell Text:", dlg.lbl_analysis_sell.cget("text"))
print("Analysis Buy Text:", dlg.lbl_analysis_buy.cget("text"))
print("Buy Qty Entry:", dlg.entry_buy_qty.get())
print("Buy Price Entry:", dlg.entry_buy_price.get())
print("Sell Qty Entry:", dlg.entry_sell_qty.get())
print("Sell Price Entry:", dlg.entry_sell_price.get())

assert dlg.entry_buy_qty.get() == "159", f"Expected 159, got {dlg.entry_buy_qty.get()}"
assert "159" in dlg.lbl_analysis_buy.cget("text")
print("ALL TESTS PASSED!")
dlg.destroy()
root.destroy()
