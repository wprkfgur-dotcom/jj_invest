"""
주문 생성 및 포트폴리오 상태 연산 엔진 (Order Engine)
종종이 전략 및 무한매수법 v4.0의 최근 매매 내역과 오늘자 LOC 주문표를 산출합니다.
"""
import pandas as pd

from strategies.jongjong import JongJongStrategy, safe_round4, round_down, round_up
from strategies.infinite_buying_v4 import InfiniteBuyingV4Strategy


def get_jongjong_today_orders(df_market: pd.DataFrame,
                              initial_capital: float = 200000.0,
                              reserve_ratio: float = 0.05,
                              div_rounds: dict = None,
                              target_yields: dict = None,
                              max_hold_days: int = 10):
    """
    최신 시장 데이터를 바탕으로 종종이 전략의 현재 포트폴리오 상태 및 오늘 LOC 주문표를 계산합니다.
    """
    strat = JongJongStrategy(
        initial_capital=initial_capital,
        reserve_ratio=reserve_ratio,
        div_rounds=div_rounds,
        target_yields=target_yields,
        max_hold_days=max_hold_days
    )

    # 1. 과거 1년치 시뮬레이션을 수행하여 가장 최근 상태(현금, 보유로트, AR, AK 등) 확정
    start_date = (df_market['Date'].max() - pd.Timedelta(days=400)).strftime('%Y-%m-%d')
    end_date = df_market['Date'].max().strftime('%Y-%m-%d')

    df_hist = strat.run(df_market, start_date=start_date, end_date=end_date)
    last_row = df_hist.iloc[-1]
    latest_date = last_row['Date']
    latest_close = last_row['Close']

    # 2. 미체결 보유 로트 추적
    # df_hist에서 아직 매도되지 않은 로트들을 찾음
    # run()의 records 구조상 매수한 날(R > 0) 중 매도일(W)이 없거나 아직 유효한 로트
    # 시뮬레이션 끝 시점(t) 기준 미매도 로트 재구성
    hold_shares = int(last_row['Hold'])
    cash = float(last_row['Cash'])
    asset = float(last_row['Asset'])
    ar_val = float(last_row['AR'])
    ak_val = float(last_row['AK'])
    current_mode = str(last_row['Mode'])

    # 종종이 다음 날 주문을 위한 당일 지표 계산
    # df_market 최신 데이터를 준비하여 MA5, MA20 및 다음 모드 확인
    df_ind = strat.prepare_indicators(df_market, start_date)
    last_idx = df_ind[df_ind['Date'] <= latest_date].index[-1]
    next_mode = df_ind.loc[last_idx, 'DB_Mode']
    if last_row['Flag']:
        next_mode = 'Riskoff'

    # 다음 날 1회 매수 시도 예산
    div = strat.div_rounds.get(next_mode, 8.0)
    p_budget = ar_val / div if cash >= (ar_val / div) else cash
    p_budget = max(0.0, p_budget)

    AU1 = p_budget
    AU2 = latest_close
    is_normal = (next_mode == 'Normal')
    is_riskoff = (next_mode == 'Riskoff')
    C2 = strat.range_normal
    C4 = strat.order_split_count
    C6 = strat.order_curvature
    O4 = strat.risk_buy_offset

    BB3 = round_down(AU2 * (1.0 + C2), 2)
    a_val = C2 if is_normal else (O4 if is_riskoff else 0.0)
    AY2 = safe_round4(AU2 * (1.0 + a_val) - 0.01)
    AZ2 = int(AU1 / AY2) if AY2 > 0 else 0
    AY3 = safe_round4(AU2 * (1.0 - C2))

    AY4 = C4 - 1
    ay_list = [AY2]
    if AY4 - 1 > 0:
        for i_seq in range(AY4 - 1):
            if AY4 - 2 == 0:
                ay_list.append(None)
            else:
                denom = AY3 + ((AY4 - 2.0 - i_seq) / (AY4 - 2.0)) ** C6 * (AY2 - AY3)
                val = round_down(AU1 / (AU1 / denom), 2) if (AU1 > 0 and denom > 0) else None
                ay_list.append(val)

    az_list = [AZ2]
    for k in range(1, len(ay_list)):
        if ay_list[k] is None or ay_list[k-1] is None or ay_list[k] <= 0 or ay_list[k-1] <= 0:
            az_list.append(0)
        else:
            az_list.append(int(AU1 / ay_list[k]) - int(AU1 / ay_list[k-1]))

    # 매수 주문표 구성
    buy_orders = []
    accum_qty = 0
    for idx in range(len(ay_list)):
        p = ay_list[idx]
        q = az_list[idx] if idx < len(az_list) else 0
        if p is not None and p > 0 and q > 0:
            accum_qty += q
            amt = p * q
            cond = f"종가 ≤ ${p:.2f} 체결"
            buy_orders.append({
                '호가단계': f"{idx+1}차 매수",
                '주문유형': 'LOC 매수',
                '주문단가': f"${p:.2f}",
                '주문수량': f"{q:,}주",
                '누적수량': f"{accum_qty:,}주",
                '예상금액': f"${amt:,.2f}",
                '체결조건': cond
            })

    # 매도 주문표 구성 (보유 주식이 있을 경우)
    sell_orders = []
    target_yield = strat.target_yields.get(next_mode, 0.0275)
    # 현재 보유 중인 경우 대표 목표 매도가 계산
    if hold_shares > 0:
        # 최근 종가 기준 또는 추정 평단가 기준 익절 목표가
        est_target = round_up(latest_close * (1.0 + target_yield), 2)
        sell_orders.append({
            '구분': '목표 익절 매도',
            '주문유형': 'LOC 매도 (또는 지정가)',
            '주문단가': f"${est_target:.2f}",
            '주문수량': f"{hold_shares:,}주",
            '예상금액': f"${est_target * hold_shares:,.2f}",
            '체결조건': f"종가 ≥ ${est_target:.2f} (수익률 {target_yield*100:+.2f}%)"
        })

    # 최근 15개 거래 내역 추출
    recent_logs = []
    for _, row in df_hist.tail(20).iterrows():
        b_qty = int(row.get('R', 0))
        act = "관망/유지"
        if b_qty > 0:
            act = f"매수 ({b_qty:,}주)"
        recent_logs.append({
            'Date': row['Date'].strftime('%Y-%m-%d'),
            'Close': f"${row['Close']:.2f}",
            'Mode': row.get('Mode', ''),
            'Action': act,
            'Cash': f"${row['Cash']:,.0f}",
            'Hold': f"{int(row['Hold']):,}주",
            'Asset': f"${row['Asset']:,.0f}",
            'DD': f"{row['DD']*100:.2f}%",
            'Profit': f"${row.get('Profit', 0):+,.2f}"
        })

    return {
        'strategy_name': '종종이 기본전략',
        'latest_date': latest_date.strftime('%Y-%m-%d'),
        'latest_close': latest_close,
        'current_mode': next_mode,
        'hold_shares': hold_shares,
        'cash': cash,
        'asset': asset,
        'ar_val': ar_val,
        'ak_val': ak_val,
        'p_budget': p_budget,
        'target_yield': target_yield,
        'buy_orders': buy_orders,
        'sell_orders': sell_orders,
        'recent_logs': recent_logs,
        'df_hist': df_hist
    }


def get_infinite_buying_today_orders(df_market: pd.DataFrame,
                                     ticker: str = 'SOXL',
                                     initial_capital: float = 200000.0,
                                     divisions: int = 40):
    """
    최신 시장 데이터를 바탕으로 무한매수법 v4.0의 현재 상태 및 오늘 LOC 주문표를 계산합니다.
    """
    strat = InfiniteBuyingV4Strategy(
        ticker=ticker,
        initial_capital=initial_capital,
        divisions=divisions
    )

    start_date = (df_market['Date'].max() - pd.Timedelta(days=500)).strftime('%Y-%m-%d')
    end_date = df_market['Date'].max().strftime('%Y-%m-%d')

    df_hist = strat.run(df_market, start_date=start_date, end_date=end_date)
    last_row = df_hist.iloc[-1]
    latest_date = last_row['Date']
    latest_close = last_row['Close']

    hold_shares = int(last_row['Hold'])
    avg_price = float(last_row['AvgPrice'])
    cash = float(last_row['Cash'])
    asset = float(last_row['Asset'])
    T = float(last_row['T'])
    mode = str(last_row['Mode'])

    is_soxl = ('SOXL' in ticker.upper())
    limit_pct = 0.20 if is_soxl else 0.15

    # 주문 리스트
    sell_orders = []
    buy_orders = []

    if mode == 'NORMAL':
        # 일반모드
        star_pct = strat.calculate_star_pct(T)
        star_point = round(avg_price * (1.0 + star_pct), 2) if (hold_shares > 0 and avg_price > 0) else latest_close
        buy_p_star = max(star_point - 0.01, 0.01)

        # 1회 매수 시도액
        budget = cash / (divisions - T) if T < divisions else cash

        # 매도 주문표
        if hold_shares > 0:
            quarter_qty = int(hold_shares / 4)
            limit_qty = hold_shares - quarter_qty
            limit_price = round(avg_price * (1.0 + limit_pct), 2)

            if quarter_qty > 0:
                sell_orders.append({
                    '구분': '쿼터매도 (1/4)',
                    '주문유형': 'LOC 매도',
                    '주문단가': f"${star_point:.2f}",
                    '주문수량': f"{quarter_qty:,}주",
                    '예상금액': f"${star_point * quarter_qty:,.2f}",
                    '체결조건': f"종가 ≥ 별지점 (${star_point:.2f})"
                })
            if limit_qty > 0:
                sell_orders.append({
                    '구분': '지정가매도 (3/4)',
                    '주문유형': '지정가(Limit) 매도',
                    '주문단가': f"${limit_price:.2f}",
                    '주문수량': f"{limit_qty:,}주",
                    '예상금액': f"${limit_price * limit_qty:,.2f}",
                    '체결조건': f"장중 고가 ≥ ${limit_price:.2f} ({limit_pct*100:+.0f}%)"
                })

        # 매수 주문표
        if hold_shares == 0 or T <= 0:
            qty = int(budget / latest_close) if latest_close > 0 else 0
            buy_orders.append({
                '호가단계': '처음 매수 (1회분)',
                '주문유형': 'LOC 매수 (+10~15% 큰수)',
                '주문단가': f"${latest_close * 1.12:.2f}",
                '주문수량': f"{qty:,}주",
                '누적수량': f"{qty:,}주",
                '예상금액': f"${latest_close * qty:,.2f}",
                '체결조건': '무조건 전량 체결 유도 (새 사이클)'
            })
        elif T < (divisions / 2.0):
            # 전반전: 0.5회분 별지점 LOC + 0.5회분 평단 LOC
            b_half = budget * 0.5
            q_star = int(b_half / buy_p_star) if buy_p_star > 0 else 0
            q_avg = int(b_half / avg_price) if avg_price > 0 else 0

            buy_orders.append({
                '호가단계': '전반전 1차 (0.5회분)',
                '주문유형': 'LOC 매수',
                '주문단가': f"${buy_p_star:.2f}",
                '주문수량': f"{q_star:,}주",
                '누적수량': f"{q_star:,}주",
                '예상금액': f"${buy_p_star * q_star:,.2f}",
                '체결조건': f"종가 ≤ 별지점-0.01 (${buy_p_star:.2f})"
            })
            buy_orders.append({
                '호가단계': '전반전 2차 (0.5회분)',
                '주문유형': 'LOC 매수',
                '주문단가': f"${avg_price:.2f}",
                '주문수량': f"{q_avg:,}주",
                '누적수량': f"{q_star + q_avg:,}주",
                '예상금액': f"${avg_price * q_avg:,.2f}",
                '체결조건': f"종가 ≤ 내 평단가 (${avg_price:.2f})"
            })
        else:
            # 후반전: 1회분 전체 별지점 LOC
            q_star = int(budget / buy_p_star) if buy_p_star > 0 else 0
            buy_orders.append({
                '호가단계': '후반전 (1.0회분)',
                '주문유형': 'LOC 매수',
                '주문단가': f"${buy_p_star:.2f}",
                '주문수량': f"{q_star:,}주",
                '누적수량': f"{q_star:,}주",
                '예상금액': f"${buy_p_star * q_star:,.2f}",
                '체결조건': f"종가 ≤ 별지점-0.01 (${buy_p_star:.2f})"
            })
    else:
        # 리버스모드 (SMA 5)
        # 직전 5거래일 평균
        sma5 = float(df_hist.tail(5)['Close'].mean())
        buy_p = max(sma5 - 0.01, 0.01)
        sell_qty = int(hold_shares / 20)
        q_budget = cash / 4.0
        q_buy = int(q_budget / buy_p) if buy_p > 0 else 0

        if sell_qty > 0:
            sell_orders.append({
                '구분': '리버스 매도 (1/20)',
                '주문유형': 'LOC 매도 (또는 1일차 MOC)',
                '주문단가': f"${sma5:.2f}",
                '주문수량': f"{sell_qty:,}주",
                '예상금액': f"${sma5 * sell_qty:,.2f}",
                '체결조건': f"종가 ≥ SMA5 (${sma5:.2f})"
            })
        if q_buy > 0:
            buy_orders.append({
                '호가단계': '리버스 쿼터매수 (잔금/4)',
                '주문유형': 'LOC 매수',
                '주문단가': f"${buy_p:.2f}",
                '주문수량': f"{q_buy:,}주",
                '누적수량': f"{q_buy:,}주",
                '예상금액': f"${buy_p * q_buy:,.2f}",
                '체결조건': f"종가 ≤ SMA5-0.01 (${buy_p:.2f})"
            })

    # 최근 15개 거래 내역
    recent_logs = []
    for _, row in df_hist.tail(20).iterrows():
        recent_logs.append({
            'Date': row['Date'].strftime('%Y-%m-%d'),
            'Close': f"${row['Close']:.2f}",
            'Mode': row.get('Mode', ''),
            'Action': f"T={row.get('T', 0):.2f}",
            'Cash': f"${row['Cash']:,.0f}",
            'Hold': f"{int(row['Hold']):,}주",
            'Asset': f"${row['Asset']:,.0f}",
            'DD': f"{row['DD']*100:.2f}%",
            'Profit': f"${row.get('Profit', 0):+,.2f}"
        })

    return {
        'strategy_name': '무한매수법 v4.0',
        'latest_date': latest_date.strftime('%Y-%m-%d'),
        'latest_close': latest_close,
        'current_mode': mode,
        'hold_shares': hold_shares,
        'avg_price': avg_price,
        'cash': cash,
        'asset': asset,
        'T': T,
        'buy_orders': buy_orders,
        'sell_orders': sell_orders,
        'recent_logs': recent_logs,
        'df_hist': df_hist
    }
