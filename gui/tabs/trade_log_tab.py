"""
매매 기록 내역 탭 (Trade Log Tab)
선택한 전략 및 기간 동안 발생한 과거 일별 매매 기록 및 포트폴리오 변화를 상세 조회합니다.
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd

from gui.theme import COLORS, FONTS
from strategies.jongjong import JongJongStrategy
from strategies.infinite_buying_v4 import InfiniteBuyingV4Strategy


class TradeLogTab(ttk.Frame):
    """
    일별 과거 매매 기록을 테이블로 조회하고 CSV로 내보내는 탭 프레임
    """

    def __init__(self, parent, get_market_data_func):
        super().__init__(parent, style='TFrame')
        self.get_market_data_func = get_market_data_func
        self.df_current_log = pd.DataFrame()

        self._build_ui()

    def _build_ui(self):
        # 1. 상단 컨트롤 패널
        ctrl_frame = ttk.Frame(self, style='Card.TFrame', padding=12)
        ctrl_frame.pack(fill='x', padx=16, pady=(16, 8))

        ttk.Label(ctrl_frame, text="전략:", style='Card.TLabel', font=FONTS['body_bold']).pack(side='left', padx=(0, 4))
        self.combo_strat = ttk.Combobox(ctrl_frame, values=['종종이 기본전략', '무한매수법 v4.0'], state='readonly', width=15)
        self.combo_strat.set('종종이 기본전략')
        self.combo_strat.pack(side='left', padx=(0, 12))

        ttk.Label(ctrl_frame, text="티커:", style='Card.TLabel', font=FONTS['body_bold']).pack(side='left', padx=(0, 4))
        self.combo_ticker = ttk.Combobox(ctrl_frame, values=['SOXL', 'TQQQ'], state='readonly', width=7)
        self.combo_ticker.set('SOXL')
        self.combo_ticker.pack(side='left', padx=(0, 12))

        ttk.Label(ctrl_frame, text="기간:", style='Card.TLabel', font=FONTS['body_bold']).pack(side='left', padx=(0, 4))
        self.entry_start = ttk.Entry(ctrl_frame, width=11)
        self.entry_start.insert(0, "2023-01-01")
        self.entry_start.pack(side='left', padx=(0, 4))

        ttk.Label(ctrl_frame, text="~", style='Card.TLabel').pack(side='left', padx=(0, 4))
        self.entry_end = ttk.Entry(ctrl_frame, width=11)
        self.entry_end.insert(0, "2026-09-25")
        self.entry_end.pack(side='left', padx=(0, 12))

        ttk.Label(ctrl_frame, text="필터:", style='Card.TLabel', font=FONTS['body_bold']).pack(side='left', padx=(0, 4))
        self.combo_filter = ttk.Combobox(ctrl_frame, values=['전체 거래일', '매수 발생일만', '손익/매도 발생일만'], state='readonly', width=14)
        self.combo_filter.set('전체 거래일')
        self.combo_filter.pack(side='left', padx=(0, 14))
        self.combo_filter.bind('<<ComboboxSelected>>', lambda e: self._apply_filter())

        btn_load = ttk.Button(ctrl_frame, text="🔍 기록 조회", style='Primary.TButton', command=self.load_trade_logs)
        btn_load.pack(side='left', padx=(0, 8))

        btn_export = ttk.Button(ctrl_frame, text="💾 CSV 내보내기", style='Success.TButton', command=self.export_csv)
        btn_export.pack(side='right')

        # 2. 통계 요약 바 (총 거래일수, 누적 손익, 최종 자산 등)
        self.stat_bar = ttk.Frame(self, style='CardAlt.TFrame', padding=(12, 8))
        self.stat_bar.pack(fill='x', padx=16, pady=4)

        self.lbl_stats = ttk.Label(self.stat_bar, text="조회 버튼을 눌러 매매 기록을 로드하세요.", style='TLabel', font=FONTS['body_bold'])
        self.lbl_stats.pack(anchor='w')

        # 3. 매매 기록 상세 테이블
        table_frame = ttk.Frame(self, style='Card.TFrame', padding=10)
        table_frame.pack(fill='both', expand=True, padx=16, pady=(4, 16))

        self.columns = ('날짜', '종가', '모드', '매수수량', '매매손익', '보유수량', '보유현금', '총평가자산', '낙폭(DD)', '특이사항/변수')
        self.tree = ttk.Treeview(table_frame, columns=self.columns, show='headings')

        for col in self.columns:
            self.tree.heading(col, text=col)
            width = 120 if col in ('총평가자산', '보유현금', '특이사항/변수') else 90
            self.tree.column(col, width=width, anchor='center')

        scroll_y = ttk.Scrollbar(table_frame, orient='vertical', command=self.tree.yview)
        scroll_x = ttk.Scrollbar(table_frame, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tree.grid(row=0, column=0, sticky='nsew')
        scroll_y.grid(row=0, column=1, sticky='ns')
        scroll_x.grid(row=1, column=0, sticky='ew')

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

    def load_trade_logs(self):
        ticker = self.combo_ticker.get()
        strat_choice = self.combo_strat.get()
        start_date = self.entry_start.get().strip()
        end_date = self.entry_end.get().strip()

        df_market = self.get_market_data_func(ticker)
        if df_market is None or len(df_market) == 0:
            messagebox.showwarning("데이터 오류", f"[{ticker}] 데이터를 불러올 수 없습니다.")
            return

        if strat_choice == '종종이 기본전략':
            strat = JongJongStrategy(initial_capital=200000.0)
            df_res = strat.run(df_market, start_date=start_date, end_date=end_date)
            df_res['BuyQty'] = df_res['R']
            df_res['Note'] = "AR: $" + df_res['AR'].apply(lambda x: f"{x:,.0f}") + " / AK: $" + df_res['AK'].apply(lambda x: f"{x:,.0f}")
        else:
            strat = InfiniteBuyingV4Strategy(ticker=ticker, initial_capital=200000.0)
            df_res = strat.run(df_market, start_date=start_date, end_date=end_date)
            df_res['BuyQty'] = df_res['Hold'].diff().fillna(df_res['Hold']).apply(lambda x: max(0, int(x)))
            df_res['Note'] = "Turn T=" + df_res['T'].apply(lambda x: f"{x:.2f}") + " / 평단: $" + df_res['AvgPrice'].apply(lambda x: f"{x:.2f}")

        self.df_current_log = df_res
        self._apply_filter()

    def _apply_filter(self):
        if self.df_current_log.empty:
            return

        filt = self.combo_filter.get()
        df = self.df_current_log.copy()

        if filt == '매수 발생일만':
            df = df[df['BuyQty'] > 0]
        elif filt == '손익/매도 발생일만':
            df = df[df['Profit'] != 0.0]

        # 통계 바 갱신
        tot_days = len(self.df_current_log)
        filtered_days = len(df)
        tot_profit = self.df_current_log['Profit'].sum()
        final_asset = self.df_current_log.iloc[-1]['Asset']
        init_cap = 200000.0
        tot_return = (final_asset / init_cap - 1.0) * 100.0

        self.lbl_stats.config(
            text=f"📊 총 {tot_days}거래일 중 {filtered_days}건 표시 | "
                 f"누적 실현손익: ${tot_profit:+,.2f} | "
                 f"최종 자산: ${final_asset:,.0f} (수익률 {tot_return:+.2f}%) | "
                 f"최대 낙폭(MDD): {self.df_current_log['DD'].min()*100:.2f}%"
        )

        # 트리뷰 채우기
        self.tree.delete(*self.tree.get_children())
        for _, row in df.iterrows():
            d_str = row['Date'].strftime('%Y-%m-%d')
            c_str = f"${row['Close']:.2f}"
            m_str = str(row.get('Mode', ''))
            b_qty = int(row.get('BuyQty', 0))
            b_str = f"{b_qty:,}주" if b_qty > 0 else "-"
            p_val = float(row.get('Profit', 0.0))
            p_str = f"${p_val:+,.2f}" if abs(p_val) > 0.01 else "-"
            h_str = f"{int(row['Hold']):,}주"
            cash_str = f"${row['Cash']:,.0f}"
            asset_str = f"${row['Asset']:,.0f}"
            dd_str = f"{row['DD']*100:.2f}%"
            note_str = str(row.get('Note', ''))

            self.tree.insert('', 'end', values=(d_str, c_str, m_str, b_str, p_str, h_str, cash_str, asset_str, dd_str, note_str))

    def export_csv(self):
        if self.df_current_log.empty:
            messagebox.showinfo("알림", "내보낼 매매 기록 데이터가 없습니다.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            title="매매 기록 CSV 저장"
        )
        if file_path:
            self.df_current_log.to_csv(file_path, index=False, encoding='utf-8-sig')
            messagebox.showinfo("저장 완료", f"성공적으로 매매 기록이 저장되었습니다:\n{file_path}")
