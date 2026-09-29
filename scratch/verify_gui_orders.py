import sys, os
sys.path.insert(0, os.path.abspath('.'))
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
from core.data import fetch_market_data
from gui.account_manager import AccountManager

df_soxl = fetch_market_data('SOXL', '2018-01-01', '2026-09-25')
am = AccountManager()
accs = am.load_accounts()
print(f"Total Accounts: {len(accs)}")

for acc in accs:
    res = am.compute_account_details(acc, df_soxl)
    print(f"\n==========================================")
    print(f"Account: {res['account_name']} ({res['ticker']})")
    print(f"Mode: {res['mode']} | Hold: {res['current_hold']}주 | Cash: ${res['current_cash']:,.2f}")
    
    info = res['netting_info']
    print(f"\n[퉁치기 분석]")
    print(f"• 상계 적용 여부: {info['is_netted']}")
    print(f"• 최대 상계(자전거래 방지) 수량: {info['max_offset_qty']}주")
    print(f"• 중복 호가 체결 구간: ${info['overlap_price_min']} ~ ${info['overlap_price_max']}")
    print(f"• 요약문: {info['summary_text']}")

    print(f"\n[🔴 오늘의 순 매도 주문 (Net Sells - {len(res['sell_orders'])}건)]")
    for s in res['sell_orders']:
        print(f"  {s['구분']:<18} | {s['주문유형']:<10} | {s['주문단가']:<8} | {s['주문수량']:<6} (누적 {s['누적수량']}) | {s['예상금액']:<12} | {s['체결조건']:<16} | {s['비고']}")

    print(f"\n[🟢 오늘의 순 매수 주문 (Net Buys - {len(res['buy_orders'])}건)]")
    for b in res['buy_orders']:
        print(f"  {b['호가단계']:<18} | {b['주문유형']:<10} | {b['주문단가']:<8} | {b['주문수량']:<6} (누적 {b['누적수량']}) | {b['예상금액']:<12} | {b['체결조건']:<16} | {b['비고']}")

    print(f"\n[상계 전 원본 매도 주문 (Raw Sells - {len(info['raw_sell_orders'])}건)]")
    for rs in info['raw_sell_orders']:
        print(f"  {rs['stage']:<15} | 단가: ${rs['price']:.2f} | 수량: {rs['qty']}주")

    print(f"\n[상계 전 원본 매수 주문 (Raw Buys - {len(info['raw_buy_orders'])}건)]")
    for rb in info['raw_buy_orders']:
        print(f"  {rb['stage']:<15} | 단가: ${rb['price']:.2f} | 수량: {rb['qty']}주")
