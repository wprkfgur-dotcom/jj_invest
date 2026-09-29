import sys, os
sys.path.insert(0, os.path.abspath('.'))
sys.stdout.reconfigure(encoding='utf-8')

# Mock test for _on_close_price_changed with 09.22 orders
today_orders = {
    'sell_orders': [],
    'buy_orders': [
        {'호가단계': '1차 분할매수', '주문유형': 'LOC 매수', '주문단가': '$160.09', '주문수량': '159주', 'price': 160.087, 'qty': 159},
        {'호가단계': '2차 분할매수', '주문유형': 'LOC 매수', '주문단가': '$146.12', '주문수량': '15주', 'price': 146.12, 'qty': 15},
        {'호가단계': '3차 분할매수', '주문유형': 'LOC 매수', '주문단가': '$123.76', '주문수량': '32주', 'price': 123.76, 'qty': 32},
        {'호가단계': '4차 매수 (폭락 대비 -17.0%)', '주문유형': 'LOC 매수', '주문단가': '$117.80', '주문수량': '216주', 'price': 117.8, 'qty': 216}
    ],
    'netting_info': {'is_netted': False}
}

account = {
    'trade_records': [
        {'Date': '2026-09-21', 'Close': 141.93, 'R': 0, 'Sold': False, 'U': None}
    ]
}

close_p = 151.95

sell_orders = today_orders.get('sell_orders', [])
buy_orders = today_orders.get('buy_orders', [])

records = account.get('trade_records', [])
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
    filled_sells.append(f"{lot.get('Date', '')} 로트({q}주@목표${u_p:.2f})")

for s in sell_orders:
    p = float(s.get('price', 0.0))
    q = int(s.get('qty', 0))
    if p > 0 and q > 0 and close_p >= p - 1e-4:
        s_name = str(s.get('구분', '매도'))
        if not any(str(lot.get('Date', '')) in s_name for lot in target_reached_lots):
            total_unsold_shares = sum(int(l['R']) for l in unsold_lots)
            if auto_sell_qty + q <= total_unsold_shares:
                auto_sell_qty += q
                filled_sells.append(f"{s_name}({q}주@${p:.2f})")

auto_buy_qty = 0
filled_buys = []
for b in buy_orders:
    p = float(b.get('price', 0.0))
    q = int(b.get('qty', 0))
    if p > 0 and q > 0:
        if close_p <= p + 1e-4:
            auto_buy_qty += q
            filled_buys.append(f"{b.get('호가단계', '매수')}({q}주@${p:.2f})")

print(f"Close Price: {close_p}")
print(f"Sell Analysis: auto_sell_qty = {auto_sell_qty}, filled_sells = {filled_sells}")
print(f"Buy Analysis: auto_buy_qty = {auto_buy_qty}, filled_buys = {filled_buys}")
