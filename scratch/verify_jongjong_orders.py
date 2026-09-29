import math
from strategies.jongjong import safe_round4, round_down, round_up, excel_round

yest_close = 151.45
p_budget = 27313.29
C2 = 0.128
C3 = -0.17

unsold_lots = [
    {'date': '09.22', 'R': 186, 'U': 156.13, 'hold_days': 3},
    {'date': '09.25', 'R': 174, 'U': 155.62, 'hold_days': 1}
]

# BB3
BB3 = round_down(yest_close * (1.0 + C2), 2)
print('BB3:', BB3)

eligible = [l for l in unsold_lots if l['U'] <= BB3 and l['hold_days'] < 10]
eligible.sort(key=lambda x: x['U'])
tung_lot = eligible[0]
print('Tung lot:', tung_lot)

sells = []
sells.append({'type': 'LOC 매도', 'price': BB3, 'qty': tung_lot['R'], 'pct': C2*100, 'label': '맥스 익절 매도 (퉁치기 로트)'})
for l in unsold_lots:
    if l is not tung_lot:
        pct = (l['U'] / yest_close - 1.0) * 100
        d_str = l['date']
        sells.append({'type': 'LOC 매도', 'price': l['U'], 'qty': l['R'], 'pct': pct, 'label': f'목표 익절 매도 ({d_str})'})

buys = []
AY2 = safe_round4(tung_lot['U'] - 0.01)
buys.append({'type': 'LOC 매수', 'price': AY2, 'qty': tung_lot['R'], 'pct': (AY2/yest_close-1)*100, 'label': '1차 순매수 (퉁치기 상계)'})

AY3_raw = yest_close * (1.0 - C2)
AY3 = round_down(AY3_raw, 2)
total_q = int(p_budget / AY3_raw)
q2 = max(0, total_q - tung_lot['R'])
buys.append({'type': 'LOC 매수', 'price': AY3, 'qty': q2, 'pct': -C2*100, 'label': '2차 순매수 (-12.8% 하단)'})

BE4_raw = yest_close * (1.0 + C3)
BE4 = round_down(BE4_raw, 2)
BF4 = excel_round(p_budget / BE4_raw, 0)
buys.append({'type': 'LOC 매수', 'price': BE4, 'qty': BF4, 'pct': C3*100, 'label': '3차 순매수 (-17% 폭락 대비)'})

print('=== SELLS ===')
for s in sells:
    print(f"매도 {s['price']:>7.2f} {s['qty']:>4}주 {s['pct']:>5.1f}% | {s['label']}")
print('=== BUYS ===')
for b in buys:
    print(f"매수 {b['price']:>7.2f} {b['qty']:>4}주 {b['pct']:>5.1f}% | {b['label']}")
