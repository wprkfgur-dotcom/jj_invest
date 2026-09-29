import math

def excel_round(val, digits=0):
    if val is None:
        return None
    factor = 10 ** digits
    res = math.copysign(math.floor(abs(val) * factor + 0.5), val)
    return res / factor if digits > 0 else int(res)

def round_down(val, digits=2):
    factor = 10 ** digits
    return math.floor(val * factor + 1e-12) / factor

def round_up(val, digits=2):
    factor = 10 ** digits
    return math.ceil(val * factor - 1e-9) / factor

def safe_round4(val):
    return round(val * 10000.0) / 10000.0

# User inputs from Excel log
yest_close = 151.45
p_budget = 27313.29
AU1 = p_budget
AU2 = yest_close
C2 = 0.128      # 12.8%
C3 = -0.17      # -17.0%

# Unsold lots in user account
# Lot 1: 09.22 purchase, R=186, U=156.13
# Lot 2: 09.25 purchase, R=174, U=155.62
unsold_lots = [
    {'date': '09.22', 'R': 186, 'U': 156.13, 'hold_days': 3},
    {'date': '09.25', 'R': 174, 'U': 155.62, 'hold_days': 1}
]

# 1. BB3 = Upper bound (+12.8%)
BB3 = round_down(AU2 * (1.0 + C2), 2)  # 170.83

# 2. Identify the lowest target lot (AU3, AV3) for 퉁치기
eligible_lots = [lot for lot in unsold_lots if lot['U'] <= BB3 and lot['hold_days'] < 10]
eligible_lots.sort(key=lambda x: x['U'])

sell_orders = []
buy_orders = []

if eligible_lots:
    tung_lot = eligible_lots[0]
    AU3 = tung_lot['U']   # 155.62
    AV3 = tung_lot['R']   # 174
    
    # 퉁치기 로트는 맥스 12.8% 상승 시 전량 매도되도록 BB3에 주문
    sell_orders.append({
        '구분': '맥스 익절 매도 (퉁치기 로트)',
        '주문유형': 'LOC 매도',
        '주문단가': BB3,
        '주문수량': AV3,
        'pct': C2 * 100.0
    })
    
    # 나머지 로트들은 각자의 목표가(U)에 매도 주문
    for lot in unsold_lots:
        if lot is not tung_lot:
            pct = (lot['U'] / AU2 - 1.0) * 100.0
            lot_d = lot['date']
            sell_orders.append({
                '구분': f'목표 익절 매도 ({lot_d} 로트)',
                '주문유형': 'LOC 매도',
                '주문단가': lot['U'],
                '주문수량': lot['R'],
                'pct': pct
            })
            
    # 매수 주문 1차: 퉁치기 로트 바로 아래 가격(AU3 - 0.01)에서 AV3만큼 매수
    AY2 = safe_round4(AU3 - 0.01)  # 155.61
    buy_orders.append({
        '호가단계': '1차 매수 (상계 순매수)',
        '주문유형': 'LOC 매수',
        '주문단가': AY2,
        '주문수량': AV3,
        'pct': (AY2 / AU2 - 1.0) * 100.0
    })
    
    # 매수 주문 2차: 하단 매수가 AY3 (-12.8%)
    AY3 = safe_round4(AU2 * (1.0 - C2))  # 132.0644 -> 132.06
    # 수량: int(AU1 / AY3) - AV3
    total_q_at_ay3 = int(AU1 / AY3)      # int(27313.29 / 132.0644) = 205
    q2 = max(0, total_q_at_ay3 - AV3)    # 205 - 174 = 31
    buy_orders.append({
        '호가단계': '2차 매수 (-12.8% 하단)',
        '주문유형': 'LOC 매수',
        '주문단가': round(AY3, 2),
        '주문수량': q2,
        'pct': -C2 * 100.0
    })
    
    # 매수 주문 3차: 폭락장 대비 매수 BE4 (-17.0%)
    BE4 = safe_round4(AU2 * (1.0 + C3))  # 125.7035 -> 125.70
    BF4 = excel_round(AU1 / BE4, 0)      # 217
    buy_orders.append({
        '호가단계': '3차 매수 (-17% 폭락 대비)',
        '주문유형': 'LOC 매수',
        '주문단가': round(BE4, 2),
        '주문수량': BF4,
        'pct': C3 * 100.0
    })

print("=== CALCULATED SELL ORDERS ===")
for s in sell_orders:
    print(f"매도 {s['주문단가']:>7.2f} {s['주문수량']:>5}주 {s['pct']:>5.1f}% | {s['구분']}")

print("\n=== CALCULATED BUY ORDERS ===")
for b in buy_orders:
    print(f"매수 {b['주문단가']:>7.2f} {b['주문수량']:>5}주 {b['pct']:>5.1f}% | {b['호가단계']}")
