"""
=====================================================================
JongJong Strategy Parameter Optimizer (종종이 전략 파라미터 최적화 엔진)
=====================================================================
2019년부터 현재까지 SOXL 및 TQQQ를 대상으로
위기준비금 비율, 최대 보유일수, 목표 익절률, 분할 수 등의 최적 조합을 탐색합니다.
"""
import sys
import os
import itertools
import time
import platform
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.dates as mdates

# 윈도우 한글 및 콘솔 인코딩 설정
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

from core.data import fetch_market_data
from core.metrics import calculate_metrics
from strategies.jongjong import JongJongStrategy


# 1. 탐색 환경 설정
TICKERS = ['SOXL', 'TQQQ']
START_DATE = '2019-01-01'
END_DATE = '2026-09-25'
INITIAL_CAPITAL = 200000.0
FEE_RATE = 0.0005
SEC_FEE = 0.0000278

# 2. 파라미터 탐색 공간 (Grid Search Space)
PARAM_GRID = {
    # 위기준비금 비율 (0%, 5%, 10%, 15%)
    'reserve_ratio': [0.0, 0.05, 0.10, 0.15],
    # 최대 보유일수 / 시간손절 (7일, 10일, 14일)
    'max_hold_days': [7, 10, 14],
    # 평시 목표 익절률 (2.0%, 2.75%, 3.5%)
    'normal_target_yield': [0.020, 0.0275, 0.035],
    # 평시 시드 분할 수 (6분할, 8분할, 10분할)
    'normal_div_rounds': [6.0, 8.0, 10.0]
}


def run_grid_search():
    print("=" * 80)
    print(f"🔍 종종이(JJ) 전략 파라미터 최적화 그리드 탐색 시작")
    print(f"• 대상 종목: {', '.join(TICKERS)}")
    print(f"• 테스트 기간: {START_DATE} ~ {END_DATE}")
    print(f"• 초기 자본: ${INITIAL_CAPITAL:,.0f} | 수수료율: {FEE_RATE*100:.2f}%")
    print("=" * 80)

    # 1. 시세 데이터 사전 다운로드 (캐싱)
    market_data = {}
    for ticker_sym in TICKERS:
        print(f"[{ticker_sym}] 시세 데이터 로딩 중...")
        market_data[ticker_sym] = fetch_market_data(ticker_sym, START_DATE, END_DATE)

    # 2. 파라미터 조합 생성
    keys, values = zip(*PARAM_GRID.items())
    combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]
    total_combinations = len(combinations)
    print(f"\n총 {total_combinations}개 파라미터 조합 탐색 (종목당 {total_combinations}회, 총 {total_combinations * len(TICKERS)}회 시뮬레이션)")

    all_results = []
    start_time = time.time()

    for idx, params in enumerate(combinations):
        r_ratio = params['reserve_ratio']
        hold_days = params['max_hold_days']
        n_yield = params['normal_target_yield']
        n_div = params['normal_div_rounds']

        div_rounds = {'Normal': n_div, 'Safe': 7.0, 'Riskoff': 5.0}
        target_yields = {'Normal': n_yield, 'Safe': 0.0025, 'Riskoff': 0.0070}

        ticker_metrics = {}

        for ticker_sym in TICKERS:
            df_market = market_data[ticker_sym]
            strat = JongJongStrategy(
                initial_capital=INITIAL_CAPITAL,
                reserve_ratio=r_ratio,
                fee_rate=FEE_RATE,
                sec_fee=SEC_FEE,
                max_hold_days=hold_days,
                div_rounds=div_rounds,
                target_yields=target_yields
            )
            df_res = strat.run(df_market, START_DATE, END_DATE)
            m = calculate_metrics(df_res, INITIAL_CAPITAL)
            ticker_metrics[ticker_sym] = m

        # 두 종목 평균 칼마 비율 및 샤프 지수 계산
        soxl_m = ticker_metrics['SOXL']
        tqqq_m = ticker_metrics['TQQQ']

        avg_calmar = (soxl_m['calmar'] + tqqq_m['calmar']) / 2.0
        avg_sharpe = (soxl_m['sharpe'] + tqqq_m['sharpe']) / 2.0
        avg_cagr = (soxl_m['cagr'] + tqqq_m['cagr']) / 2.0
        worst_mdd = min(soxl_m['mdd'], tqqq_m['mdd'])

        all_results.append({
            'reserve_ratio': r_ratio,
            'max_hold_days': hold_days,
            'normal_yield': n_yield,
            'normal_div': n_div,
            'avg_calmar': avg_calmar,
            'avg_sharpe': avg_sharpe,
            'avg_cagr': avg_cagr,
            'worst_mdd': worst_mdd,
            'soxl_cagr': soxl_m['cagr'],
            'soxl_mdd': soxl_m['mdd'],
            'soxl_asset': soxl_m['final_asset'],
            'soxl_calmar': soxl_m['calmar'],
            'tqqq_cagr': tqqq_m['cagr'],
            'tqqq_mdd': tqqq_m['mdd'],
            'tqqq_asset': tqqq_m['final_asset'],
            'tqqq_calmar': tqqq_m['calmar'],
        })

        if (idx + 1) % 20 == 0 or (idx + 1) == total_combinations:
            elapsed = time.time() - start_time
            print(f"  진행률: [{idx + 1}/{total_combinations}] 완료 ({elapsed:.1f}초 경과)")

    df_results = pd.DataFrame(all_results)

    # 3. 최적 파라미터 선정 (칼마 비율 기준 상위)
    df_sorted_calmar = df_results.sort_values(by='avg_calmar', ascending=False).reset_index(drop=True)
    df_sorted_sharpe = df_results.sort_values(by='avg_sharpe', ascending=False).reset_index(drop=True)

    print("\n" + "=" * 90)
    print("🏆 [종합 칼마 비율(Calmar Ratio) 기준 TOP 5 파라미터 조합]")
    print("(위험 대비 수익률이 가장 우수하여 계좌 안정성과 복리 성장을 극대화한 조합)")
    print("=" * 90)
    top_calmar = df_sorted_calmar.head(5)
    for i, row in top_calmar.iterrows():
        print(f"Rank {i+1}:")
        print(f"  • 파라미터: 위기준비금={row['reserve_ratio']*100:.0f}%, 최대보유={row['max_hold_days']:.0f}일, 목표익절={row['normal_yield']*100:.2f}%, 시드분할={row['normal_div']:.0f}분할")
        print(f"  • 종합 성과: 평균 Calmar={row['avg_calmar']:.2f} | 평균 Sharpe={row['avg_sharpe']:.2f} | 평균 CAGR={row['avg_cagr']:+.2f}% | 최악 MDD={row['worst_mdd']:.2f}%")
        print(f"  • SOXL: CAGR={row['soxl_cagr']:+.2f}%, MDD={row['soxl_mdd']:.2f}%, 최종자산=${row['soxl_asset']:,.0f}")
        print(f"  • TQQQ: CAGR={row['tqqq_cagr']:+.2f}%, MDD={row['tqqq_mdd']:.2f}%, 최종자산=${row['tqqq_asset']:,.0f}")
        print("-" * 90)

    # 기본값 vs 최적값 비교
    default_row = df_results[(df_results['reserve_ratio'] == 0.05) &
                             (df_results['max_hold_days'] == 10) &
                             (df_results['normal_yield'] == 0.0275) &
                             (df_results['normal_div'] == 8.0)].iloc[0]

    best_calmar_params = top_calmar.iloc[0]

    print("\n" + "=" * 90)
    print("⚖️ [기존 기본값 vs 최적 파라미터 직접 비교]")
    print("=" * 90)
    comp_data = [
        {
            '구분': '기존 기본 설정',
            '설정치': 'AK 5% | 10일 보유 | +2.75% 익절 | 8분할',
            'SOXL 최종자산': f"${default_row['soxl_asset']:,.0f}",
            'SOXL CAGR': f"{default_row['soxl_cagr']:+.2f}%",
            'SOXL MDD': f"{default_row['soxl_mdd']:.2f}%",
            'TQQQ 최종자산': f"${default_row['tqqq_asset']:,.0f}",
            'TQQQ CAGR': f"{default_row['tqqq_cagr']:+.2f}%",
            'TQQQ MDD': f"{default_row['tqqq_mdd']:.2f}%",
            '평균 Calmar': f"{default_row['avg_calmar']:.2f}"
        },
        {
            '구분': '최적화 설정 (Calmar 1위)',
            '설정치': f"AK {best_calmar_params['reserve_ratio']*100:.0f}% | {best_calmar_params['max_hold_days']:.0f}일 보유 | +{best_calmar_params['normal_yield']*100:.2f}% 익절 | {best_calmar_params['normal_div']:.0f}분할",
            'SOXL 최종자산': f"${best_calmar_params['soxl_asset']:,.0f}",
            'SOXL CAGR': f"{best_calmar_params['soxl_cagr']:+.2f}%",
            'SOXL MDD': f"{best_calmar_params['soxl_mdd']:.2f}%",
            'TQQQ 최종자산': f"${best_calmar_params['tqqq_asset']:,.0f}",
            'TQQQ CAGR': f"{best_calmar_params['tqqq_cagr']:+.2f}%",
            'TQQQ MDD': f"{best_calmar_params['tqqq_mdd']:.2f}%",
            '평균 Calmar': f"{best_calmar_params['avg_calmar']:.2f}"
        }
    ]
    print(pd.DataFrame(comp_data).to_string(index=False))
    print("=" * 90)

    # 4. 비교 차트 시각화 및 저장
    plot_optimization_comparison(market_data, default_row, best_calmar_params)
    return best_calmar_params


def plot_optimization_comparison(market_data, default_p, best_p):
    """
    기본 설정과 최적 설정의 2019-2026 자산 성장 곡선 및 MDD를 2x2 서브플롯으로 비교 출력합니다.
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 10), sharex=True)

    # 최적 파라미터 객체 구성
    best_div = {'Normal': best_p['normal_div'], 'Safe': 7.0, 'Riskoff': 5.0}
    best_yield = {'Normal': best_p['normal_yield'], 'Safe': 0.0025, 'Riskoff': 0.0070}

    for col_idx, ticker_sym in enumerate(TICKERS):
        df_market = market_data[ticker_sym]

        # 기본 전략 실행
        strat_def = JongJongStrategy(
            name=f"{ticker_sym} (기본값)",
            initial_capital=INITIAL_CAPITAL,
            reserve_ratio=default_p['reserve_ratio'],
            max_hold_days=int(default_p['max_hold_days']),
            div_rounds={'Normal': default_p['normal_div'], 'Safe': 7.0, 'Riskoff': 5.0},
            target_yields={'Normal': default_p['normal_yield'], 'Safe': 0.0025, 'Riskoff': 0.0070}
        )
        res_def = strat_def.run(df_market, START_DATE, END_DATE)

        # 최적화 전략 실행
        strat_opt = JongJongStrategy(
            name=f"{ticker_sym} (최적화)",
            initial_capital=INITIAL_CAPITAL,
            reserve_ratio=best_p['reserve_ratio'],
            max_hold_days=int(best_p['max_hold_days']),
            div_rounds=best_div,
            target_yields=best_yield
        )
        res_opt = strat_opt.run(df_market, START_DATE, END_DATE)

        # 단순 보유 (Buy & Hold)
        first_c = res_def.iloc[0]['Close']
        bnh_asset = INITIAL_CAPITAL * (res_def['Close'] / first_c)

        # 상단: 자산 곡선
        ax_top = axes[0, col_idx]
        ax_top.plot(res_opt['Date'], res_opt['Asset'], label=f"최적화 설정 (Calmar: {best_p[ticker_sym.lower()+'_calmar']:.2f})", color='#1f77b4', linewidth=2.0)
        ax_top.plot(res_def['Date'], res_def['Asset'], label=f"기본 설정 (Calmar: {default_p[ticker_sym.lower()+'_calmar']:.2f})", color='#2ca02c', linestyle='--', linewidth=1.5)
        ax_top.plot(res_def['Date'], bnh_asset, label=f"{ticker_sym} 단순보유(B&H)", color='#ff7f0e', linestyle=':', alpha=0.7)
        ax_top.axhline(INITIAL_CAPITAL, color='gray', linestyle='-', linewidth=0.8, alpha=0.5)

        ax_top.set_title(f"[{ticker_sym}] 자산 성장 곡선 비교 (2019 ~ 2026)", fontsize=13, fontweight='bold', pad=10)
        ax_top.set_ylabel("자산 가치 ($)", fontsize=11)
        ax_top.yaxis.set_major_formatter(ticker.StrMethodFormatter('${x:,.0f}'))
        ax_top.grid(True, linestyle='--', alpha=0.4)
        ax_top.legend(loc='upper left', fontsize=9)

        # 하단: 낙폭 (Drawdown)
        ax_bot = axes[1, col_idx]
        dd_opt = res_opt['DD'] * 100.0
        dd_def = res_def['DD'] * 100.0
        ax_bot.plot(res_opt['Date'], dd_opt, label=f"최적화 MDD ({best_p[ticker_sym.lower()+'_mdd']:.1f}%)", color='#1f77b4', linewidth=1.5)
        ax_bot.plot(res_def['Date'], dd_def, label=f"기본 MDD ({default_p[ticker_sym.lower()+'_mdd']:.1f}%)", color='#2ca02c', linestyle='--', linewidth=1.2)
        ax_bot.fill_between(res_opt['Date'], dd_opt, 0, color='#1f77b4', alpha=0.15)

        ax_bot.set_title(f"[{ticker_sym}] 고점 대비 낙폭(Drawdown) 비교", fontsize=11, fontweight='bold', pad=8)
        ax_bot.set_ylabel("Drawdown (%)", fontsize=10)
        ax_bot.set_xlabel("일자", fontsize=10)
        ax_bot.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:.0f}%'))
        ax_bot.grid(True, linestyle='--', alpha=0.4)
        ax_bot.legend(loc='lower left', fontsize=9)
        ax_bot.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

    plt.tight_layout()
    plt.savefig('optimization_result.png', dpi=150)
    print("📈 최적화 비교 차트가 'optimization_result.png' 파일로 저장되었습니다.")


if __name__ == "__main__":
    run_grid_search()
