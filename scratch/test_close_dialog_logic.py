import sys
sys.stdout.reconfigure(encoding='utf-8')

# Mock account with 3 unsold lots on 09.25:
records = [
    {'Date': '2026-09-22', 'R': 159, 'Close': 151.95, 'S': 24184.20, 'U': 156.13, 'Sold': False, 'Profit': 0.0},
    {'Date': '2026-09-23', 'R': 159, 'Close': 146.25, 'S': 23277.72, 'U': 150.28, 'Sold': False, 'Profit': 0.0},
    {'Date': '2026-09-24', 'R': 159, 'Close': 146.33, 'S': 23290.46, 'U': 150.36, 'Sold': False, 'Profit': 0.0}
]

close_p = 151.45

# Netting orders generated for 09.25:
sell_orders = [
    {'구분': '맥스 익절 매도 (퉁치기 로트)', 'price': 165.06, 'qty': 159},
    {'구분': '목표 익절 매도 (09.22 로트)', 'price': 156.13, 'qty': 159},
    {'구분': '목표 익절 매도 (09.24 로트)', 'price': 150.36, 'qty': 159}
]

buy_orders = [
    {'호가단계': '1차 순매수 (퉁치기 상계)', 'price': 150.27, 'qty': 159},
    {'호가단계': '2차 순매수 (-12.8% 하단)', 'price': 127.59, 'qty': 29},
    {'호가단계': '3차 순매수 (-17.0% 폭락 대비)', 'price': 121.45, 'qty': 206}
]

unsold_lots = [r for r in records if r.get('R', 0) > 0 and not r.get('Sold', False)]

target_reached_lots = []
for lot in unsold_lots:
    u_p = float(lot.get('U', 0.0)) if lot.get('U') is not None else 0.0
    if u_p > 0 and close_p >= u_p - 1e-4:
        target_reached_lots.append(lot)

auto_sell_qty = 0
filled_sells = []
for lot in target_reached_lots:
    q = int(lot['R'])
    u_p = float(lot['U'])
    auto_sell_qty += q
    filled_sells.append(f"{lot.get('Date', '')}분 익절({q}주@목표${u_p:.2f})")

auto_buy_qty = 0
filled_buys = []
for b in buy_orders:
    p = float(b.get('price', 0.0))
    q = int(b.get('qty', 0))
    if p > 0 and q > 0 and close_p <= p + 1e-4:
        auto_buy_qty += q
        filled_buys.append(f"{b.get('호가단계', '매수')}({q}주@${p:.2f})")

if auto_buy_qty == 0 and target_reached_lots:
    min_u_lot = min(unsold_lots, key=lambda x: float(x.get('U', 999999.0)))
    if min_u_lot in target_reached_lots:
        tung_q = int(min_u_lot['R'])
        auto_buy_qty = tung_q
        filled_buys.append(f"퉁치기 상계 순매수({tung_q}주@${close_p:.2f})")

print("Close price:", close_p)
print(f"Auto sell qty: {auto_sell_qty}주")
print("Filled sells:", filled_sells)
print(f"Auto buy qty: {auto_buy_qty}주")
print("Filled buys:", filled_buys)
