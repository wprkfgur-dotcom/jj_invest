def calculate_netted_orders(raw_buy_orders, raw_sell_orders):
    """
    매수 주문 목록과 매도 주문 목록의 겹치는 구간을 계산하여 
    자전거래(스스로 매수/매도 동시 체결)를 상계(퉁치기)한 순주문(Net Orders)을 산출합니다.
    """
    # 1. 모든 관련 가격 및 경계점 (p - 0.01, p + 0.01) 수집
    key_prices = set()
    for b in raw_buy_orders:
        p = round(float(b['price']), 2)
        key_prices.add(p)
        key_prices.add(round(p - 0.01, 2))
        key_prices.add(round(p + 0.01, 2))
    for s in raw_sell_orders:
        p = round(float(s['price']), 2)
        key_prices.add(p)
        key_prices.add(round(p - 0.01, 2))
        key_prices.add(round(p + 0.01, 2))
    
    sorted_prices = sorted(p for p in key_prices if p > 0)
    if not sorted_prices:
        return {'net_buy_orders': [], 'net_sell_orders': [], 'max_offset_qty': 0}

    def gross_buy(p):
        return sum(b['qty'] for b in raw_buy_orders if p <= b['price'] + 1e-4)
    
    def gross_sell(p):
        return sum(s['qty'] for s in raw_sell_orders if p >= s['price'] - 1e-4)

    # 각 가격점별 gross_buy, gross_sell, net(=buy - sell), offset(=min(buy, sell))
    price_stats = []
    max_offset = 0
    for p in sorted_prices:
        gb = gross_buy(p)
        gs = gross_sell(p)
        off = min(gb, gs)
        if off > max_offset:
            max_offset = off
        price_stats.append({
            'price': p,
            'gross_buy': gb,
            'gross_sell': gs,
            'net': gb - gs,
            'offset': off
        })

    # 순 매도 주문 도출:
    # NetSell(p) = gross_sell(p) - gross_buy(p)
    # p가 오를수록 NetSell은 증가.
    # LOC 매도는 "종가 >= P" 체결이므로, P에서 NetSell이 증가하는 첫 지점에 주문을 배치.
    net_sell_orders = []
    prev_net_sell = 0
    for stat in price_stats:
        p = stat['price']
        ns = max(0, -stat['net'])
        if ns > prev_net_sell:
            order_q = ns - prev_net_sell
            net_sell_orders.append({
                'price': p,
                'qty': order_q,
                'type': 'LOC 매도',
                'condition': f"종가 ≥ ${p:.2f}"
            })
            prev_net_sell = ns

    # 순 매수 주문 도출:
    # NetBuy(p) = gross_buy(p) - gross_sell(p)
    # p가 내릴수록 NetBuy는 증가.
    # LOC 매수는 "종가 <= P" 체결이므로, P에서 NetBuy가 증가하는 첫 지점(높은 가격)에 주문을 배치.
    net_buy_orders = []
    prev_net_buy = 0
    for stat in reversed(price_stats):
        p = stat['price']
        nb = max(0, stat['net'])
        if nb > prev_net_buy:
            order_q = nb - prev_net_buy
            net_buy_orders.append({
                'price': p,
                'qty': order_q,
                'type': 'LOC 매수',
                'condition': f"종가 ≤ ${p:.2f}"
            })
            prev_net_buy = nb

    return {
        'net_buy_orders': net_buy_orders,
        'net_sell_orders': net_sell_orders,
        'max_offset_qty': max_offset
    }

# Test with user screenshot
raw_s = [{'price': 155.62, 'qty': 338, 'type': 'LOC 매도'}]
raw_b = [
    {'price': 170.83, 'qty': 39, 'type': 'LOC 매수'},
    {'price': 170.82, 'qty': 39, 'type': 'LOC 매수'},
    {'price': 155.92, 'qty': 39, 'type': 'LOC 매수'},
    {'price': 132.06, 'qty': 39, 'type': 'LOC 매수'},
]

res = calculate_netted_orders(raw_b, raw_s)
print("Max Offset Qty (퉁친 수량):", res['max_offset_qty'])
print("\n--- NET SELL ORDERS ---")
for o in res['net_sell_orders']:
    print(f"LOC 매도 ${o['price']:.2f}: {o['qty']}주")
print("\n--- NET BUY ORDERS ---")
for o in res['net_buy_orders']:
    print(f"LOC 매수 ${o['price']:.2f}: {o['qty']}주")
