import math
from typing import List, Dict, Any
from strategies.jongjong import safe_round4, round_down, round_up, excel_round

def generate_jongjong_orders(
    unsold_lots: List[Dict[str, Any]],
    yest_close: float,
    p_budget: float,
    mode: str = 'Normal',
    C2: float = 0.128,
    C3: float = -0.17,
    C4: int = 6,
    C6: float = 1.0,
    target_yield: float = 0.0275
) -> Dict[str, Any]:
    """
    종종이 실매매 주문표 생성 엔진 (퉁치기 및 슬롯 기반 1:1 매도 완벽 구현)
    - 매도는 부분 매도나 분할 슬라이싱 없이 미매도 슬롯당 최대 1개 주문 (최대 미매도 슬롯 수와 동일)
    - 퉁치기 슬롯: BB3 이하 목표가를 가진 슬롯 중 최저 목표가 슬롯(AU3, AV3)
      -> 맥스 +12.8%(BB3)에 전량 매도 주문 (12.8% 급등 시 퉁치기 없이 전량 청산)
    - 나머지 미매도 슬롯: 각자의 고유 목표가(U)에 매도 주문
    - 순 매수 주문:
      1차 매수: AU3 - 0.01 (AV3주 상계 순매수)
      2차 매수: yest_close * (1 - C2) (하단 잔여 순매수)
      3차 매수: yest_close * (1 + C3) (폭락 대비 매수)
    """
    AU1 = max(0.0, float(p_budget))
    AU2 = float(yest_close)
    is_normal = (mode == 'Normal')
    is_riskoff = (mode == 'Riskoff')

    moc_lots = [l for l in unsold_lots if l.get('hold_days', 0) >= 10]
    loc_lots = [l for l in unsold_lots if l.get('hold_days', 0) < 10]

    BB3 = round_down(AU2 * (1.0 + C2), 2)
    
    AU3, AV3, tung_lot = None, 0, None
    if loc_lots:
        min_u = min(l['U'] for l in loc_lots)
        if is_normal and BB3 >= min_u:
            AU3 = min_u
            for l in loc_lots:
                if l['U'] == min_u:
                    tung_lot = l
                    AV3 = l['R']
                    break

    # 1. 매도 주문 생성 (슬롯 단위 1:1 매도, 절대 쪼개지 않음)
    formatted_sells = []
    accum_s = 0

    # (1) MOC 만기 매도
    for l in moc_lots:
        q = l['R']
        accum_s += q
        formatted_sells.append({
            '구분': f"MOC 청산 ({l.get('date', '만기')} 10일)",
            '주문유형': 'MOC 매도',
            '주문단가': f"${AU2:.2f}",
            '주문수량': f"{q:,}주",
            '누적수량': f"{accum_s:,}주",
            '예상금액': f"${AU2 * q:,.2f}",
            '체결조건': "10영업일 보유 만기 종가 전량 청산",
            '비고': "MOC 종가 시장가 청산",
            'price': AU2,
            'qty': q
        })

    # (2) LOC 목표 매도
    if tung_lot is not None:
        # 퉁치기 대상 슬롯은 맥스 12.8%에 전량 매도 주문 (급등 시 청산)
        q = tung_lot['R']
        accum_s += q
        formatted_sells.append({
            '구분': '맥스 익절 매도 (퉁치기 로트)',
            '주문유형': 'LOC 매도',
            '주문단가': f"${BB3:.2f}",
            '주문수량': f"{q:,}주",
            '누적수량': f"{accum_s:,}주",
            '예상금액': f"${BB3 * q:,.2f}",
            '체결조건': f"종가 ≥ ${BB3:.2f} (+{C2*100:.1f}%)",
            '비고': "12.8% 상한 도달 시 전량 청산 (퉁치기 미발생)",
            'price': BB3,
            'qty': q
        })

        # 나머지 슬롯들은 원래 목표가(U)에 매도
        for l in loc_lots:
            if l is not tung_lot:
                q = l['R']
                accum_s += q
                pct = (l['U'] / AU2 - 1.0) * 100.0
                d_str = l.get('date', '')
                formatted_sells.append({
                    '구분': f"목표 익절 매도 ({d_str} 로트)",
                    '주문유형': 'LOC 매도',
                    '주문단가': f"${l['U']:.2f}",
                    '주문수량': f"{q:,}주",
                    '누적수량': f"{accum_s:,}주",
                    '예상금액': f"${l['U'] * q:,.2f}",
                    '체결조건': f"종가 ≥ ${l['U']:.2f} ({pct:+.1f}%)",
                    '비고': "개별 슬롯 목표가 도달 시 전량 매도",
                    'price': l['U'],
                    'qty': q
                })
    else:
        for l in loc_lots:
            q = l['R']
            accum_s += q
            pct = (l['U'] / AU2 - 1.0) * 100.0
            d_str = l.get('date', '')
            formatted_sells.append({
                '구분': f"목표 익절 매도 ({d_str} 로트)",
                '주문유형': 'LOC 매도',
                '주문단가': f"${l['U']:.2f}",
                '주문수량': f"{q:,}주",
                '누적수량': f"{accum_s:,}주",
                '예상금액': f"${l['U'] * q:,.2f}",
                '체결조건': f"종가 ≥ ${l['U']:.2f} ({pct:+.1f}%)",
                '비고': "개별 슬롯 목표가 도달 시 전량 매도",
                'price': l['U'],
                'qty': q
            })

    # 2. 매수 주문 생성
    formatted_buys = []
    accum_b = 0

    if AU1 > 0:
        if tung_lot is not None and is_normal:
            # 퉁치기 모드 매수
            # 1차 매수: AU3 - 0.01 (AV3주 상계 순매수)
            AY2 = safe_round4(AU3 - 0.01)
            pct1 = (AY2 / AU2 - 1.0) * 100.0
            accum_b += AV3
            formatted_buys.append({
                '호가단계': '1차 순매수 (퉁치기 상계)',
                '주문유형': 'LOC 매수',
                '주문단가': f"${AY2:.2f}",
                '주문수량': f"{AV3:,}주",
                '누적수량': f"{accum_b:,}주",
                '예상금액': f"${AY2 * AV3:,.2f}",
                '체결조건': f"종가 ≤ ${AY2:.2f} ({pct1:+.1f}%)",
                '비고': f"최저 목표가(${AU3:.2f}) 하단 상계 순매수",
                'price': AY2,
                'qty': AV3
            })

            # 2차 매수: 하단 밴드 (-12.8%)
            AY3_raw = AU2 * (1.0 - C2)
            AY3 = round_down(AY3_raw, 2)
            total_q = int(AU1 / AY3_raw)
            q2 = max(0, total_q - AV3)
            if q2 > 0:
                accum_b += q2
                formatted_buys.append({
                    '호가단계': '2차 순매수 (-12.8% 하단)',
                    '주문유형': 'LOC 매수',
                    '주문단가': f"${AY3:.2f}",
                    '주문수량': f"{q2:,}주",
                    '누적수량': f"{accum_b:,}주",
                    '예상금액': f"${AY3 * q2:,.2f}",
                    '체결조건': f"종가 ≤ ${AY3:.2f} (-{C2*100:.1f}%)",
                    '비고': f"하단 밴드 잔여 순매수 ({total_q}주 - {AV3}주 상계)",
                    'price': AY3,
                    'qty': q2
                })

            # 3차 매수: 폭락장 대비 (-17.0%)
            BE4_raw = AU2 * (1.0 + C3)
            BE4 = round_down(BE4_raw, 2)
            BF4 = excel_round(AU1 / BE4_raw, 0)
            if BF4 > 0:
                accum_b += BF4
                formatted_buys.append({
                    '호가단계': '3차 순매수 (-17.0% 폭락 대비)',
                    '주문유형': 'LOC 매수',
                    '주문단가': f"${BE4:.2f}",
                    '주문수량': f"{BF4:,}주",
                    '누적수량': f"{accum_b:,}주",
                    '예상금액': f"${BE4 * BF4:,.2f}",
                    '체결조건': f"종가 ≤ ${BE4:.2f} ({C3*100:.1f}%)",
                    '비고': "폭락장 대비 1회분 추가 LOC 매수",
                    'price': BE4,
                    'qty': BF4
                })
        else:
            # 퉁치기 없는 일반 분할 매수
            AY2 = safe_round4(AU2 * (1.0 + C2) - 0.01) if is_normal else safe_round4(AU2 - 0.01)
            AY3 = round_down(AU2 * (1.0 - C2), 2)
            grid_p = [AY2]
            n_steps = max(2, C4 - 1)
            for i in range(1, n_steps):
                p_step = round_down(AY2 - (AY2 - AY3) * (i / (n_steps - 1)), 2)
                if p_step not in grid_p:
                    grid_p.append(p_step)

            each_q = max(1, int((AU1 / len(grid_p)) / AU2))
            for idx, p in enumerate(grid_p):
                accum_b += each_q
                pct = (p / AU2 - 1.0) * 100.0
                formatted_buys.append({
                    '호가단계': f"{idx+1}차 분할매수",
                    '주문유형': 'LOC 매수',
                    '주문단가': f"${p:.2f}",
                    '주문수량': f"{each_q:,}주",
                    '누적수량': f"{accum_b:,}주",
                    '예상금액': f"${p * each_q:,.2f}",
                    '체결조건': f"종가 ≤ ${p:.2f} ({pct:+.1f}%)",
                    '비고': "일반 분할 LOC 매수",
                    'price': p,
                    'qty': each_q
                })

            # 폭락장 대비 매수
            BE4_raw = AU2 * (1.0 + C3)
            BE4 = round_down(BE4_raw, 2)
            BF4 = excel_round(AU1 / BE4_raw, 0)
            if BF4 > 0:
                accum_b += BF4
                formatted_buys.append({
                    '호가단계': '폭락 대비 매수 (-17.0%)',
                    '주문유형': 'LOC 매수',
                    '주문단가': f"${BE4:.2f}",
                    '주문수량': f"{BF4:,}주",
                    '누적수량': f"{accum_b:,}주",
                    '예상금액': f"${BE4 * BF4:,.2f}",
                    '체결조건': f"종가 ≤ ${BE4:.2f} ({C3*100:.1f}%)",
                    '비고': "폭락장 대비 1회분 추가 LOC 매수",
                    'price': BE4,
                    'qty': BF4
                })

    is_netted = (tung_lot is not None)
    max_offset_qty = AV3 if is_netted else 0
    if is_netted:
        summary_text = (
            f"⚡ [종종이 퉁치기 적용] 최저 목표가 슬롯({tung_lot.get('date', '')}, {AV3:,}주)을 당일 매수와 상계하여 "
            f"맥스 익절(+{C2*100:.1f}%) 매도 1개 및 순매수 3단계로 재구성했습니다 (총 매도 주문: {len(formatted_sells)}개)."
        )
    else:
        summary_text = f"미매도 슬롯({len(formatted_sells)}개)에 대한 개별 목표가 매도 주문이 유지됩니다."

    return {
        'sell_orders': formatted_sells,
        'buy_orders': formatted_buys,
        'is_netted': is_netted,
        'max_offset_qty': max_offset_qty,
        'overlap_price_min': round(AU2 * (1.0 - C2), 2) if is_netted else None,
        'overlap_price_max': BB3 if is_netted else None,
        'summary_text': summary_text
    }

if __name__ == '__main__':
    unsold_lots = [
        {'date': '09.22', 'R': 186, 'U': 156.13, 'hold_days': 3},
        {'date': '09.25', 'R': 174, 'U': 155.62, 'hold_days': 1}
    ]
    res = generate_jongjong_orders(unsold_lots, yest_close=151.45, p_budget=27313.29)
    print("SELL ORDERS (count:", len(res['sell_orders']), "):")
    for s in res['sell_orders']:
        print(" ", s['주문유형'], s['구분'], s['주문단가'], s['주문수량'], s['체결조건'], s['비고'])
    print("BUY ORDERS (count:", len(res['buy_orders']), "):")
    for b in res['buy_orders']:
        print(" ", b['주문유형'], b['호가단계'], b['주문단가'], b['주문수량'], b['체결조건'], b['비고'])
