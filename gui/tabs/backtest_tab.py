"""
백테스트 시뮬레이터 탭 (Backtest Simulator Tab)
다양한 전략(종종이 기본전략, 무한매수법 v4.0, 단순보유)의 백테스트를 실행하고
성과 비교 테이블 및 고해상도 인터랙티브 차트를 화면에 직접 렌더링합니다.
"""
from tkinter import ttk, messagebox
import threading

import platform
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.ticker as ticker
import matplotlib.dates as mdates

# 한글 폰트 설정
if platform.system() == 'Windows':
    plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

from gui.theme import COLORS, FONTS
from core.metrics import build_comparison_table
from strategies import JongJongStrategy, InfiniteBuyingV4Strategy, BuyAndHoldStrategy


class BacktestTab(ttk.Frame):
    """
    백테스트 실행 및 결과 차트/테이블 시각화 탭 프레임
    """

    def __init__(self, parent, get_market_data_func):
        super().__init__(parent, style='TFrame')
        self.get_market_data_func = get_market_data_func
        self.figure = None
        self.canvas = None
        self.toolbar = None

        self._build_ui()

    def _build_ui(self):
        # 1. 상단 파라미터 제어 패널
        ctrl_frame = ttk.Frame(self, style='Card.TFrame', padding=12)
        ctrl_frame.pack(fill='x', padx=16, pady=(16, 8))

        ttk.Label(ctrl_frame, text="비교 대상:", style='Card.TLabel', font=FONTS['body_bold']).pack(side='left', padx=(0, 4))
        self.combo_mode = ttk.Combobox(ctrl_frame, values=['모든 전략 종합 비교', '종종이 기본전략', '무한매수법 v4.0', '단순보유(B&H)'], state='readonly', width=18)
        self.combo_mode.set('모든 전략 종합 비교')
        self.combo_mode.pack(side='left', padx=(0, 12))

        ttk.Label(ctrl_frame, text="티커:", style='Card.TLabel', font=FONTS['body_bold']).pack(side='left', padx=(0, 4))
        self.combo_ticker = ttk.Combobox(ctrl_frame, values=['SOXL', 'TQQQ'], state='readonly', width=7)
        self.combo_ticker.set('SOXL')
        self.combo_ticker.pack(side='left', padx=(0, 12))

        ttk.Label(ctrl_frame, text="시작일:", style='Card.TLabel', font=FONTS['body_bold']).pack(side='left', padx=(0, 4))
        self.entry_start = ttk.Entry(ctrl_frame, width=11)
        self.entry_start.insert(0, "2019-01-01")
        self.entry_start.pack(side='left', padx=(0, 4))

        ttk.Label(ctrl_frame, text="~ 종료일:", style='Card.TLabel', font=FONTS['body_bold']).pack(side='left', padx=(0, 4))
        self.entry_end = ttk.Entry(ctrl_frame, width=11)
        self.entry_end.insert(0, "2026-09-25")
        self.entry_end.pack(side='left', padx=(0, 12))

        ttk.Label(ctrl_frame, text="원금 ($):", style='Card.TLabel', font=FONTS['body_bold']).pack(side='left', padx=(0, 4))
        self.entry_capital = ttk.Entry(ctrl_frame, width=10)
        self.entry_capital.insert(0, "200000")
        self.entry_capital.pack(side='left', padx=(0, 14))

        self.btn_run = ttk.Button(ctrl_frame, text="▶ 백테스트 실행", style='Primary.TButton', command=self.start_backtest_thread)
        self.btn_run.pack(side='left', padx=(0, 12))

        self.lbl_status = ttk.Label(ctrl_frame, text="준비 완료", style='CardMuted.TLabel')
        self.lbl_status.pack(side='left')

        # 2. 메인 컨텐츠 영역 (좌우 또는 상하 분할)
        # 상단: 성과 비교 표 / 하단: 차트
        paned = ttk.PanedWindow(self, orient='vertical')
        paned.pack(fill='both', expand=True, padx=16, pady=(4, 16))

        # (1) 상단 성과 비교 테이블 프레임
        table_container = ttk.Frame(paned, style='Card.TFrame', padding=10)
        paned.add(table_container, weight=1)

        ttk.Label(table_container, text="📊 전체 전략 종합 성과 지표 비교", style='CardTitle.TLabel').pack(anchor='w', pady=(0, 6))

        comp_cols = ('전략명', '초기원금', '최종총자산', '총수익률', 'CAGR', '최대낙폭(MDD)', '샤프지수', '칼마비율', '최종현금', '보유수량')
        self.tree_comp = ttk.Treeview(table_container, columns=comp_cols, show='headings', height=4)
        for c in comp_cols:
            self.tree_comp.heading(c, text=c)
            w = 140 if c in ('전략명', '최종총자산', '최종현금') else 85
            self.tree_comp.column(c, width=w, anchor='center')
        self.tree_comp.pack(fill='x', pady=(0, 4))

        # (2) 하단 Matplotlib 차트 임베딩 프레임
        chart_container = ttk.Frame(paned, style='Card.TFrame', padding=6)
        paned.add(chart_container, weight=3)

        self.chart_frame = chart_container

        # 초기 차트 Figure 생성
        self._init_chart()

    def _init_chart(self):
        plt.style.use('dark_background')
        if platform.system() == 'Windows':
            plt.rcParams['font.family'] = 'Malgun Gothic'
        plt.rcParams['axes.unicode_minus'] = False
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(10, 6), gridspec_kw={'height_ratios': [2.2, 1]}, sharex=True)
        self.fig.patch.set_facecolor('#1e1e2e')
        self.ax1.set_facecolor('#181825')
        self.ax2.set_facecolor('#181825')

        self.ax1.set_title("전략별 총자산 성장 곡선", fontsize=11, color='#cdd6f4')
        self.ax2.set_title("고점 대비 낙폭(Drawdown %)", fontsize=10, color='#cdd6f4')

        self.fig.tight_layout()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill='both', expand=True)

        toolbar_frame = ttk.Frame(self.chart_frame, style='Card.TFrame')
        toolbar_frame.pack(fill='x')
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.toolbar.update()

    def start_backtest_thread(self):
        self.btn_run.config(state='disabled')
        self.lbl_status.config(text="백테스트 연산 중...", foreground=COLORS['accent_yellow'])

        thread = threading.Thread(target=self._run_backtest, daemon=True)
        thread.start()

    def _run_backtest(self):
        try:
            ticker_symbol = self.combo_ticker.get()
            mode_choice = self.combo_mode.get()
            start_date = self.entry_start.get().strip()
            end_date = self.entry_end.get().strip()
            cap = float(self.entry_capital.get().replace(',', '').strip())

            df_market = self.get_market_data_func(ticker_symbol)
            if df_market is None or len(df_market) == 0:
                raise ValueError("시세 데이터를 로드할 수 없습니다.")

            # 전략 인스턴스 준비
            all_strats = [
                JongJongStrategy(name="종종이 기본전략", initial_capital=cap),
                InfiniteBuyingV4Strategy(name="무한매수법 v4.0", ticker=ticker_symbol, initial_capital=cap, divisions=40),
                BuyAndHoldStrategy(name=f"{ticker_symbol} 단순보유(B&H)", initial_capital=cap)
            ]

            if mode_choice == '종종이 기본전략':
                active_strats = [all_strats[0]]
            elif mode_choice == '무한매수법 v4.0':
                active_strats = [all_strats[1]]
            elif mode_choice == '단순보유(B&H)':
                active_strats = [all_strats[2]]
            else:
                active_strats = all_strats

            results_dict = {}
            for st in active_strats:
                df_res = st.run(df_market, start_date, end_date)
                results_dict[st.name] = (df_res, st.initial_capital)

            # UI 스레드에서 결과 갱신
            self.after(0, lambda: self._update_results(results_dict, ticker_symbol))

        except Exception as e:
            err_msg = str(e)
            self.after(0, lambda: messagebox.showerror("백테스트 오류", f"오류 발생:\n{err_msg}"))
            self.after(0, lambda: self.lbl_status.config(text="오류 발생", foreground=COLORS['accent_red']))
        finally:
            self.after(0, lambda: self.btn_run.config(state='normal'))

    def _update_results(self, results_dict, ticker_symbol):
        # 1. 성과 테이블 갱신
        self.tree_comp.delete(*self.tree_comp.get_children())
        df_comp = build_comparison_table(results_dict)

        for _, r in df_comp.iterrows():
            self.tree_comp.insert('', 'end', values=(
                r['전략명'], r['초기원금($)'], r['최종총자산($)'], r['총수익률(%)'],
                r['CAGR(%)'], r['최대낙폭(MDD)'], r['샤프지수'], r['칼마비율'],
                r['최종현금($)'], r['보유수량(주)']
            ))

        # 2. Matplotlib 차트 갱신
        self.ax1.clear()
        self.ax2.clear()

        palette = ['#89b4fa', '#fab387', '#a6e3a1', '#f38ba8', '#cba6f7']

        first_key = list(results_dict.keys())[0]
        _, first_cap = results_dict[first_key]

        for idx, (strat_name, (df_res, _)) in enumerate(results_dict.items()):
            c = palette[idx % len(palette)]
            self.ax1.plot(df_res['Date'], df_res['Asset'], label=f"{strat_name}", color=c, linewidth=2.0)
            dd_pct = df_res['DD'] * 100.0
            self.ax2.plot(df_res['Date'], dd_pct, label=f"{strat_name}", color=c, linewidth=1.2)

        self.ax1.axhline(first_cap, color='#6c7086', linestyle='--', alpha=0.6, label='원금 기준선')
        self.ax1.set_title(f"백테스트 자산 성장 곡선 ({ticker_symbol})", fontsize=11, fontweight='bold', color='#cdd6f4', pad=8)
        self.ax1.set_ylabel("총자산 ($)", fontsize=9, color='#a6adc8')
        self.ax1.yaxis.set_major_formatter(ticker.StrMethodFormatter('${x:,.0f}'))
        self.ax1.grid(True, linestyle=':', alpha=0.3, color='#45475a')
        self.ax1.legend(loc='upper left', fontsize=8, facecolor='#27273a', edgecolor='#45475a')

        self.ax2.set_title("고점 대비 최대 낙폭 (MDD %)", fontsize=10, fontweight='bold', color='#cdd6f4', pad=6)
        self.ax2.set_ylabel("낙폭 (%)", fontsize=9, color='#a6adc8')
        self.ax2.set_xlabel("거래일자", fontsize=9, color='#a6adc8')
        self.ax2.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:.0f}%'))
        self.ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        self.ax2.grid(True, linestyle=':', alpha=0.3, color='#45475a')
        self.ax2.legend(loc='lower left', fontsize=8, facecolor='#27273a', edgecolor='#45475a')

        self.fig.tight_layout()
        self.canvas.draw()

        self.lbl_status.config(text="백테스트 완료!", foreground=COLORS['accent_green'])
