"""
오늘 주문 가이드 탭 (Today's Order Tab)
선택한 전략 및 종목에 따라 오늘 밤 걸어야 하는 LOC 매수/매도 주문표를 시각화합니다.
"""
from tkinter import ttk, messagebox

from gui.theme import COLORS, FONTS
from gui.order_engine import get_jongjong_today_orders, get_infinite_buying_today_orders


class TodayOrderTab(ttk.Frame):
    """
    오늘 매수/매도 주문표 및 포트폴리오 현황을 표시하는 탭 프레임
    """

    def __init__(self, parent, get_market_data_func):
        super().__init__(parent, style='TFrame')
        self.get_market_data_func = get_market_data_func
        self.current_orders_data = None

        self._build_ui()

    def _build_ui(self):
        # 1. 상단 컨트롤 패널 (종목 선택, 전략 선택, 새로고침)
        ctrl_frame = ttk.Frame(self, style='Card.TFrame', padding=12)
        ctrl_frame.pack(fill='x', padx=16, pady=(16, 8))

        ttk.Label(ctrl_frame, text="투자 전략:", style='Card.TLabel', font=FONTS['body_bold']).pack(side='left', padx=(0, 6))
        self.combo_strat = ttk.Combobox(ctrl_frame, values=['종종이 기본전략', '무한매수법 v4.0'], state='readonly', width=16)
        self.combo_strat.set('종종이 기본전략')
        self.combo_strat.pack(side='left', padx=(0, 16))
        self.combo_strat.bind('<<ComboboxSelected>>', lambda e: self.refresh_orders())

        ttk.Label(ctrl_frame, text="종목 티커:", style='Card.TLabel', font=FONTS['body_bold']).pack(side='left', padx=(0, 6))
        self.combo_ticker = ttk.Combobox(ctrl_frame, values=['SOXL', 'TQQQ'], state='readonly', width=8)
        self.combo_ticker.set('SOXL')
        self.combo_ticker.pack(side='left', padx=(0, 16))
        self.combo_ticker.bind('<<ComboboxSelected>>', lambda e: self.refresh_orders())

        ttk.Label(ctrl_frame, text="원금 ($):", style='Card.TLabel', font=FONTS['body_bold']).pack(side='left', padx=(0, 6))
        self.entry_capital = ttk.Entry(ctrl_frame, width=12)
        self.entry_capital.insert(0, "200000")
        self.entry_capital.pack(side='left', padx=(0, 16))

        btn_refresh = ttk.Button(ctrl_frame, text="🔄 주문표 계산/새로고침", style='Primary.TButton', command=self.refresh_orders)
        btn_refresh.pack(side='left', padx=(0, 12))

        btn_copy = ttk.Button(ctrl_frame, text="📋 MTS/HTS 주문 복사", style='Success.TButton', command=self.copy_orders_to_clipboard)
        btn_copy.pack(side='right')

        # 2. KPI 상태 요약 대시보드 카드 영역
        kpi_frame = ttk.Frame(self, style='TFrame')
        kpi_frame.pack(fill='x', padx=16, pady=6)

        # 4개의 상태 카드 (모드/최근종가, 현금/보유량, 총자산, 전략핵심변수)
        self.card_mode = self._create_kpi_card(kpi_frame, "시장 모드 / 상태", "-", "종가: -")
        self.card_cash = self._create_kpi_card(kpi_frame, "보유 현금 / 수량", "-", "보유수량: -")
        self.card_asset = self._create_kpi_card(kpi_frame, "현재 총 평가자산", "-", "기준일자: -")
        self.card_metric = self._create_kpi_card(kpi_frame, "시드(AR) / 위기준비(AK)", "-", "1회 매수예산: -")

        self.card_mode.pack(side='left', fill='both', expand=True, padx=(0, 6))
        self.card_cash.pack(side='left', fill='both', expand=True, padx=6)
        self.card_asset.pack(side='left', fill='both', expand=True, padx=6)
        self.card_metric.pack(side='left', fill='both', expand=True, padx=(6, 0))

        # 3. 중간 분할 영역 (상단: 오늘의 매도 주문 / 하단: 오늘의 매수 주문)
        content_frame = ttk.Frame(self, style='TFrame')
        content_frame.pack(fill='both', expand=True, padx=16, pady=(8, 16))

        # (1) 매도 주문표 카드
        sell_frame = ttk.LabelFrame(content_frame, text="🔴 오늘의 매도 주문 (Target Sell Orders)", padding=10)
        sell_frame.pack(fill='x', pady=(0, 8))

        sell_cols = ('구분', '주문유형', '주문단가', '주문수량', '예상금액', '체결조건')
        self.tree_sell = ttk.Treeview(sell_frame, columns=sell_cols, show='headings', height=3)
        for col in sell_cols:
            self.tree_sell.heading(col, text=col)
            width = 160 if col in ('구분', '체결조건') else 100
            self.tree_sell.column(col, width=width, anchor='center')
        self.tree_sell.pack(fill='x')

        # (2) 매수 주문표 카드
        buy_frame = ttk.LabelFrame(content_frame, text="🟢 오늘의 분할 매수 주문 (Tiered LOC Buy Orders)", padding=10)
        buy_frame.pack(fill='both', expand=True, pady=(4, 0))

        buy_cols = ('호가단계', '주문유형', '주문단가', '주문수량', '누적수량', '예상금액', '체결조건')
        self.tree_buy = ttk.Treeview(buy_frame, columns=buy_cols, show='headings', height=6)
        for col in buy_cols:
            self.tree_buy.heading(col, text=col)
            width = 180 if col == '체결조건' else 110
            self.tree_buy.column(col, width=width, anchor='center')

        scroll_buy = ttk.Scrollbar(buy_frame, orient='vertical', command=self.tree_buy.yview)
        self.tree_buy.configure(yscrollcommand=scroll_buy.set)
        self.tree_buy.pack(side='left', fill='both', expand=True)
        scroll_buy.pack(side='right', fill='y')

    def _create_kpi_card(self, parent, title, main_val, sub_val):
        frame = ttk.Frame(parent, style='Card.TFrame', padding=(14, 10))
        lbl_title = ttk.Label(frame, text=title, style='KPILbl.TLabel')
        lbl_title.pack(anchor='w')

        lbl_main = ttk.Label(frame, text=main_val, style='KPIVal.TLabel')
        lbl_main.pack(anchor='w', pady=(2, 2))

        lbl_sub = ttk.Label(frame, text=sub_val, style='CardMuted.TLabel')
        lbl_sub.pack(anchor='w')

        frame.lbl_title = lbl_title
        frame.lbl_main = lbl_main
        frame.lbl_sub = lbl_sub
        return frame

    def refresh_orders(self):
        strat_choice = self.combo_strat.get()
        ticker = self.combo_ticker.get()
        try:
            capital = float(self.entry_capital.get().replace(',', '').strip())
        except ValueError:
            capital = 200000.0

        # 시세 데이터 획득
        df_market = self.get_market_data_func(ticker)
        if df_market is None or len(df_market) == 0:
            messagebox.showwarning("데이터 오류", f"[{ticker}] 시세 데이터를 가져올 수 없습니다.")
            return

        if strat_choice == '종종이 기본전략':
            data = get_jongjong_today_orders(df_market, initial_capital=capital)
            self._update_ui_jongjong(data, ticker)
        else:
            data = get_infinite_buying_today_orders(df_market, ticker=ticker, initial_capital=capital)
            self._update_ui_infinite(data, ticker)

        self.current_orders_data = data

    def _update_ui_jongjong(self, data, ticker):
        mode = data['current_mode']
        mode_color = COLORS['accent_green'] if mode == 'Normal' else (COLORS['accent_yellow'] if mode == 'Safe' else COLORS['accent_orange'])

        self.card_mode.lbl_main.config(text=f"{mode} 모드", foreground=mode_color)
        self.card_mode.lbl_sub.config(text=f"최근종가: ${data['latest_close']:.2f}")

        self.card_cash.lbl_main.config(text=f"${data['cash']:,.0f}", foreground=COLORS['text_white'])
        self.card_cash.lbl_sub.config(text=f"보유수량: {data['hold_shares']:,}주")

        self.card_asset.lbl_main.config(text=f"${data['asset']:,.0f}", foreground=COLORS['accent_blue'])
        self.card_asset.lbl_sub.config(text=f"기준일자: {data['latest_date']}")

        self.card_metric.lbl_title.config(text="시드(AR) / 위기준비(AK)")
        self.card_metric.lbl_main.config(text=f"${data['ar_val']:,.0f} / ${data['ak_val']:,.0f}", foreground=COLORS['accent_purple'])
        self.card_metric.lbl_sub.config(text=f"1회 매수예산: ${data['p_budget']:,.2f}")

        # 매도 주문 업데이트
        self.tree_sell.delete(*self.tree_sell.get_children())
        if len(data['sell_orders']) == 0:
            self.tree_sell.insert('', 'end', values=('보유 없음', '-', '-', '-', '-', '현재 매도할 보유 수량이 없습니다.'))
        else:
            for s in data['sell_orders']:
                self.tree_sell.insert('', 'end', values=(s['구분'], s['주문유형'], s['주문단가'], s['주문수량'], s['예상금액'], s['체결조건']))

        # 매수 주문 업데이트
        self.tree_buy.delete(*self.tree_buy.get_children())
        if len(data['buy_orders']) == 0:
            self.tree_buy.insert('', 'end', values=('-', '-', '-', '-', '-', '-', '오늘 실행할 매수 주문이 없습니다.'))
        else:
            for b in data['buy_orders']:
                self.tree_buy.insert('', 'end', values=(b['호가단계'], b['주문유형'], b['주문단가'], b['주문수량'], b['누적수량'], b['예상금액'], b['체결조건']))

    def _update_ui_infinite(self, data, ticker):
        mode = data['current_mode']
        mode_text = "일반모드 (Normal)" if mode == 'NORMAL' else "소진후 리버스모드 (Reverse)"
        mode_color = COLORS['accent_green'] if mode == 'NORMAL' else COLORS['accent_red']

        self.card_mode.lbl_main.config(text=mode_text, foreground=mode_color)
        self.card_mode.lbl_sub.config(text=f"최근종가: ${data['latest_close']:.2f}")

        self.card_cash.lbl_main.config(text=f"${data['cash']:,.0f}", foreground=COLORS['text_white'])
        self.card_cash.lbl_sub.config(text=f"보유: {data['hold_shares']:,}주 (평단: ${data['avg_price']:.2f})")

        self.card_asset.lbl_main.config(text=f"${data['asset']:,.0f}", foreground=COLORS['accent_blue'])
        self.card_asset.lbl_sub.config(text=f"기준일자: {data['latest_date']}")

        self.card_metric.lbl_title.config(text="진행 회차 (Turn T)")
        self.card_metric.lbl_main.config(text=f"T = {data['T']:.4f}", foreground=COLORS['accent_cyan'])
        self.card_metric.lbl_sub.config(text="소진 한도: T > 39")

        # 매도 주문
        self.tree_sell.delete(*self.tree_sell.get_children())
        if len(data['sell_orders']) == 0:
            self.tree_sell.insert('', 'end', values=('보유 없음', '-', '-', '-', '-', '현재 매도할 보유 수량이 없습니다.'))
        else:
            for s in data['sell_orders']:
                self.tree_sell.insert('', 'end', values=(s['구분'], s['주문유형'], s['주문단가'], s['주문수량'], s['예상금액'], s['체결조건']))

        # 매수 주문
        self.tree_buy.delete(*self.tree_buy.get_children())
        if len(data['buy_orders']) == 0:
            self.tree_buy.insert('', 'end', values=('-', '-', '-', '-', '-', '-', '오늘 실행할 매수 주문이 없습니다.'))
        else:
            for b in data['buy_orders']:
                self.tree_buy.insert('', 'end', values=(b['호가단계'], b['주문유형'], b['주문단가'], b['주문수량'], b['누적수량'], b['예상금액'], b['체결조건']))

    def copy_orders_to_clipboard(self):
        if not self.current_orders_data:
            messagebox.showinfo("알림", "복사할 주문 데이터가 없습니다. 먼저 새로고침을 실행하세요.")
            return

        d = self.current_orders_data
        strat = d['strategy_name']
        ticker = self.combo_ticker.get()

        lines = [
            f"=== 📌 오늘의 주식 매매 LOC 주문표 ({ticker}) ===",
            f"• 적용 전략: {strat}",
            f"• 기준 일자: {d['latest_date']} (최근 종가: ${d['latest_close']:.2f})",
            f"• 현재 모드: {d.get('current_mode', '-')}",
            f"• 보유 현금: ${d['cash']:,.2f} / 보유 수량: {d['hold_shares']:,}주",
            "",
            "[1. 매도 주문 (Sell)]"
        ]

        if not d['sell_orders']:
            lines.append("  (매도 주문 없음)")
        else:
            for s in d['sell_orders']:
                lines.append(f"  • [{s['주문유형']}] {s['구분']} - 단가: {s['주문단가']} / 수량: {s['주문수량']} ({s['체결조건']})")

        lines.append("")
        lines.append("[2. 매수 주문 (Buy)]")
        if not d['buy_orders']:
            lines.append("  (매수 주문 없음)")
        else:
            for b in d['buy_orders']:
                lines.append(f"  • [{b['주문유형']}] {b['호가단계']} - 단가: {b['주문단가']} / 수량: {b['주문수량']} ({b['체결조건']})")

        text = "\n".join(lines)
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("클립보드 복사 완료", f"오늘의 [{ticker}] 매수/매도 주문표가 클립보드에 복사되었습니다!\nMTS나 HTS에 붙여넣기 하세요.")
