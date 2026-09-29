import sys, os
sys.path.insert(0, os.path.abspath('.'))
sys.stdout.reconfigure(encoding='utf-8')

from gui.account_manager import AccountManager
from core.data import fetch_market_data

mgr = AccountManager()
acc = mgr.load_accounts()[0]
df_market = fetch_market_data(acc['ticker'], '2025-01-01', '2026-09-25')
details = mgr.compute_account_details(acc, df_market)

df_res = details['df_res']
print('\nTree log view rows:')
for idx, r in df_res.iloc[-5:].iterrows():
    d_str = r['Date'].strftime('%Y-%m-%d')
    c_str = f"${r['Close']:.2f}"
    m_str = r.get('Mode', 'Normal')
    status_str = r.get('StatusText', '-')
    b_str = f"{int(r.get('R', 0)):,}주" if int(r.get('R', 0)) > 0 else '-'
    p_val = float(r.get('Profit', 0.0))
    p_str = f"+${p_val:,.2f}" if p_val > 0.01 else (f"-${abs(p_val):,.2f}" if p_val < -0.01 else '-')
    hold_str = f"{int(r.get('Hold', 0)):,}주"
    cash_str = f"${float(r.get('Cash', 0.0)):,.0f}"
    asset_str = f"${float(r.get('Asset', 0.0)):,.0f}"
    print(f"{d_str} | {c_str} | {m_str} | {status_str} | 매수: {b_str} | 손익: {p_str} | 보유: {hold_str} | 현금: {cash_str} | 총자산: {asset_str}")
