"""
메인 GUI 윈도우 모듈 (Main Window)
종종이 및 무한매수법 대시보드의 메인 프레임과 탭 컨테이너를 관리합니다.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from datetime import datetime

from gui.theme import COLORS, FONTS, apply_theme
from gui.tabs.accounts_tab import AccountsTab
from gui.tabs.backtest_tab import BacktestTab
from core.data import fetch_market_data


class TradingAppWindow:
    """
    종종이 & 무한매수법 자동매매 시스템 메인 윈도우
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("종종이 & 무한매수 주식 매매 시스템 (JongJong & Infinite Buying)")
        self.root.geometry("1280x880")
        self.root.minsize(1050, 720)

        # 시장 데이터 메모리 캐시 (티커별 캐싱)
        self.data_cache = {}

        # 테마 적용
        apply_theme(self.root)

        self._build_header()
        self._build_notebook()
        self._build_statusbar()

        # 최초 실행 시 계좌 목록 로드
        self.root.after(100, self._initial_load)

    def get_market_data(self, ticker: str, start_date: str = '2018-01-01', end_date: str = None) -> pd.DataFrame:
        """
        메모리 캐싱을 지원하는 시세 데이터 제공 함수
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        cache_key = f"{ticker}_{start_date}_{end_date}"
        if cache_key not in self.data_cache:
            self.set_status(f"[{ticker}] 시세 데이터 수집 중...")
            self.root.update_idletasks()
            df = fetch_market_data(ticker, start_date, end_date)
            self.data_cache[cache_key] = df
            self.set_status(f"[{ticker}] 시세 데이터 로드 완료 ({len(df)}거래일)")
        return self.data_cache[cache_key]

    def _build_header(self):
        header = ttk.Frame(self.root, style='Card.TFrame', padding=(20, 12))
        header.pack(fill='x', side='top')

        left_box = ttk.Frame(header, style='Card.TFrame')
        left_box.pack(side='left')

        lbl_title = ttk.Label(left_box, text="⚡ 종종이 & 무한매수 자동매매 시스템", style='Title.TLabel')
        lbl_title.pack(anchor='w')

        lbl_sub = ttk.Label(left_box, text="JongJong Multi-Mode LOC Trading & Infinite Buying Method v4.0", style='CardMuted.TLabel')
        lbl_sub.pack(anchor='w', pady=(2, 0))

        right_box = ttk.Frame(header, style='Card.TFrame')
        right_box.pack(side='right')

        now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        lbl_time = ttk.Label(right_box, text=f"시스템 시간: {now_str}", style='CardMuted.TLabel')
        lbl_time.pack(anchor='e')

        lbl_badge = ttk.Label(right_box, text="● 엔진 가동 중 (ONLINE)", style='Card.TLabel', foreground=COLORS['accent_green'], font=FONTS['caption'])
        lbl_badge.pack(anchor='e', pady=(2, 0))

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=12, pady=8)

        # Tab 1: 계좌 관리 및 실매매 대시보드
        self.tab_accounts = AccountsTab(self.notebook, self.get_market_data)
        self.notebook.add(self.tab_accounts, text="  💼 내 투자 계좌 관리 및 실매매 (Accounts & Live)  ")

        # Tab 2: 백테스트 분석기
        self.tab_backtest = BacktestTab(self.notebook, self.get_market_data)
        self.notebook.add(self.tab_backtest, text="  📊 백테스트 시뮬레이터 (Backtest Simulator)  ")

    def _build_statusbar(self):
        status_bar = ttk.Frame(self.root, style='CardAlt.TFrame', padding=(16, 6))
        status_bar.pack(fill='x', side='bottom')

        self.lbl_status = ttk.Label(status_bar, text="시스템 준비 완료", style='TLabel', font=FONTS['caption'])
        self.lbl_status.pack(side='left')

        lbl_info = ttk.Label(status_bar, text="버전 1.1.0 (계좌 관리 및 입출금 지원) | 라오어 무한매수 v4.0 & 종종이 전략", style='TLabel', foreground=COLORS['text_muted'], font=FONTS['caption'])
        lbl_info.pack(side='right')

    def set_status(self, msg: str):
        self.lbl_status.config(text=msg)

    def _initial_load(self):
        try:
            self.tab_accounts.reload_accounts()
        except Exception as e:
            print(f"초기 로드 중 경고: {e}")

