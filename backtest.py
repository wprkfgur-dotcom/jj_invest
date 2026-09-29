"""
=====================================================================
Multi-Strategy Backtesting Framework (다중 전략 백테스트 러너)
=====================================================================
여러 전략을 모듈식으로 추가하고 동일 기간/종목에서 성과를 한눈에 비교할 수 있습니다.
"""
import sys
import os

# 윈도우 콘솔 UTF-8 인코딩 대응
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core.data import fetch_market_data
from core.metrics import calculate_yearly_stats, build_comparison_table
from core.visualizer import plot_comparison
from strategies import JongJongStrategy, BuyAndHoldStrategy, InfiniteBuyingV4Strategy


# =====================================================================
# [사용자 설정 영역 (User Settings)]
# =====================================================================

# 1. 기본 백테스트 환경
TICKER = 'SOXL'                # 대상 종목 티커 (예: 'SOXL', 'TQQQ', 'UPRO', 'NVDA')
START_DATE = '2019-01-01'      # 매매 시작일 (YYYY-MM-DD)
END_DATE = '2026-09-25'        # 매매 종료일 (YYYY-MM-DD)
INITIAL_CAPITAL = 200000.0     # 초기 투자 원금 ($)

# 2. 거래 비용 설정
FEE_RATE = 0.0005              # 매매 수수료율 (편도 0.05%)
SEC_FEE = 0.0000278            # 미국 증권거래세 (매도 시 부과)

# 3. 비교할 전략 목록 (종종이 기본전략 + 무한매수법 v4.0 + 단순보유 벤치마크)
STRATEGIES = [
    # ① 종종이 기본전략 (오리지널 설정: 8분할 / +2.75% 익절 / 위기준비금 5% / 10일 보유)
    JongJongStrategy(
        name="종종이 기본전략",
        initial_capital=INITIAL_CAPITAL,
        reserve_ratio=0.05,
        fee_rate=FEE_RATE,
        sec_fee=SEC_FEE,
        max_hold_days=10,
        div_rounds={'Normal': 8.0, 'Safe': 7.0, 'Riskoff': 5.0},
        target_yields={'Normal': 0.0275, 'Safe': 0.0025, 'Riskoff': 0.0070}
    ),
    # ② 무한매수법 v4.0 (라오어 공식: 40분할 / 동적 T 회차 / 별% LOC 매수·쿼터매도 / 지정가 매도 / 소진후 리버스모드)
    InfiniteBuyingV4Strategy(
        name="무한매수법 v4.0",
        ticker=TICKER,
        initial_capital=INITIAL_CAPITAL,
        divisions=40,
        fee_rate=FEE_RATE,
        sec_fee=SEC_FEE
    ),
    # ③ 단순 보유 벤치마크 (Buy & Hold)
    BuyAndHoldStrategy(
        name=f"{TICKER} 단순보유(B&H)",
        initial_capital=INITIAL_CAPITAL,
        fee_rate=FEE_RATE,
        sec_fee=SEC_FEE
    )
]

# 4. 출력 및 시각화 옵션
SAVE_CHART = True              # 차트 이미지 파일 저장 여부
CHART_FILENAME = 'backtest_result.png'  # 저장 파일명
SHOW_CHART = False             # 화면 차트 팝업 표시 여부 (이미지로 저장됨)
# =====================================================================


def run_all_strategies():
    # 1. 공통 시세 데이터 1회 다운로드
    df_market = fetch_market_data(TICKER, START_DATE, END_DATE)

    results_dict = {}

    print("\n" + "=" * 80)
    print(f"🚀 [{TICKER}] 백테스트 실행 ({START_DATE} ~ {END_DATE})")
    print("=" * 80)

    # 2. 등록된 각 전략 순차 실행
    for strat in STRATEGIES:
        print(f"• 전략 연산 중: [{strat.name}] ...")
        df_res = strat.run(df_market, START_DATE, END_DATE)
        results_dict[strat.name] = (df_res, strat.initial_capital)

    # 3. 종종이 기본전략 전체 기간 상세 요약 출력
    for strat_name, (df_res, cap) in results_dict.items():
        if "종종이" in strat_name:
            final_asset = df_res.iloc[-1]['Asset']
            total_return = (final_asset / cap - 1.0) * 100.0
            mdd = df_res['DD'].min() * 100.0

            bnh_str = ""
            for b_name, (df_b, cap_b) in results_dict.items():
                if "단순보유" in b_name or "B&H" in b_name:
                    bnh_ret = (df_b.iloc[-1]['Asset'] / cap_b - 1.0) * 100.0
                    bnh_str = f" (동일 기간 단순 보유 시: {bnh_ret:+.2f}%)"
                    break

            print("\n" + "="*75)
            print(f"=== '{strat_name}' 전체 기간 백테스트 요약 ({TICKER}) ===")
            print("="*75)
            print(f"테스트 기간   : {df_res.iloc[0]['Date'].strftime('%Y-%m-%d')} ~ {df_res.iloc[-1]['Date'].strftime('%Y-%m-%d')} (총 {len(df_res)}거래일)")
            print(f"초기 원금     : ${cap:,.2f}")
            print(f"최종 총자산   : ${final_asset:,.2f} (현금: ${df_res.iloc[-1]['Cash']:,.2f} / 보유수량: {df_res.iloc[-1]['Hold']}주)")
            if 'AR' in df_res.columns and 'AK' in df_res.columns:
                print(f"  - 운용 시드(AR)     : ${df_res.iloc[-1]['AR']:,.2f}")
                print(f"  - 누적 위기준비금(AK): ${df_res.iloc[-1]['AK']:,.2f}")
            print(f"전체 수익률   : {total_return:+.2f}%{bnh_str}")
            print(f"최대 낙폭(MDD): {mdd:.2f}%")
            print("="*75)
            break

    # 4. 전체 전략 비교 요약 테이블 출력
    if len(results_dict) > 1:
        print("\n" + "=" * 80)
        print(f"📊 [전체 전략 종합 성과 비교 요약] ({TICKER})")
        print("=" * 80)
        df_comp = build_comparison_table(results_dict)
        print(df_comp.to_string(index=False))
        print("=" * 80)

    # 5. 각 전략별 연도별 성과 출력
    for strat_name, (df_res, cap) in results_dict.items():
        print(f"\n[📅 연도별 성과: {strat_name}]")
        df_yearly = calculate_yearly_stats(df_res, cap)
        print(df_yearly.to_string(index=False))
        print("-" * 80)

    # 5. 다중 전략 통합 비교 차트 출력
    plot_comparison(
        results_dict=results_dict,
        ticker_symbol=TICKER,
        save_chart=SAVE_CHART,
        chart_filename=CHART_FILENAME,
        show_chart=SHOW_CHART
    )


# 하위 호환성을 위한 래퍼 함수 (기존 단일 호출 호환)
def fetch_and_prepare_data(ticker_symbol, start_date, end_date):
    strat = JongJongStrategy()
    df = fetch_market_data(ticker_symbol, start_date, end_date)
    return strat.prepare_indicators(df, start_date)

def run_jongjong_backtest(df, start_date, end_date, initial_capital=200000.0, **kwargs):
    strat = JongJongStrategy(initial_capital=initial_capital, **kwargs)
    return strat.run(df, start_date, end_date)


if __name__ == "__main__":
    run_all_strategies()