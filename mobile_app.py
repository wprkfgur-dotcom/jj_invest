"""
=====================================================================
종종이 & 무한매수 주식 매매 시스템 - 모바일/안드로이드 앱 (Flet)
=====================================================================
구조:
  1. 하단 3대 탭: [홈] / [계좌 현황] / [백테스트]
  2. [홈]: 전체 등록 계좌의 자산 현황 합산 대시보드 + 포트폴리오 자산 추이 그래프
  3. [계좌 현황]: 등록 계좌 카드 리스트 + 우측 하단 '+' 신규 계좌 등록 FAB
  4. [계좌 상세]: 계좌 기본 정보, 매입 조각별 상세(수량/매입가/손실률), 금일 매수매도표, 정산 및 거래내역
  5. [백테스트]: 종목/전략/기간별 시뮬레이션 실행 및 성과 지표/비교 차트
"""
import sys
import os
import io
import base64
import subprocess
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# UTF-8 출력 보장
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 모듈 탐색 경로
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import flet as ft
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from gui.account_manager import AccountManager
from core.data import fetch_market_data
from core.metrics import calculate_metrics
from strategies.jongjong import JongJongStrategy
from strategies.infinite_buying_v4 import InfiniteBuyingV4Strategy
from strategies.buy_and_hold import BuyAndHoldStrategy


# =====================================================================
# 색상 테마 및 디자인 상수
# =====================================================================
BG_DARK = "#0B0F19"           # 전체 배경 (딥 다크)
SURFACE_CARD = "#151C2C"      # 카드 배경
SURFACE_CONTAINER = "#1E293B" # 입력 필드 / 하위 컨테이너 배경
BORDER_COLOR = "#243049"      # 구분선 및 카드 테두리
ACCENT_BLUE = "#38BDF8"       # 메인 강조 하늘색
PROFIT_GREEN = "#10B981"      # 수익/매수 에메랄드 그린
LOSS_RED = "#F43F5E"          # 손실/매도 로즈 레드
RESERVE_AMBER = "#F59E0B"     # 위기준비금 앰버
TEXT_PRIMARY = "#F8FAFC"      # 본문 화이트
TEXT_SECONDARY = "#94A3B8"    # 보조 텍스트 (그레이)
TEXT_MUTED = "#64748B"

EXCHANGE_RATE = 1380.0        # USD/KRW 환율 기준


def copy_text_to_clipboard(page: ft.Page, text: str):
    """
    Windows 및 모바일(Android) 환경 모두에서 안전하게 클립보드에 텍스트를 복사합니다.
    """
    try:
        cb = ft.Clipboard()
        if cb not in page.overlay:
            page.overlay.append(cb)
            page.update()
        cb.set(text)
    except Exception:
        pass

    if sys.platform == "win32":
        try:
            subprocess.run(["clip.exe"], input=text.encode("utf-16"), check=True)
        except Exception:
            pass


def show_toast(page: ft.Page, message: str, is_error: bool = False):
    """
    모바일 플로팅 토스트 알림을 표시합니다.
    """
    sb = ft.SnackBar(
        content=ft.Row(
            controls=[
                ft.Icon(
                    ft.Icons.ERROR_OUTLINE if is_error else ft.Icons.CHECK_CIRCLE_OUTLINE,
                    color=ft.Colors.WHITE,
                    size=20
                ),
                ft.Text(message, color=ft.Colors.WHITE, size=13, weight=ft.FontWeight.W_500, expand=True),
            ],
            spacing=8
        ),
        bgcolor=LOSS_RED if is_error else PROFIT_GREEN,
        open=True,
        duration=2500,
        behavior=ft.SnackBarBehavior.FLOATING,
        margin=ft.Margin.all(12)
    )
    page.overlay.append(sb)
    page.update()


def get_current_stock_price(ticker: str, fallback_price: float = 0.0) -> float:
    """
    야후 파이낸스에서 실시간 또는 최근 종가를 신속하게 조회합니다.
    조회 실패 시 fallback_price를 반환합니다.
    """
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        fi = t.fast_info
        p = fi.get('lastPrice') or fi.get('regularMarketPrice') or fi.get('previousClose')
        if p is not None and float(p) > 0:
            return round(float(p), 2)
    except Exception as ex:
        print(f"[{ticker}] 실시간 시세 조회 안내: {ex}")

    return round(float(fallback_price), 2) if fallback_price > 0 else 142.50


def compute_suggested_trades(close_p: float, buy_orders: list, sell_orders: list):
    """
    종가(close_p)를 기준으로 LOC 매수 및 매도 체결 가능 수량을 산출합니다.
    - 매수: 종가 <= LOC 주문단가인 주문들의 수량 합산
    - 매도: 종가 >= LOC 주문단가인 주문들의 수량 합산
    """
    calc_buy_q = 0
    calc_sell_q = 0

    for b in buy_orders:
        bp = b.get('price')
        if bp is None:
            raw_p = str(b.get('주문단가', '0')).replace('$', '').replace(',', '').strip()
            bp = float(raw_p) if raw_p else 0.0
        bq = b.get('qty')
        if bq is None:
            raw_q = str(b.get('주문수량', '0')).replace('주', '').replace(',', '').strip()
            bq = int(raw_q) if raw_q else 0
        if bp > 0 and bq > 0 and close_p <= bp + 1e-4:
            calc_buy_q += bq

    for s in sell_orders:
        sp = s.get('price')
        if sp is None:
            raw_p = str(s.get('주문단가', '0')).replace('$', '').replace(',', '').strip()
            sp = float(raw_p) if raw_p else 0.0
        sq = s.get('qty')
        if sq is None:
            raw_q = str(s.get('주문수량', '0')).replace('주', '').replace(',', '').strip()
            sq = int(raw_q) if raw_q else 0
        if sp > 0 and sq > 0 and close_p >= sp - 1e-4:
            calc_sell_q += sq

    return calc_buy_q, calc_sell_q


# =====================================================================
# 차트 렌더링 헬퍼 (Matplotlib Base64 이미지 변환)
# =====================================================================
def render_portfolio_chart(accounts_data: list, total_portfolio_asset: float) -> str:
    """
    전체 계좌의 통합 자산 추이 그래프를 생성하여 base64 URI로 반환합니다.
    """
    fig, ax = plt.subplots(figsize=(5.2, 2.5), facecolor=SURFACE_CARD)
    ax.set_facecolor(SURFACE_CARD)

    all_series = []
    for d in accounts_data:
        df = d.get('df_res')
        if df is not None and not df.empty and 'Asset' in df.columns:
            s = df.set_index('Date')['Asset']
            all_series.append(s)

    if all_series:
        combined_df = pd.concat(all_series, axis=1).ffill().fillna(0.0)
        total_series = combined_df.sum(axis=1)
        x_vals = total_series.index
        y_vals = total_series.values
    else:
        # 기록이 아직 없는 신규 운용 시작 시
        dates = pd.date_range(end=datetime.now(), periods=5)
        x_vals = dates
        y_vals = [total_portfolio_asset] * 5

    ax.plot(x_vals, y_vals, color=ACCENT_BLUE, linewidth=2.2, label='통합 자산')
    min_y = min(y_vals) if len(y_vals) > 0 else 0.0
    ax.fill_between(x_vals, y_vals, min_y * 0.98, color=ACCENT_BLUE, alpha=0.15)

    ax.tick_params(colors=TEXT_SECONDARY, labelsize=8)
    for spine in ax.spines.values():
        spine.set_color(BORDER_COLOR)
    ax.grid(True, linestyle='--', alpha=0.2, color=TEXT_SECONDARY)
    fig.autofmt_xdate(rotation=20)

    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode('utf-8')
    return f"data:image/png;base64,{b64}"


def render_backtest_chart(df_strat: pd.DataFrame, df_bnh: pd.DataFrame, strat_name: str, ticker: str) -> str:
    """
    백테스트 결과(전략 vs 단순보유) 자산 비교 차트를 생성하여 base64 URI로 반환합니다.
    """
    fig, ax = plt.subplots(figsize=(5.2, 2.7), facecolor=SURFACE_CARD)
    ax.set_facecolor(SURFACE_CARD)

    dates = pd.to_datetime(df_strat['Date'])
    strat_assets = df_strat['Asset'].values
    ax.plot(dates, strat_assets, color=PROFIT_GREEN, linewidth=2.0, label=strat_name)

    if df_bnh is not None and not df_bnh.empty:
        bnh_dates = pd.to_datetime(df_bnh['Date'])
        bnh_assets = df_bnh['Asset'].values
        ax.plot(bnh_dates, bnh_assets, color=TEXT_SECONDARY, linewidth=1.4, linestyle='--', label=f'{ticker} 단순보유')

    ax.tick_params(colors=TEXT_SECONDARY, labelsize=8)
    for spine in ax.spines.values():
        spine.set_color(BORDER_COLOR)
    ax.grid(True, linestyle='--', alpha=0.2, color=TEXT_SECONDARY)
    ax.legend(facecolor=SURFACE_CARD, edgecolor=BORDER_COLOR, labelcolor=TEXT_PRIMARY, fontsize=8, loc='upper left')
    fig.autofmt_xdate(rotation=20)

    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode('utf-8')
    return f"data:image/png;base64,{b64}"


# =====================================================================
# 메인 애플리케이션 클래스
# =====================================================================
class MobileTradingApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.am = AccountManager()
        self.accounts = []
        self.accounts_details = []
        self.current_tab_index = 0       # 0: 홈, 1: 계좌 현황, 2: 백테스트
        self.viewing_account_id = None    # None이면 3대 탭 표시, 특정 ID면 계좌 상세 화면 표시

        # 백테스트 상태 저장용
        self.bt_results = None
        self.bt_is_loading = False

        # Flet 기본 창 설정 (스마트폰 크기 및 테마)
        self.page.title = "종종 투자 (JongJong Mobile)"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = BG_DARK
        self.page.padding = 0

        # 데스크톱 실행 시 안드로이드 폰 비율로 크기 고정
        if hasattr(self.page, "window"):
            self.page.window.width = 412
            self.page.window.height = 860
            self.page.window.resizable = True
            self.page.window.min_width = 360
            self.page.window.min_height = 600

        # 메인 컨텐츠 컨테이너
        self.content_container = ft.Container(
            expand=True,
            padding=ft.Padding.only(left=12, right=12, top=8, bottom=8)
        )

        # 상단 네비게이션 & 하단 네비게이션
        self._setup_app_bar()
        self._setup_bottom_nav()

        # 데이터 로드
        self.reload_data()

    def _setup_app_bar(self):
        self.title_text = ft.Text("종종 투자 포트폴리오", size=16, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
        self.subtitle_text = ft.Text("전체 계좌 통합 자산", size=11, color=TEXT_SECONDARY)

        self.leading_icon = ft.Container(
            content=ft.Icon(ft.Icons.SAVINGS_OUTLINED, color=ACCENT_BLUE, size=22),
            padding=ft.Padding.only(left=12)
        )

        self.action_buttons = [
            ft.IconButton(
                icon=ft.Icons.REFRESH_ROUNDED,
                icon_color=TEXT_SECONDARY,
                tooltip="새로고침",
                on_click=lambda e: self.reload_data(show_message=True)
            )
        ]

        self.page.appbar = ft.AppBar(
            leading=self.leading_icon,
            title=ft.Column(
                controls=[self.title_text, self.subtitle_text],
                spacing=1,
                alignment=ft.MainAxisAlignment.CENTER
            ),
            actions=self.action_buttons,
            bgcolor=SURFACE_CARD,
            elevation=2
        )

    def _setup_bottom_nav(self):
        self.bottom_nav = ft.NavigationBar(
            selected_index=0,
            bgcolor=SURFACE_CARD,
            indicator_color=ft.Colors.with_opacity(0.2, ACCENT_BLUE),
            destinations=[
                ft.NavigationBarDestination(
                    icon=ft.Icons.HOME_OUTLINED,
                    selected_icon=ft.Icons.HOME_ROUNDED,
                    label="홈"
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
                    selected_icon=ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED,
                    label="계좌 현황"
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.ANALYTICS_OUTLINED,
                    selected_icon=ft.Icons.ANALYTICS_ROUNDED,
                    label="백테스트"
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED,
                    selected_icon=ft.Icons.SETTINGS_ROUNDED,
                    label="설정"
                ),
            ],
            on_change=self.on_nav_change
        )
        self.page.navigation_bar = self.bottom_nav

    def reload_data(self, show_message: bool = False):
        """
        모든 계좌 및 각 계좌별 상세 연산을 재실행합니다.
        """
        self.accounts = self.am.load_accounts()
        self.accounts_details = []

        for acc in self.accounts:
            try:
                dtl = self.am.compute_account_details(acc)
                self.accounts_details.append(dtl)
            except Exception as ex:
                print(f"계좌({acc.get('name')}) 연산 오류: {ex}")

        self._render_current_view()

        if show_message:
            show_toast(self.page, "데이터가 새로고침되었습니다.")

    def on_nav_change(self, e):
        self.current_tab_index = e.control.selected_index
        self.viewing_account_id = None  # 탭 이동 시 상세 화면 탈출
        self._render_current_view()

    def open_account_detail(self, account_id: str):
        """
        특정 계좌의 상세 페이지로 전환합니다.
        """
        self.viewing_account_id = account_id
        self._render_current_view()

    def back_to_accounts(self, e=None):
        """
        계좌 상세 페이지에서 다시 계좌 목록으로 복귀합니다.
        """
        self.viewing_account_id = None
        self._render_current_view()

    def _render_current_view(self):
        # 1. 상세 페이지 모드인 경우
        if self.viewing_account_id:
            target_acc = next((a for a in self.accounts if a['id'] == self.viewing_account_id), None)
            target_dtl = next((d for d in self.accounts_details if d.get('account_id') == self.viewing_account_id), None)

            if target_acc and target_dtl:
                self._update_appbar_for_detail(target_acc)
                self.page.floating_action_button = None
                self.content_container.content = self._build_account_detail_view(target_acc, target_dtl)
                self.page.update()
                return

        # 2. 메인 탭 모드인 경우
        self._update_appbar_for_tabs()

        if self.current_tab_index == 0:
            self.page.floating_action_button = None
            self.content_container.content = self._build_home_tab()
        elif self.current_tab_index == 1:
            # 계좌 현황 탭: 우측 하단 단일 '+' 원형 FAB 활성화
            self.page.floating_action_button = ft.FloatingActionButton(
                icon=ft.Icons.ADD,
                shape=ft.CircleBorder(),
                bgcolor=ACCENT_BLUE,
                foreground_color=ft.Colors.BLACK,
                tooltip="새 계좌 추가",
                on_click=self.open_add_account_dialog
            )
            self.content_container.content = self._build_accounts_tab()
        elif self.current_tab_index == 2:
            self.page.floating_action_button = None
            self.content_container.content = self._build_backtest_tab()
        elif self.current_tab_index == 3:
            self.page.floating_action_button = None
            self.content_container.content = self._build_settings_tab()

        self.page.update()

    def _update_appbar_for_tabs(self):
        if self.current_tab_index == 0:
            self.title_text.value = "종종 투자 포트폴리오"
            self.subtitle_text.value = "전체 계좌 통합 자산 현황"
            self.leading_icon.content = ft.Icon(ft.Icons.SAVINGS_OUTLINED, color=ACCENT_BLUE, size=22)
        elif self.current_tab_index == 1:
            self.title_text.value = "계좌 현황"
            self.subtitle_text.value = f"총 {len(self.accounts)}개 계좌 운용 중"
            self.leading_icon.content = ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, color=ACCENT_BLUE, size=22)
        elif self.current_tab_index == 2:
            self.title_text.value = "전략 백테스트"
            self.subtitle_text.value = "시뮬레이션 및 성과 검증"
            self.leading_icon.content = ft.Icon(ft.Icons.ANALYTICS_OUTLINED, color=ACCENT_BLUE, size=22)
        elif self.current_tab_index == 3:
            self.title_text.value = "환경 설정"
            self.subtitle_text.value = "데이터 내보내기 및 시스템 설정"
            self.leading_icon.content = ft.Icon(ft.Icons.SETTINGS_OUTLINED, color=ACCENT_BLUE, size=22)

        self.page.appbar.leading = self.leading_icon
        self.page.appbar.actions = [
            ft.IconButton(
                icon=ft.Icons.REFRESH_ROUNDED,
                icon_color=TEXT_SECONDARY,
                tooltip="새로고침",
                on_click=lambda e: self.reload_data(show_message=True)
            )
        ]

    def _update_appbar_for_detail(self, target_acc: dict):
        acc_name = target_acc.get('name', '계좌')
        ticker = target_acc.get('ticker', 'SOXL')
        strat = target_acc.get('strategy', '종종이 기본전략')

        self.title_text.value = f"{acc_name} ({ticker})"
        self.subtitle_text.value = strat

        # 뒤로가기 버튼
        self.page.appbar.leading = ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            icon_color=TEXT_PRIMARY,
            tooltip="계좌 목록으로",
            on_click=self.back_to_accounts
        )
        self.page.appbar.actions = [
            ft.IconButton(
                icon=ft.Icons.SETTINGS_OUTLINED,
                icon_color=TEXT_SECONDARY,
                tooltip="계좌 설정",
                on_click=lambda e, aid=target_acc['id']: self.open_settings_dialog(aid)
            ),
            ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE,
                icon_color=LOSS_RED,
                tooltip="계좌 삭제",
                on_click=lambda e, aid=target_acc['id']: self.open_delete_account_dialog(aid)
            ),
            ft.IconButton(
                icon=ft.Icons.REFRESH_ROUNDED,
                icon_color=TEXT_SECONDARY,
                tooltip="새로고침",
                on_click=lambda e: self.reload_data(show_message=True)
            )
        ]

    # =================================================================
    # TAB 0: 🏠 홈 (전체 통합 자산 현황 & 포트폴리오 그래프)
    # =================================================================
    def _build_home_tab(self):
        if not self.accounts:
            return self._build_empty_home_view()

        # 전체 계좌 합산 지표 산출
        tot_asset = sum(d.get('current_asset', 0.0) for d in self.accounts_details)
        tot_seed = sum(d.get('initial_seed', 0.0) for d in self.accounts_details)
        tot_profit = sum(d.get('total_profit', 0.0) for d in self.accounts_details)
        tot_return_pct = (tot_profit / tot_seed * 100.0) if tot_seed > 0 else 0.0

        tot_cash = sum(d.get('current_cash', 0.0) for d in self.accounts_details)
        tot_ak = sum(d.get('ak_val', 0.0) for d in self.accounts_details)
        tot_ar = sum(d.get('ar_val', 0.0) for d in self.accounts_details)
        tot_stock_val = max(0.0, tot_asset - tot_cash)

        krw_asset = tot_asset * EXCHANGE_RATE
        is_profit = tot_profit >= 0
        p_color = PROFIT_GREEN if is_profit else LOSS_RED
        p_icon = ft.Icons.ARROW_DROP_UP if is_profit else ft.Icons.ARROW_DROP_DOWN

        # 1. 통합 자산 히어로 카드
        hero_card = ft.Card(
            bgcolor=SURFACE_CARD,
            elevation=3,
            shape=ft.RoundedRectangleBorder(radius=16),
            content=ft.Container(
                padding=18,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Text("전체 계좌 통합 평가 자산", size=13, color=TEXT_SECONDARY, weight=ft.FontWeight.W_500),
                                ft.Container(
                                    content=ft.Text(f"총 {len(self.accounts)}개 계좌", size=11, color=ACCENT_BLUE, weight=ft.FontWeight.BOLD),
                                    bgcolor=ft.Colors.with_opacity(0.15, ACCENT_BLUE),
                                    padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                                    border_radius=10
                                )
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        ft.Container(height=4),
                        ft.Text(f"${tot_asset:,.2f}", size=32, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        ft.Text(f"약 {krw_asset:,.0f}원 (환율 {EXCHANGE_RATE:,.0f}원)", size=12, color=TEXT_MUTED),
                        ft.Container(height=8),
                        ft.Divider(color=BORDER_COLOR, height=1),
                        ft.Container(height=4),
                        ft.Row(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Icon(p_icon, color=p_color, size=20),
                                        ft.Text(f"{tot_return_pct:+.2f}%", size=14, weight=ft.FontWeight.BOLD, color=p_color),
                                        ft.Text(f"({tot_profit:+,.2f}달러)", size=12, color=p_color),
                                    ],
                                    spacing=2
                                ),
                                ft.Text(f"총 원금: ${tot_seed:,.0f}", size=12, color=TEXT_SECONDARY)
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        )
                    ]
                )
            )
        )

        # 2. 통합 자산 추이 그래프
        chart_base64 = render_portfolio_chart(self.accounts_details, tot_asset)
        chart_card = ft.Card(
            bgcolor=SURFACE_CARD,
            elevation=2,
            shape=ft.RoundedRectangleBorder(radius=14),
            content=ft.Container(
                padding=14,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.SHOW_CHART, size=18, color=ACCENT_BLUE),
                                ft.Text("포트폴리오 자산 성장 추이", size=13, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                            ],
                            spacing=6
                        ),
                        ft.Container(height=4),
                        ft.Image(src=chart_base64, fit="contain", border_radius=8),
                    ]
                )
            )
        )

        # 3. 4대 종합 지표 그리드
        def make_metric_card(title, value, subtext, icon, icon_color):
            return ft.Container(
                bgcolor=SURFACE_CARD,
                border=ft.Border.all(1, BORDER_COLOR),
                border_radius=12,
                padding=12,
                expand=True,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Text(title, size=11, color=TEXT_SECONDARY, weight=ft.FontWeight.W_500),
                                ft.Icon(icon, size=16, color=icon_color)
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        ft.Container(height=2),
                        ft.Text(value, size=15, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        ft.Text(subtext, size=10, color=TEXT_MUTED)
                    ],
                    spacing=1
                )
            )

        row1 = ft.Row(
            controls=[
                make_metric_card("총 예수금 (Cash)", f"${tot_cash:,.0f}", "현금 보유액", ft.Icons.ATTACH_MONEY, PROFIT_GREEN),
                make_metric_card("주식 평가액", f"${tot_stock_val:,.0f}", "보유 주식 총액", ft.Icons.PIE_CHART_OUTLINE, ft.Colors.PURPLE_300),
            ],
            spacing=8
        )

        row2 = ft.Row(
            controls=[
                make_metric_card("총 위기준비금 (AK)", f"${tot_ak:,.0f}", "폭락 안전 준비금", ft.Icons.SHIELD_OUTLINED, RESERVE_AMBER),
                make_metric_card("총 실가동 시드 (AR)", f"${tot_ar:,.0f}", "분할 운용 시드", ft.Icons.ROCKET_LAUNCH_OUTLINED, ACCENT_BLUE),
            ],
            spacing=8
        )

        # 4. 운용 계좌별 비중 요약 리스트
        acc_summary_items = []
        for d in self.accounts_details:
            name = d.get('account_name', '')
            ticker = d.get('ticker', '')
            asset = d.get('current_asset', 0.0)
            ret_pct = d.get('total_return_pct', 0.0)
            ratio = (asset / tot_asset * 100.0) if tot_asset > 0 else 0.0
            r_color = PROFIT_GREEN if ret_pct >= 0 else LOSS_RED

            item = ft.Container(
                bgcolor=SURFACE_CARD,
                border=ft.Border.all(1, BORDER_COLOR),
                border_radius=10,
                padding=12,
                on_click=lambda e, aid=d.get('account_id'): self.open_account_detail(aid),
                content=ft.Row(
                    controls=[
                        ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Text(name, size=13, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                                        ft.Container(
                                            content=ft.Text(ticker, size=10, color=ACCENT_BLUE),
                                            bgcolor=ft.Colors.with_opacity(0.15, ACCENT_BLUE),
                                            padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                            border_radius=4
                                        )
                                    ],
                                    spacing=6
                                ),
                                ft.Text(f"포트폴리오 비중: {ratio:.1f}%", size=11, color=TEXT_MUTED)
                            ],
                            spacing=2,
                            expand=True
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(f"${asset:,.2f}", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                                ft.Text(f"{ret_pct:+.2f}%", size=11, weight=ft.FontWeight.BOLD, color=r_color)
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.END,
                            spacing=1
                        ),
                        ft.Icon(ft.Icons.CHEVRON_RIGHT, color=TEXT_MUTED, size=20)
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                )
            )
            acc_summary_items.append(item)

        return ft.ListView(
            controls=[
                hero_card,
                ft.Container(height=6),
                chart_card,
                ft.Container(height=6),
                row1,
                row2,
                ft.Container(height=8),
                ft.Row(
                    controls=[
                        ft.Text("계좌별 자산 및 비중", size=13, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        ft.TextButton("전체 보기", on_click=lambda _: self._goto_tab(1))
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                *acc_summary_items,
                ft.Container(height=20)
            ],
            spacing=8,
            expand=True
        )

    def _build_empty_home_view(self):
        return ft.Column(
            controls=[
                ft.Container(height=80),
                ft.Icon(ft.Icons.SAVINGS_OUTLINED, size=64, color=TEXT_MUTED),
                ft.Text("등록된 계좌가 없습니다.", size=16, weight=ft.FontWeight.W_600, color=TEXT_SECONDARY),
                ft.Text("우측 하단 '+' 버튼 또는 아래 버튼을 눌러\n첫 번째 계좌를 생성해보세요.", size=13, color=TEXT_MUTED, text_align=ft.TextAlign.CENTER),
                ft.Container(height=16),
                ft.FilledButton(
                    content=ft.Row(
                        controls=[ft.Icon(ft.Icons.ADD, size=18), ft.Text("첫 계좌 생성하기", weight=ft.FontWeight.BOLD)],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=6
                    ),
                    style=ft.ButtonStyle(
                        bgcolor=ACCENT_BLUE,
                        color=ft.Colors.BLACK,
                        shape=ft.RoundedRectangleBorder(radius=10),
                        padding=ft.Padding.symmetric(horizontal=24, vertical=12)
                    ),
                    on_click=self.open_add_account_dialog
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True
        )

    def _goto_tab(self, index: int):
        self.bottom_nav.selected_index = index
        self.current_tab_index = index
        self.viewing_account_id = None
        self._render_current_view()

    # =================================================================
    # TAB 1: 💼 계좌 현황 (카드 리스트 & 우측 하단 '+' FAB)
    # =================================================================
    def _build_accounts_tab(self):
        if not self.accounts:
            return self._build_empty_home_view()

        cards = []
        for acc in self.accounts:
            aid = acc['id']
            dtl = next((d for d in self.accounts_details if d.get('account_id') == aid), {})

            name = acc.get('name', '계좌')
            ticker = acc.get('ticker', 'SOXL')
            strat = acc.get('strategy', '종종이 기본전략')
            seed = acc.get('initial_seed', 0.0)
            reserve_pct = float(acc.get('reserve_ratio', 0.05)) * 100.0

            asset = dtl.get('current_asset', seed)
            ret_pct = dtl.get('total_return_pct', 0.0)
            cash = dtl.get('current_cash', seed)
            hold = dtl.get('current_hold', 0)
            ak_val = dtl.get('ak_val', seed * 0.05)
            op_state = dtl.get('operational_state', 'WAITING_FOR_FILL')
            mode = dtl.get('mode', 'Normal')

            r_color = PROFIT_GREEN if ret_pct >= 0 else LOSS_RED

            card = ft.Card(
                bgcolor=SURFACE_CARD,
                elevation=2,
                shape=ft.RoundedRectangleBorder(radius=14),
                content=ft.Container(
                    padding=16,
                    border=ft.Border.all(1, BORDER_COLOR),
                    border_radius=14,
                    on_click=lambda e, target_id=aid: self.open_account_detail(target_id),
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Row(
                                        controls=[
                                            ft.Text(name, size=15, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                                            ft.Container(
                                                content=ft.Text(ticker, size=11, color=ACCENT_BLUE, weight=ft.FontWeight.BOLD),
                                                bgcolor=ft.Colors.with_opacity(0.15, ACCENT_BLUE),
                                                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                                border_radius=4
                                            ),
                                        ],
                                        spacing=6
                                    ),
                                    ft.Container(
                                        content=ft.Text(
                                            "🟢 주문대기" if op_state == 'WAITING_FOR_FILL' else "⚪ 마감완료",
                                            size=11,
                                            color=PROFIT_GREEN if op_state == 'WAITING_FOR_FILL' else TEXT_SECONDARY,
                                            weight=ft.FontWeight.BOLD
                                        ),
                                        bgcolor=ft.Colors.with_opacity(0.12, PROFIT_GREEN if op_state == 'WAITING_FOR_FILL' else TEXT_SECONDARY),
                                        padding=ft.Padding.symmetric(horizontal=7, vertical=2),
                                        border_radius=8
                                    )
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                            ),
                            ft.Text(f"{strat} • {mode} 모드", size=11, color=TEXT_SECONDARY),
                            ft.Container(height=4),
                            ft.Row(
                                controls=[
                                    ft.Column(
                                        controls=[
                                            ft.Text("평가 자산", size=10, color=TEXT_MUTED),
                                            ft.Text(f"${asset:,.2f}", size=18, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                                        ],
                                        spacing=1
                                    ),
                                    ft.Column(
                                        controls=[
                                            ft.Text("총 수익률", size=10, color=TEXT_MUTED),
                                            ft.Text(f"{ret_pct:+.2f}%", size=18, weight=ft.FontWeight.BOLD, color=r_color)
                                        ],
                                        horizontal_alignment=ft.CrossAxisAlignment.END,
                                        spacing=1
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                            ),
                            ft.Container(height=4),
                            ft.Divider(color=BORDER_COLOR, height=1),
                            ft.Container(height=2),
                            ft.Row(
                                controls=[
                                    ft.Text(f"원금: ${seed:,.0f}", size=11, color=TEXT_MUTED),
                                    ft.Text(f"예수금: ${cash:,.0f}", size=11, color=TEXT_MUTED),
                                    ft.Text(f"보유: {hold:,}주", size=11, color=TEXT_MUTED),
                                    ft.Text(f"위기: {reserve_pct:.0f}% (${ak_val:,.0f})", size=11, color=RESERVE_AMBER),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                            ),
                            ft.Container(height=4),
                            ft.Row(
                                controls=[
                                    ft.Text("👉 터치하여 상세 매입 정보 및 주문표 보기", size=11, color=ACCENT_BLUE),
                                    ft.Icon(ft.Icons.ARROW_FORWARD, size=14, color=ACCENT_BLUE)
                                ],
                                alignment=ft.MainAxisAlignment.END,
                                spacing=4
                            )
                        ],
                        spacing=3
                    )
                )
            )
            cards.append(card)

        return ft.ListView(
            controls=[
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=4, vertical=6),
                    content=ft.Row(
                        controls=[
                            ft.Text(f"운용 계좌 ({len(self.accounts)}개)", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                            ft.Text("우측 하단 '+' 버튼으로 새 계좌 추가", size=11, color=TEXT_MUTED)
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    )
                ),
                *cards,
                ft.Container(height=70) # 플로팅 버튼 여백
            ],
            spacing=8,
            expand=True
        )

    # =================================================================
    # 계좌 상세 페이지 (기본 정보 + 매입 조각별 상세 + 금일 주문표 + 일일 정산)
    # =================================================================
    def _build_account_detail_view(self, acc: dict, dtl: dict):
        acc_id = acc['id']
        name = acc.get('name', '')
        ticker = acc.get('ticker', 'SOXL')
        strat = acc.get('strategy', '종종이 기본전략')
        seed = acc.get('initial_seed', 0.0)
        curr_d = dtl.get('current_date', '')
        target_date = dtl.get('target_order_date', '')

        asset = dtl.get('current_asset', 0.0)
        ret_pct = dtl.get('total_return_pct', 0.0)
        profit = dtl.get('total_profit', 0.0)
        cash = dtl.get('current_cash', 0.0)
        hold = dtl.get('current_hold', 0)
        ak_val = dtl.get('ak_val', 0.0)
        ar_val = dtl.get('ar_val', 0.0)
        budget = dtl.get('daily_budget', 0.0)
        mode = dtl.get('mode', 'Normal')
        latest_price = dtl.get('current_price', 0.0)
        op_state = dtl.get('operational_state', 'WAITING_FOR_FILL')

        # -------------------------------------------------------------
        # 1. 계좌 기본 정보 & KPI 카드
        # -------------------------------------------------------------
        basic_info_card = ft.Card(
            bgcolor=SURFACE_CARD,
            elevation=2,
            shape=ft.RoundedRectangleBorder(radius=14),
            content=ft.Container(
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Column(
                                    controls=[
                                        ft.Text(f"{name} ({ticker})", size=16, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                                        ft.Text(f"{strat} • {mode} 모드 (8분할 운용)", size=11, color=TEXT_SECONDARY)
                                    ],
                                    spacing=2
                                ),
                                ft.Container(
                                    content=ft.Text(
                                        "🟢 주문대기" if op_state == 'WAITING_FOR_FILL' else "⚪ 마감완료",
                                        size=11,
                                        color=PROFIT_GREEN if op_state == 'WAITING_FOR_FILL' else TEXT_SECONDARY,
                                        weight=ft.FontWeight.BOLD
                                    ),
                                    bgcolor=ft.Colors.with_opacity(0.12, PROFIT_GREEN if op_state == 'WAITING_FOR_FILL' else TEXT_SECONDARY),
                                    padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                                    border_radius=8
                                )
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        ft.Container(height=6),
                        ft.Row(
                            controls=[
                                ft.Column([
                                    ft.Text("평가 자산", size=11, color=TEXT_MUTED),
                                    ft.Text(f"${asset:,.2f}", size=20, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                                ], spacing=1),
                                ft.Column([
                                    ft.Text("총 수익률", size=11, color=TEXT_MUTED),
                                    ft.Text(f"{ret_pct:+.2f}% ({profit:+,.0f}$)", size=18, weight=ft.FontWeight.BOLD, color=PROFIT_GREEN if profit >= 0 else LOSS_RED)
                                ], horizontal_alignment=ft.CrossAxisAlignment.END, spacing=1)
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        ft.Container(height=4),
                        ft.Divider(color=BORDER_COLOR, height=1),
                        ft.Container(height=4),
                        ft.Row(
                            controls=[
                                ft.Column([
                                    ft.Text("위기준비금 (AK)", size=10, color=RESERVE_AMBER),
                                    ft.Text(f"${ak_val:,.0f}", size=14, weight=ft.FontWeight.BOLD, color=RESERVE_AMBER)
                                ], spacing=1),
                                ft.Column([
                                    ft.Text("실가동시드 (AR)", size=10, color=ACCENT_BLUE),
                                    ft.Text(f"${ar_val:,.0f}", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                                ], spacing=1),
                                ft.Column([
                                    ft.Text("하루 배분 예산", size=10, color=TEXT_SECONDARY),
                                    ft.Text(f"${budget:,.2f}", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                                ], spacing=1),
                                ft.Column([
                                    ft.Text("예수금", size=10, color=TEXT_SECONDARY),
                                    ft.Text(f"${cash:,.0f}", size=14, weight=ft.FontWeight.BOLD, color=PROFIT_GREEN)
                                ], spacing=1),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        )
                    ]
                )
            )
        )

        # -------------------------------------------------------------
        # 2. 매입 정보 (전체 몇 조각 매입했고, 각각의 수량/매입가/손실비율)
        # -------------------------------------------------------------
        df_res = dtl.get('df_res')
        unsold_lots = []
        if df_res is not None and not df_res.empty:
            unsold_df = df_res[(df_res['R'] > 0) & (~df_res['Sold'])]
            for idx, r_row in unsold_df.iterrows():
                unsold_lots.append(r_row)

        total_pieces = len(unsold_lots)
        lot_cards = []

        if total_pieces > 0:
            for i, lot in enumerate(unsold_lots):
                r_q = int(lot['R'])
                bp = float(lot.get('BuyPrice', lot['Close']))
                d_str = str(lot['Date'])[:10]
                cur_p = latest_price if latest_price > 0 else bp
                ret_loss = (cur_p / bp - 1.0) * 100.0
                target_u = float(lot['U']) if lot.get('U') is not None else bp * 1.0275
                invest_amt = float(lot.get('S', bp * r_q))

                loss_color = PROFIT_GREEN if ret_loss >= 0 else LOSS_RED

                l_card = ft.Container(
                    bgcolor=SURFACE_CARD,
                    border=ft.Border.all(1, ft.Colors.with_opacity(0.3, loss_color)),
                    border_radius=10,
                    padding=12,
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Row([
                                        ft.Container(
                                            content=ft.Text(f"조각 #{i+1}", size=11, weight=ft.FontWeight.BOLD, color=ACCENT_BLUE),
                                            bgcolor=ft.Colors.with_opacity(0.15, ACCENT_BLUE),
                                            padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                            border_radius=4
                                        ),
                                        ft.Text(f"매입일: {d_str}", size=12, weight=ft.FontWeight.W_600, color=TEXT_PRIMARY),
                                    ], spacing=6),
                                    ft.Text(f"현재 손익률: {ret_loss:+.2f}%", size=12, weight=ft.FontWeight.BOLD, color=loss_color)
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                            ),
                            ft.Container(height=4),
                            ft.Row(
                                controls=[
                                    ft.Column([
                                        ft.Text("매입 수량", size=10, color=TEXT_MUTED),
                                        ft.Text(f"{r_q:,}주", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                                    ], spacing=1),
                                    ft.Column([
                                        ft.Text("매입 단가", size=10, color=TEXT_MUTED),
                                        ft.Text(f"${bp:.2f}", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                                    ], spacing=1),
                                    ft.Column([
                                        ft.Text("매입 총액", size=10, color=TEXT_MUTED),
                                        ft.Text(f"${invest_amt:,.2f}", size=13, weight=ft.FontWeight.W_600, color=TEXT_PRIMARY)
                                    ], spacing=1),
                                    ft.Column([
                                        ft.Text("익절 목표가", size=10, color=TEXT_MUTED),
                                        ft.Text(f"${target_u:.2f}", size=14, weight=ft.FontWeight.BOLD, color=PROFIT_GREEN)
                                    ], spacing=1),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                            )
                        ],
                        spacing=2
                    )
                )
                lot_cards.append(l_card)
        else:
            lot_cards.append(
                ft.Container(
                    bgcolor=SURFACE_CARD,
                    border=ft.Border.all(1, BORDER_COLOR),
                    border_radius=10,
                    padding=16,
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=PROFIT_GREEN, size=20),
                            ft.Text("현재 보유 중인 매입 조각이 없습니다. (100% 현금 대기 중)", size=12, color=TEXT_SECONDARY)
                        ],
                        spacing=8
                    )
                )
            )

        holdings_section = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Row([
                            ft.Icon(ft.Icons.LAYERS_OUTLINED, color=ACCENT_BLUE, size=18),
                            ft.Text("매입 조각 현황", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                        ], spacing=6),
                        ft.Text(f"총 {total_pieces}조각 보유 중 ({hold:,}주)", size=12, color=ACCENT_BLUE, weight=ft.FontWeight.BOLD)
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                *lot_cards
            ],
            spacing=8
        )

        # -------------------------------------------------------------
        # 3. 금일 매수·매도 주문표 (간결하고 직관적인 수량 중심 UI)
        # -------------------------------------------------------------
        sell_orders = dtl.get('sell_orders', [])
        buy_orders = dtl.get('buy_orders', [])

        total_sell_qty = 0
        for s in sell_orders:
            raw_q = str(s.get('주문수량', s.get('qty', '0'))).replace('주', '').replace(',', '').strip()
            try:
                total_sell_qty += int(raw_q)
            except Exception:
                pass

        total_buy_qty = 0
        for b in buy_orders:
            raw_q = str(b.get('주문수량', b.get('qty', '0'))).replace('주', '').replace(',', '').strip()
            try:
                total_buy_qty += int(raw_q)
            except Exception:
                pass

        # 3-1. 매도 주문 박스 (단일 테두리 박스 - 심플하게 몇 개 매도할지 직관 표시)
        sell_items = []
        if sell_orders:
            for s in sell_orders:
                title = s.get('구분', 'LOC 매도')
                price = s.get('주문단가', '$0.00')
                qty = str(s.get('주문수량', '0')).replace('주', '').replace(',', '').strip()

                row = ft.Container(
                    padding=ft.Padding.symmetric(vertical=8, horizontal=10),
                    bgcolor=ft.Colors.with_opacity(0.06, LOSS_RED),
                    border_radius=8,
                    content=ft.Row(
                        controls=[
                            ft.Row([
                                ft.Container(
                                    content=ft.Text("매도", size=10, weight=ft.FontWeight.BOLD, color=LOSS_RED),
                                    bgcolor=ft.Colors.with_opacity(0.15, LOSS_RED),
                                    padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                    border_radius=4
                                ),
                                ft.Text(f"{title} ({price})", size=13, weight=ft.FontWeight.W_600, color=TEXT_PRIMARY),
                            ], spacing=8),
                            ft.Text(f"{qty}주 매도", size=14, weight=ft.FontWeight.BOLD, color=LOSS_RED)
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    )
                )
                sell_items.append(row)
        else:
            sell_items.append(
                ft.Container(
                    padding=ft.Padding.symmetric(vertical=8, horizontal=8),
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=TEXT_MUTED, size=15),
                            ft.Text("당일 체결 대상 매도 주문 없음 (보유 홀딩)", size=12, color=TEXT_MUTED)
                        ],
                        spacing=6
                    )
                )
            )

        sell_box = ft.Container(
            bgcolor=SURFACE_CARD,
            border=ft.Border.all(1, ft.Colors.with_opacity(0.35, LOSS_RED)),
            border_radius=12,
            padding=12,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Row([
                                ft.Icon(ft.Icons.ARROW_UPWARD, color=LOSS_RED, size=16),
                                ft.Text("🔴 매도 주문", size=13, weight=ft.FontWeight.BOLD, color=LOSS_RED),
                            ], spacing=6),
                            ft.Container(
                                content=ft.Text(f"총 {total_sell_qty:,}주 매도" if total_sell_qty > 0 else "0건", size=10, color=LOSS_RED, weight=ft.FontWeight.BOLD),
                                bgcolor=ft.Colors.with_opacity(0.15, LOSS_RED),
                                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                border_radius=4
                            )
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    ),
                    ft.Divider(color=BORDER_COLOR, height=1),
                    *sell_items
                ],
                spacing=6
            )
        )

        # 3-2. 매수 주문 박스 (단일 테두리 박스 - 심플하게 몇 개 매수할지 직관 표시)
        buy_items = []
        if buy_orders:
            for b in buy_orders:
                stage = b.get('호가단계', '순매수')
                price = b.get('주문단가', '$0.00')
                qty = str(b.get('주문수량', '0')).replace('주', '').replace(',', '').strip()
                tag_label = stage.split()[0] if ' ' in stage else stage[:3]

                row = ft.Container(
                    padding=ft.Padding.symmetric(vertical=8, horizontal=10),
                    bgcolor=ft.Colors.with_opacity(0.06, PROFIT_GREEN),
                    border_radius=8,
                    content=ft.Row(
                        controls=[
                            ft.Row([
                                ft.Container(
                                    content=ft.Text(tag_label, size=10, weight=ft.FontWeight.BOLD, color=PROFIT_GREEN),
                                    bgcolor=ft.Colors.with_opacity(0.15, PROFIT_GREEN),
                                    padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                    border_radius=4
                                ),
                                ft.Text(f"{stage} ({price})", size=13, weight=ft.FontWeight.W_600, color=TEXT_PRIMARY),
                            ], spacing=8),
                            ft.Text(f"{qty}주 매수", size=14, weight=ft.FontWeight.BOLD, color=PROFIT_GREEN)
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    )
                )
                buy_items.append(row)
        else:
            buy_items.append(
                ft.Container(
                    padding=ft.Padding.symmetric(vertical=8, horizontal=8),
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=TEXT_MUTED, size=15),
                            ft.Text("당일 체결 대상 매수 주문 없음", size=12, color=TEXT_MUTED)
                        ],
                        spacing=6
                    )
                )
            )

        buy_box = ft.Container(
            bgcolor=SURFACE_CARD,
            border=ft.Border.all(1, ft.Colors.with_opacity(0.35, PROFIT_GREEN)),
            border_radius=12,
            padding=12,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Row([
                                ft.Icon(ft.Icons.ARROW_DOWNWARD, color=PROFIT_GREEN, size=16),
                                ft.Text("🟢 매수 주문", size=13, weight=ft.FontWeight.BOLD, color=PROFIT_GREEN),
                            ], spacing=6),
                            ft.Container(
                                content=ft.Text(f"총 {total_buy_qty:,}주 매수" if total_buy_qty > 0 else "0건", size=10, color=PROFIT_GREEN, weight=ft.FontWeight.BOLD),
                                bgcolor=ft.Colors.with_opacity(0.15, PROFIT_GREEN),
                                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                border_radius=4
                            )
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    ),
                    ft.Divider(color=BORDER_COLOR, height=1),
                    *buy_items
                ],
                spacing=6
            )
        )

        orders_section = ft.Column(
            controls=[
                ft.Row([
                    ft.Icon(ft.Icons.RECEIPT_LONG, color=ACCENT_BLUE, size=18),
                    ft.Text(f"금일 매수·매도 주문표 ({target_date})", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                ], spacing=6),
                sell_box,
                buy_box
            ],
            spacing=8
        )

        # -------------------------------------------------------------
        # 4. 실시간 시세 조회 및 일일 정산 입력 폼
        # -------------------------------------------------------------
        records = acc.get('trade_records', [])
        fallback_p = latest_price
        if fallback_p <= 0 and records:
            fallback_p = float(records[-1].get('Close', 142.50))
        elif fallback_p <= 0:
            fallback_p = 142.50

        real_close = get_current_stock_price(ticker, fallback_price=fallback_p)
        calc_buy_q, calc_sell_q = compute_suggested_trades(real_close, buy_orders, sell_orders)

        # 첫날 신규 계좌이고 매수 대기 중인데 계산이 0이면 1차 주문 수량으로 기본 제안
        if calc_buy_q == 0 and not records and buy_orders:
            try:
                calc_buy_q = int(str(buy_orders[0].get('주문수량', '0')).replace('주', '').replace(',', '').strip())
            except Exception:
                pass

        close_field = ft.TextField(
            label="당일종가($)",
            label_style=ft.TextStyle(size=11, color=TEXT_SECONDARY),
            value=f"{real_close:.2f}",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY,
            text_size=12,
            text_align=ft.TextAlign.RIGHT,
            content_padding=ft.Padding.symmetric(horizontal=8, vertical=6),
            expand=True
        )

        buy_qty_field = ft.TextField(
            label="체결매수(주)",
            label_style=ft.TextStyle(size=11, color=PROFIT_GREEN),
            value=str(calc_buy_q),
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=BORDER_COLOR,
            focused_border_color=PROFIT_GREEN,
            color=TEXT_PRIMARY,
            text_size=12,
            text_align=ft.TextAlign.RIGHT,
            content_padding=ft.Padding.symmetric(horizontal=8, vertical=6),
            expand=True
        )

        sell_qty_field = ft.TextField(
            label="체결매도(주)",
            label_style=ft.TextStyle(size=11, color=LOSS_RED),
            value=str(calc_sell_q),
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=BORDER_COLOR,
            focused_border_color=LOSS_RED,
            color=TEXT_PRIMARY,
            text_size=12,
            text_align=ft.TextAlign.RIGHT,
            content_padding=ft.Padding.symmetric(horizontal=8, vertical=6),
            expand=True
        )

        def on_close_changed(e):
            try:
                val = float(close_field.value.strip())
                b_q, s_q = compute_suggested_trades(val, buy_orders, sell_orders)
                buy_qty_field.value = str(b_q)
                sell_qty_field.value = str(s_q)
                buy_qty_field.update()
                sell_qty_field.update()
            except Exception:
                pass

        close_field.on_change = on_close_changed

        def handle_settle(e):
            try:
                c_p = float(close_field.value.strip())
                b_q = int(buy_qty_field.value.strip())
                s_q = int(sell_qty_field.value.strip())
                self.am.record_daily_close(acc_id=acc_id, close_price=c_p, buy_qty=b_q, sell_qty=s_q, buy_price=c_p)
                show_toast(self.page, f"{curr_d} 장 마감 정산이 완료되었습니다!")
                self.reload_data()
            except Exception as ex:
                show_toast(self.page, f"정산 오류: {ex}", is_error=True)

        def handle_next_day(e):
            res = self.am.advance_next_day(acc_id)
            if res:
                show_toast(self.page, f"다음 거래일({res.get('current_date')})로 진행되었습니다!")
                self.reload_data()
            else:
                show_toast(self.page, "다음 거래일 진행 실패", is_error=True)

        settle_card = ft.Card(
            bgcolor=SURFACE_CARD,
            elevation=2,
            shape=ft.RoundedRectangleBorder(radius=12),
            content=ft.Container(
                padding=14,
                content=ft.Column(
                    controls=[
                        ft.Row([
                            ft.Text(f"일일 정산 ({curr_d})", size=13, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                        ], spacing=6),
                        ft.Row([close_field, buy_qty_field, sell_qty_field], spacing=6),
                        ft.Row(
                            controls=[
                                ft.FilledButton(
                                    "정산 마감 확정",
                                    style=ft.ButtonStyle(bgcolor=PROFIT_GREEN, color=ft.Colors.WHITE),
                                    expand=True,
                                    on_click=handle_settle
                                ),
                                ft.FilledButton(
                                    "다음 거래일 진행",
                                    style=ft.ButtonStyle(bgcolor=ACCENT_BLUE, color=ft.Colors.BLACK),
                                    expand=True,
                                    on_click=handle_next_day
                                ),
                            ],
                            spacing=6
                        ),
                        ft.OutlinedButton(
                            content=ft.Row([ft.Icon(ft.Icons.UNDO, size=15, color=LOSS_RED), ft.Text("최근 거래일 Undo", size=11, color=LOSS_RED)], alignment=ft.MainAxisAlignment.CENTER, spacing=4),
                            style=ft.ButtonStyle(side=ft.BorderSide(1, ft.Colors.with_opacity(0.3, LOSS_RED))),
                            width=380,
                            on_click=lambda _: self.open_undo_dialog(acc_id)
                        )
                    ],
                    spacing=8
                )
            )
        )

        # -------------------------------------------------------------
        # 5. 최근 거래 내역 (엑셀 형식 표 & 길게 탭/클릭하여 수정)
        # -------------------------------------------------------------
        table_rows = []
        if records:
            for orig_idx, r in reversed(list(enumerate(records))):
                r_d = str(r.get('Date', ''))
                r_cp = float(r.get('Close', 0.0))
                r_bq = int(r.get('BuyQty', r.get('R', 0)))
                r_sq = int(r.get('SellQty', 0))
                r_asset = float(r.get('Asset', 0.0))
                r_p = float(r.get('Profit', 0.0) or 0.0)

                p_str = f"{r_p:+,.0f}$" if r_p != 0 else "$0"
                p_color = PROFIT_GREEN if r_p > 0 else (LOSS_RED if r_p < 0 else TEXT_MUTED)

                def make_edit_fn(idx_to_edit):
                    return lambda _: self.open_edit_trade_dialog(acc_id, idx_to_edit)

                table_rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(r_d, size=11, color=TEXT_PRIMARY, weight=ft.FontWeight.W_500)),
                            ft.DataCell(ft.Text(f"${r_cp:.2f}", size=11, color=TEXT_PRIMARY)),
                            ft.DataCell(ft.Text(f"{r_bq:,}", size=11, color=PROFIT_GREEN if r_bq > 0 else TEXT_MUTED, weight=ft.FontWeight.BOLD if r_bq > 0 else ft.FontWeight.NORMAL)),
                            ft.DataCell(ft.Text(f"{r_sq:,}", size=11, color=LOSS_RED if r_sq > 0 else TEXT_MUTED, weight=ft.FontWeight.BOLD if r_sq > 0 else ft.FontWeight.NORMAL)),
                            ft.DataCell(ft.Text(f"${r_asset:,.0f}", size=11, color=TEXT_PRIMARY)),
                            ft.DataCell(ft.Text(p_str, size=11, color=p_color, weight=ft.FontWeight.W_600)),
                            ft.DataCell(
                                ft.IconButton(
                                    icon=ft.Icons.EDIT_OUTLINED,
                                    icon_size=15,
                                    icon_color=ACCENT_BLUE,
                                    tooltip="기록 수정",
                                    on_click=make_edit_fn(orig_idx)
                                )
                            ),
                        ],
                        on_long_press=make_edit_fn(orig_idx)
                    )
                )

            history_table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("날짜", weight=ft.FontWeight.BOLD, size=11, color=TEXT_SECONDARY)),
                    ft.DataColumn(ft.Text("종가", weight=ft.FontWeight.BOLD, size=11, color=TEXT_SECONDARY), numeric=True),
                    ft.DataColumn(ft.Text("매수", weight=ft.FontWeight.BOLD, size=11, color=TEXT_SECONDARY), numeric=True),
                    ft.DataColumn(ft.Text("매도", weight=ft.FontWeight.BOLD, size=11, color=TEXT_SECONDARY), numeric=True),
                    ft.DataColumn(ft.Text("평가자산", weight=ft.FontWeight.BOLD, size=11, color=TEXT_SECONDARY), numeric=True),
                    ft.DataColumn(ft.Text("손익", weight=ft.FontWeight.BOLD, size=11, color=TEXT_SECONDARY), numeric=True),
                    ft.DataColumn(ft.Text("수정", weight=ft.FontWeight.BOLD, size=11, color=TEXT_SECONDARY)),
                ],
                rows=table_rows,
                border=ft.Border.all(1, BORDER_COLOR),
                heading_row_color=ft.Colors.with_opacity(0.35, BG_DARK),
                data_row_min_height=38,
                data_row_max_height=42,
                column_spacing=12,
                horizontal_margin=8,
            )

            history_view = ft.Container(
                bgcolor=SURFACE_CARD,
                border=ft.Border.all(1, BORDER_COLOR),
                border_radius=10,
                padding=4,
                content=ft.Row(
                    controls=[history_table],
                    scroll=ft.ScrollMode.ALWAYS
                )
            )
        else:
            history_view = ft.Container(
                bgcolor=SURFACE_CARD,
                border=ft.Border.all(1, BORDER_COLOR),
                border_radius=10,
                padding=20,
                alignment=ft.Alignment.CENTER,
                content=ft.Text("기록된 거래 내역이 없습니다.", size=12, color=TEXT_MUTED)
            )

        history_section = ft.Column(
            controls=[
                ft.Row([
                    ft.Text("최근 거래 내역", size=13, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                    ft.Text("(길게 탭 또는 ✏️ 눌러 수정)", size=10, color=TEXT_SECONDARY),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                history_view
            ],
            spacing=6
        )

        return ft.ListView(
            controls=[
                basic_info_card,
                ft.Container(height=6),
                holdings_section,
                ft.Container(height=6),
                orders_section,
                ft.Container(height=6),
                settle_card,
                ft.Container(height=6),
                history_section,
                ft.Container(height=20)
            ],
            spacing=8,
            expand=True
        )

    # =================================================================
    # TAB 2: 📊 백테스트 (전략 검증 및 성과 비교 차트)
    # =================================================================
    def _build_backtest_tab(self):
        ticker_dd = ft.Dropdown(
            label="대상 종목",
            value="SOXL",
            options=[
                ft.dropdown.Option("SOXL"),
                ft.dropdown.Option("TQQQ"),
                ft.dropdown.Option("UPRO"),
                ft.dropdown.Option("NVDA"),
                ft.dropdown.Option("AAPL")
            ],
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY,
            expand=True
        )

        strat_dd = ft.Dropdown(
            label="검증 전략",
            value="종종이 기본전략",
            options=[
                ft.dropdown.Option("종종이 기본전략"),
                ft.dropdown.Option("무한매수법 v4.0"),
                ft.dropdown.Option("단순보유(Buy & Hold)")
            ],
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY,
            expand=True
        )

        period_dd = ft.Dropdown(
            label="테스트 기간",
            value="최근 3년",
            options=[
                ft.dropdown.Option("최근 1년"),
                ft.dropdown.Option("최근 2년"),
                ft.dropdown.Option("최근 3년"),
                ft.dropdown.Option("최근 5년"),
                ft.dropdown.Option("2019년~현재")
            ],
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY,
            expand=True
        )

        seed_field = ft.TextField(
            label="초기 투자 원금 ($)",
            value="200000",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY,
            expand=True
        )

        progress_ring = ft.ProgressRing(visible=False, color=ACCENT_BLUE, width=24, height=24)
        run_btn = ft.FilledButton(
            content=ft.Row(
                controls=[
                    progress_ring,
                    ft.Icon(ft.Icons.ROCKET_LAUNCH, size=16),
                    ft.Text("백테스트 실행", size=14, weight=ft.FontWeight.BOLD)
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8
            ),
            style=ft.ButtonStyle(
                bgcolor=ACCENT_BLUE,
                color=ft.Colors.BLACK,
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.Padding.symmetric(vertical=12)
            ),
            width=380
        )

        def handle_run_backtest(e):
            t = ticker_dd.value
            s_name = strat_dd.value
            p_val = period_dd.value
            try:
                cap = float(seed_field.value.strip())
            except Exception:
                cap = 200000.0

            # 기간 환산
            now = datetime.now()
            if p_val == "최근 1년":
                s_date = (now - timedelta(days=365)).strftime('%Y-%m-%d')
            elif p_val == "최근 2년":
                s_date = (now - timedelta(days=730)).strftime('%Y-%m-%d')
            elif p_val == "최근 3년":
                s_date = (now - timedelta(days=1095)).strftime('%Y-%m-%d')
            elif p_val == "최근 5년":
                s_date = (now - timedelta(days=1825)).strftime('%Y-%m-%d')
            else:
                s_date = '2019-01-01'
            e_date = now.strftime('%Y-%m-%d')

            progress_ring.visible = True
            run_btn.disabled = True
            self.page.update()

            try:
                # 야후 파이낸스 시세 다운로드
                df_market = fetch_market_data(t, s_date, e_date)

                # 전략 인스턴스 생성
                if "종종이" in s_name:
                    strat = JongJongStrategy(initial_capital=cap, reserve_ratio=0.05)
                elif "무한" in s_name:
                    strat = InfiniteBuyingV4Strategy(ticker=t, initial_capital=cap, divisions=40)
                else:
                    strat = BuyAndHoldStrategy(name=f"{t} 단순보유", initial_capital=cap)

                # 벤치마크(단순보유)
                bnh_strat = BuyAndHoldStrategy(name=f"{t} 단순보유", initial_capital=cap)

                df_res = strat.run(df_market, s_date, e_date)
                df_bnh = bnh_strat.run(df_market, s_date, e_date)

                m_res = calculate_metrics(df_res, cap)
                chart_b64 = render_backtest_chart(df_res, df_bnh, s_name, t)

                self.bt_results = {
                    'ticker': t,
                    'strategy': s_name,
                    'period': f"{s_date} ~ {e_date}",
                    'initial_capital': cap,
                    'metrics': m_res,
                    'chart_b64': chart_b64
                }
                show_toast(self.page, f"{t} 백테스트 연산이 완료되었습니다!")
            except Exception as ex:
                show_toast(self.page, f"백테스트 실패: {ex}", is_error=True)
            finally:
                progress_ring.visible = False
                run_btn.disabled = False
                self._render_current_view()

        run_btn.on_click = handle_run_backtest

        # 파라미터 입력 카드
        input_card = ft.Card(
            bgcolor=SURFACE_CARD,
            elevation=2,
            shape=ft.RoundedRectangleBorder(radius=14),
            content=ft.Container(
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Row([
                            ft.Icon(ft.Icons.TUNE, color=ACCENT_BLUE, size=18),
                            ft.Text("백테스트 환경 설정", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                        ], spacing=6),
                        ft.Container(height=4),
                        ft.Row([ticker_dd, strat_dd], spacing=8),
                        ft.Row([period_dd, seed_field], spacing=8),
                        ft.Container(height=4),
                        run_btn
                    ],
                    spacing=8
                )
            )
        )

        results_widgets = []
        if self.bt_results:
            res = self.bt_results
            m = res.get('metrics', {})
            f_asset = m.get('final_asset', 0.0)
            tot_ret = m.get('total_return', 0.0)
            cagr = m.get('cagr', 0.0)
            mdd = m.get('mdd', 0.0)
            sharpe = m.get('sharpe', 0.0)
            calmar = m.get('calmar', 0.0)
            t_days = m.get('trading_days', 0)

            # 4대 핵심 결과 카드
            def make_kpi(title, val, sub, color):
                return ft.Container(
                    bgcolor=SURFACE_CARD,
                    border=ft.Border.all(1, BORDER_COLOR),
                    border_radius=10,
                    padding=10,
                    expand=True,
                    content=ft.Column(
                        controls=[
                            ft.Text(title, size=10, color=TEXT_MUTED),
                            ft.Text(val, size=16, weight=ft.FontWeight.BOLD, color=color),
                            ft.Text(sub, size=10, color=TEXT_SECONDARY)
                        ],
                        spacing=1
                    )
                )

            kpi_row1 = ft.Row([
                make_kpi("최종 자산", f"${f_asset:,.0f}", f"약 {f_asset*EXCHANGE_RATE/1e8:.2f}억원", TEXT_PRIMARY),
                make_kpi("총 수익률", f"{tot_ret:+.2f}%", f"{'수익' if tot_ret>=0 else '손실'}", PROFIT_GREEN if tot_ret>=0 else LOSS_RED),
            ], spacing=6)

            kpi_row2 = ft.Row([
                make_kpi("CAGR (연복리)", f"{cagr:+.2f}%", "연평균 성장률", ACCENT_BLUE),
                make_kpi("MDD (최대낙폭)", f"{mdd:.2f}%", "최대 손실폭", LOSS_RED),
            ], spacing=6)

            chart_display = ft.Card(
                bgcolor=SURFACE_CARD,
                elevation=2,
                shape=ft.RoundedRectangleBorder(radius=12),
                content=ft.Container(
                    padding=12,
                    content=ft.Column(
                        controls=[
                            ft.Text(f"{res['strategy']} vs 단순보유 자산 곡선", size=13, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                            ft.Container(height=4),
                            ft.Image(src=res['chart_b64'], fit="contain", border_radius=8)
                        ]
                    )
                )
            )

            stats_card = ft.Container(
                bgcolor=SURFACE_CARD,
                border=ft.Border.all(1, BORDER_COLOR),
                border_radius=10,
                padding=12,
                content=ft.Row(
                    controls=[
                        ft.Text(f"거래일수: {t_days}일", size=11, color=TEXT_MUTED),
                        ft.Text(f"샤프지수: {sharpe:.2f}", size=11, color=TEXT_MUTED),
                        ft.Text(f"Calmar: {calmar:.2f}", size=11, color=TEXT_MUTED),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_AROUND
                )
            )

            results_widgets = [
                ft.Container(height=4),
                ft.Text("📊 시뮬레이션 성과 요약", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                kpi_row1,
                kpi_row2,
                ft.Container(height=4),
                chart_display,
                stats_card
            ]
        else:
            results_widgets = [
                ft.Container(height=20),
                ft.Container(
                    bgcolor=SURFACE_CARD,
                    border=ft.Border.all(1, BORDER_COLOR),
                    border_radius=12,
                    padding=20,
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.Icons.QUERY_STATS, size=40, color=TEXT_MUTED),
                            ft.Text("백테스트 결과가 여기에 표시됩니다.", size=13, weight=ft.FontWeight.W_600, color=TEXT_SECONDARY),
                            ft.Text("종목과 기간을 선택한 후 [백테스트 실행]을 눌러보세요.", size=11, color=TEXT_MUTED, text_align=ft.TextAlign.CENTER)
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=6
                    )
                )
            ]

        return ft.ListView(
            controls=[
                input_card,
                *results_widgets,
                ft.Container(height=20)
            ],
            spacing=8,
            expand=True
        )

    # =================================================================
    # TAB 3: ⚙ 설정 (CSV 내보내기 & 시스템 환경 설정)
    # =================================================================
    def _build_settings_tab(self):
        global EXCHANGE_RATE

        exports_dir = os.path.join(CURRENT_DIR, "exports")
        os.makedirs(exports_dir, exist_ok=True)

        acc_options = []
        for a in self.accounts:
            acc_options.append(ft.dropdown.Option(key=a['id'], text=f"{a.get('name', '계좌')} ({a.get('ticker', '')})"))

        selected_acc_id = self.accounts[0]['id'] if self.accounts else None

        export_acc_dd = ft.Dropdown(
            label="내보낼 계좌 선택",
            value=selected_acc_id,
            options=acc_options,
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY,
            expand=True
        )

        def handle_export_csv(e):
            aid = export_acc_dd.value
            if not aid:
                show_toast(self.page, "내보낼 계좌를 선택해주세요.", is_error=True)
                return

            target = next((a for a in self.accounts if a['id'] == aid), None)
            if not target:
                show_toast(self.page, "계좌를 찾을 수 없습니다.", is_error=True)
                return

            acc_name = target.get('name', '계좌').replace(' ', '_')
            now_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{acc_name}_매매일지_{now_str}.csv"
            filepath = os.path.join(exports_dir, filename)

            try:
                ok = self.am.export_trade_records_csv(aid, filepath)
                if ok:
                    show_toast(self.page, f"'{filename}' 파일로 저장되었습니다!")
                else:
                    show_toast(self.page, "저장할 매매 일지 기록이 없습니다.", is_error=True)
            except Exception as ex:
                show_toast(self.page, f"CSV 내보내기 실패: {ex}", is_error=True)

        def handle_open_folder(e):
            try:
                if sys.platform == "win32":
                    os.startfile(exports_dir)
                else:
                    subprocess.run(["open" if sys.platform == "darwin" else "xdg-open", exports_dir])
            except Exception as ex:
                show_toast(self.page, f"폴더 열기 실패: {ex}", is_error=True)

        # 1. CSV 내보내기 카드
        export_card = ft.Card(
            bgcolor=SURFACE_CARD,
            elevation=2,
            shape=ft.RoundedRectangleBorder(radius=14),
            content=ft.Container(
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.FILE_DOWNLOAD_OUTLINED, color=ACCENT_BLUE, size=20),
                                ft.Text("계좌 매매 내역 CSV 내보내기", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                            ],
                            spacing=6
                        ),
                        ft.Text("선택한 계좌의 일일 매매 기록(체결가, 수량, 현금, 잔고, 실현손익)을 엑셀용 CSV 파일로 저장합니다.", size=11, color=TEXT_SECONDARY),
                        ft.Container(height=4),
                        export_acc_dd,
                        ft.Container(height=4),
                        ft.Row(
                            controls=[
                                ft.FilledButton(
                                    content=ft.Row([ft.Icon(ft.Icons.DOWNLOAD, size=16), ft.Text("CSV 내보내기", size=13, weight=ft.FontWeight.BOLD)], spacing=6),
                                    style=ft.ButtonStyle(bgcolor=ACCENT_BLUE, color=ft.Colors.BLACK, shape=ft.RoundedRectangleBorder(radius=8), padding=ft.Padding.symmetric(vertical=11)),
                                    expand=True,
                                    on_click=handle_export_csv
                                ),
                                ft.OutlinedButton(
                                    content=ft.Row([ft.Icon(ft.Icons.FOLDER_OPEN, size=16, color=TEXT_PRIMARY), ft.Text("저장 폴더 열기", size=12, color=TEXT_PRIMARY)], spacing=4),
                                    style=ft.ButtonStyle(side=ft.BorderSide(1, BORDER_COLOR), shape=ft.RoundedRectangleBorder(radius=8), padding=ft.Padding.symmetric(vertical=11)),
                                    expand=True,
                                    on_click=handle_open_folder
                                )
                            ],
                            spacing=8
                        )
                    ],
                    spacing=8
                )
            )
        )

        # 2. 환율 설정 카드
        rate_field = ft.TextField(
            label="기준 환율 (1 USD = N 원)",
            value=f"{EXCHANGE_RATE:.0f}",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY,
            text_size=13,
            content_padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            expand=True
        )

        def handle_save_rate(e):
            global EXCHANGE_RATE
            try:
                new_rate = float(rate_field.value.strip())
                if new_rate > 0:
                    EXCHANGE_RATE = new_rate
                    show_toast(self.page, f"기준 환율이 {EXCHANGE_RATE:,.0f}원으로 변경되었습니다.")
                    self.reload_data()
            except Exception:
                show_toast(self.page, "올바른 환율 숫자를 입력하세요.", is_error=True)

        rate_card = ft.Card(
            bgcolor=SURFACE_CARD,
            elevation=2,
            shape=ft.RoundedRectangleBorder(radius=14),
            content=ft.Container(
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.CURRENCY_EXCHANGE, color=PROFIT_GREEN, size=20),
                                ft.Text("기준 환율 설정", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                            ],
                            spacing=6
                        ),
                        ft.Text("홈 화면 및 계좌 상세에서 달러 자산을 원화로 환산할 때 적용되는 기준 환율입니다.", size=11, color=TEXT_SECONDARY),
                        ft.Container(height=4),
                        ft.Row(
                            controls=[
                                rate_field,
                                ft.FilledButton(
                                    "적용",
                                    style=ft.ButtonStyle(bgcolor=PROFIT_GREEN, color=ft.Colors.WHITE, shape=ft.RoundedRectangleBorder(radius=8)),
                                    on_click=handle_save_rate
                                )
                            ],
                            spacing=8
                        )
                    ],
                    spacing=8
                )
            )
        )

        # 3. 추후 확장 예정 설정 안내 카드
        future_card = ft.Card(
            bgcolor=SURFACE_CARD,
            elevation=2,
            shape=ft.RoundedRectangleBorder(radius=14),
            content=ft.Container(
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.AUTO_AWESOME, color=RESERVE_AMBER, size=20),
                                ft.Text("향후 추가 예정 설정", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                            ],
                            spacing=6
                        ),
                        ft.Text("다음 업데이트에서 다양한 개인화 및 자동화 설정이 제공될 예정입니다.", size=11, color=TEXT_SECONDARY),
                        ft.Container(height=4),
                        ft.Row([ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED, size=16, color=TEXT_MUTED), ft.Text("미국 프리마켓 장전 목표가 도달 알림", size=12, color=TEXT_MUTED)], spacing=8),
                        ft.Row([ft.Icon(ft.Icons.CLOUD_SYNC_OUTLINED, size=16, color=TEXT_MUTED), ft.Text("구글 드라이브 / 클라우드 계좌 백업 동기화", size=12, color=TEXT_MUTED)], spacing=8),
                        ft.Row([ft.Icon(ft.Icons.API, size=16, color=TEXT_MUTED), ft.Text("증권사 Open API 연동 및 자동 주문 전송", size=12, color=TEXT_MUTED)], spacing=8),
                        ft.Row([ft.Icon(ft.Icons.WIDGETS_OUTLINED, size=16, color=TEXT_MUTED), ft.Text("안드로이드 바탕화면 실시간 잔고 위젯", size=12, color=TEXT_MUTED)], spacing=8),
                    ],
                    spacing=6
                )
            )
        )

        # 4. 앱 정보 카드
        app_info_card = ft.Container(
            padding=14,
            bgcolor=SURFACE_CARD,
            border=ft.Border.all(1, BORDER_COLOR),
            border_radius=12,
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=18, color=TEXT_MUTED),
                    ft.Column(
                        controls=[
                            ft.Text("종종 투자 모바일 (JongJong Mobile) v1.0.0", size=12, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                            ft.Text("엔진: Python 3.12 & Flutter (Flet 1.0.2) • 데이터: data/accounts.json", size=10, color=TEXT_MUTED),
                        ],
                        spacing=2,
                        expand=True
                    )
                ],
                spacing=10
            )
        )

        return ft.ListView(
            controls=[
                export_card,
                ft.Container(height=6),
                rate_card,
                ft.Container(height=6),
                future_card,
                ft.Container(height=6),
                app_info_card,
                ft.Container(height=20)
            ],
            spacing=8,
            expand=True
        )

    # =================================================================
    # 모달 다이얼로그 (계좌 추가, 계좌 설정, 계좌 삭제, Undo)
    # =================================================================
    def open_add_account_dialog(self, e=None):
        """
        신규 계좌 추가 다이얼로그 (기존 신규 계좌 등록 다이얼로그와 동일)
        """
        today_str = datetime.now().strftime('%Y-%m-%d')
        cnt = len(self.accounts) + 1

        name_f = ft.TextField(label="계좌 별칭", value=f"SOXL 종종이 {cnt}호", border_color=BORDER_COLOR, focused_border_color=ACCENT_BLUE, color=TEXT_PRIMARY)
        ticker_f = ft.TextField(label="종목 티커", value="SOXL", border_color=BORDER_COLOR, focused_border_color=ACCENT_BLUE, color=TEXT_PRIMARY)
        strat_f = ft.Dropdown(
            label="전략 선택",
            value="종종이 기본전략",
            options=[ft.dropdown.Option("종종이 기본전략"), ft.dropdown.Option("무한매수법 v4.0")],
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY
        )
        date_f = ft.TextField(label="시작일 (YYYY-MM-DD)", value=today_str, border_color=BORDER_COLOR, focused_border_color=ACCENT_BLUE, color=TEXT_PRIMARY)
        seed_f = ft.TextField(label="초기 시드 ($)", value="100000", keyboard_type=ft.KeyboardType.NUMBER, border_color=BORDER_COLOR, focused_border_color=ACCENT_BLUE, color=TEXT_PRIMARY)
        reserve_f = ft.TextField(label="위기준비금 비율 (%, 기본 5%)", value="5", keyboard_type=ft.KeyboardType.NUMBER, border_color=BORDER_COLOR, focused_border_color=RESERVE_AMBER, color=TEXT_PRIMARY)
        memo_f = ft.TextField(label="메모 (선택)", value="모바일 실전 운용", border_color=BORDER_COLOR, focused_border_color=ACCENT_BLUE, color=TEXT_PRIMARY)

        def handle_create(evt):
            name = name_f.value.strip()
            ticker = ticker_f.value.strip().upper()
            strat_val = strat_f.value.strip()
            s_d = date_f.value.strip()
            memo = memo_f.value.strip()

            if not name:
                show_toast(self.page, "계좌명을 입력해주세요.", is_error=True)
                return

            try:
                seed = float(seed_f.value.strip())
                res_pct = float(reserve_f.value.strip())
                res_ratio = max(0.0, min(1.0, res_pct / 100.0))
            except Exception:
                show_toast(self.page, "시드 및 위기준비금 숫자를 확인해주세요.", is_error=True)
                return

            new_acc = self.am.add_account(
                name=name,
                strategy=strat_val,
                ticker=ticker,
                start_date=s_d,
                initial_seed=seed,
                memo=memo,
                reserve_ratio=res_ratio
            )
            self.page.pop_dialog()
            show_toast(self.page, f"'{name}' 계좌가 생성되었습니다!")
            self.reload_data()

        dlg = ft.AlertDialog(
            title=ft.Row([ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET, color=ACCENT_BLUE), ft.Text("새 계좌 등록", weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)], spacing=8),
            content=ft.Container(
                width=340,
                content=ft.Column(
                    controls=[name_f, strat_f, ft.Row([ticker_f, date_f], spacing=6), ft.Row([seed_f, reserve_f], spacing=6), memo_f],
                    spacing=8,
                    tight=True
                )
            ),
            actions=[
                ft.TextButton("취소", on_click=lambda _: self.page.pop_dialog()),
                ft.FilledButton("계좌 생성", style=ft.ButtonStyle(bgcolor=ACCENT_BLUE, color=ft.Colors.BLACK), on_click=handle_create)
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=SURFACE_CARD
        )
        self.page.show_dialog(dlg)

    def open_settings_dialog(self, acc_id: str):
        target = next((a for a in self.accounts if a['id'] == acc_id), None)
        if not target:
            return

        cur_reserve_pct = float(target.get('reserve_ratio', 0.05)) * 100.0
        name_f = ft.TextField(label="계좌 별칭", value=target.get('name', ''), border_color=BORDER_COLOR, focused_border_color=ACCENT_BLUE, color=TEXT_PRIMARY)
        seed_f = ft.TextField(label="초기 시드 ($)", value=str(target.get('initial_seed', 100000.0)), keyboard_type=ft.KeyboardType.NUMBER, border_color=BORDER_COLOR, focused_border_color=ACCENT_BLUE, color=TEXT_PRIMARY)

        slider_text = ft.Text(f"위기준비금: {cur_reserve_pct:.1f}%", size=13, weight=ft.FontWeight.BOLD, color=RESERVE_AMBER)
        slider = ft.Slider(min=0, max=20, divisions=20, value=cur_reserve_pct, active_color=RESERVE_AMBER, thumb_color=RESERVE_AMBER)
        slider.on_change = lambda e: (setattr(slider_text, 'value', f"위기준비금: {e.control.value:.1f}%"), self.page.update())

        memo_f = ft.TextField(label="메모", value=target.get('memo', ''), border_color=BORDER_COLOR, focused_border_color=ACCENT_BLUE, color=TEXT_PRIMARY)

        def handle_save(evt):
            try:
                new_name = name_f.value.strip()
                new_seed = float(seed_f.value.strip())
                new_res = slider.value / 100.0
                new_memo = memo_f.value.strip()

                self.am.update_account_settings(acc_id=acc_id, name=new_name, initial_seed=new_seed, reserve_ratio=new_res, memo=new_memo)
                self.page.pop_dialog()
                show_toast(self.page, "계좌 설정이 저장되었습니다.")
                self.reload_data()
            except Exception as ex:
                show_toast(self.page, f"저장 실패: {ex}", is_error=True)

        dlg = ft.AlertDialog(
            title=ft.Row([ft.Icon(ft.Icons.SETTINGS, color=ACCENT_BLUE), ft.Text("계좌 설정 변경", weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)], spacing=8),
            content=ft.Container(
                width=340,
                content=ft.Column(controls=[name_f, seed_f, ft.Container(height=2), slider_text, slider, memo_f], spacing=8, tight=True)
            ),
            actions=[
                ft.TextButton("취소", on_click=lambda _: self.page.pop_dialog()),
                ft.FilledButton("설정 저장", style=ft.ButtonStyle(bgcolor=ACCENT_BLUE, color=ft.Colors.BLACK), on_click=handle_save)
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=SURFACE_CARD
        )
        self.page.show_dialog(dlg)

    def open_delete_account_dialog(self, acc_id: str):
        target = next((a for a in self.accounts if a['id'] == acc_id), None)
        if not target:
            return
        name = target.get('name', '계좌')

        def handle_delete(evt):
            self.page.pop_dialog()
            success = self.am.delete_account(acc_id)
            if success:
                show_toast(self.page, f"'{name}' 계좌가 삭제되었습니다.")
                self.viewing_account_id = None
                self.reload_data()
            else:
                show_toast(self.page, "삭제 실패", is_error=True)

        dlg = ft.AlertDialog(
            title=ft.Row([ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=LOSS_RED), ft.Text("계좌 삭제 확인", weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)], spacing=8),
            content=ft.Text(f"정말로 '{name}' 계좌를 영구 삭제하시겠습니까?\n모든 매매 기록 및 설정이 삭제됩니다.", size=13, color=TEXT_SECONDARY),
            actions=[
                ft.TextButton("닫기", on_click=lambda _: self.page.pop_dialog()),
                ft.FilledButton("계좌 삭제", style=ft.ButtonStyle(bgcolor=LOSS_RED, color=ft.Colors.WHITE), on_click=handle_delete)
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=SURFACE_CARD
        )
        self.page.show_dialog(dlg)

    def open_undo_dialog(self, acc_id: str):
        def handle_undo(evt):
            self.page.pop_dialog()
            ok = self.am.delete_last_day_record(acc_id)
            if ok:
                show_toast(self.page, "최근 거래일 정산 기록이 취소되었습니다.")
                self.reload_data()
            else:
                show_toast(self.page, "취소할 기록이 없습니다.", is_error=True)

        dlg = ft.AlertDialog(
            title=ft.Row([ft.Icon(ft.Icons.UNDO, color=LOSS_RED), ft.Text("거래일 Undo 확인", weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)], spacing=8),
            content=ft.Text("가장 최근 거래일의 정산 기록을 삭제하고 이전 상태로 되돌리시겠습니까?", size=13, color=TEXT_SECONDARY),
            actions=[
                ft.TextButton("닫기", on_click=lambda _: self.page.pop_dialog()),
                ft.FilledButton("취소 실행", style=ft.ButtonStyle(bgcolor=LOSS_RED, color=ft.Colors.WHITE), on_click=handle_undo)
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=SURFACE_CARD
        )
        self.page.show_dialog(dlg)

    def open_edit_trade_dialog(self, acc_id: str, record_idx: int):
        """
        거래 기록을 직접 수정하는 대화상자를 엽니다.
        """
        acc = next((a for a in self.accounts if a['id'] == acc_id), None)
        if not acc:
            return
        records = acc.get('trade_records', [])
        if record_idx < 0 or record_idx >= len(records):
            return

        target = records[record_idx]
        cur_d = str(target.get('Date', ''))
        cur_close = float(target.get('Close', 0.0))
        cur_bq = int(target.get('BuyQty', target.get('R', 0)))
        cur_sq = int(target.get('SellQty', 0))
        cur_profit = float(target.get('Profit', 0.0) or 0.0)

        date_f = ft.TextField(
            label="거래일자 (YYYY-MM-DD)",
            value=cur_d,
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY,
            text_size=12
        )
        close_f = ft.TextField(
            label="종가 ($)",
            value=f"{cur_close:.2f}",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY,
            text_size=12
        )
        buy_q_f = ft.TextField(
            label="체결 매수량 (주)",
            value=str(cur_bq),
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=BORDER_COLOR,
            focused_border_color=PROFIT_GREEN,
            color=TEXT_PRIMARY,
            text_size=12
        )
        sell_q_f = ft.TextField(
            label="체결 매도량 (주)",
            value=str(cur_sq),
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=BORDER_COLOR,
            focused_border_color=LOSS_RED,
            color=TEXT_PRIMARY,
            text_size=12
        )
        profit_f = ft.TextField(
            label="실현 손익 ($)",
            value=f"{cur_profit:.2f}",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=BORDER_COLOR,
            focused_border_color=PROFIT_GREEN,
            color=TEXT_PRIMARY,
            text_size=12
        )

        def handle_save_edit(e):
            try:
                n_date = date_f.value.strip()
                n_close = float(close_f.value.strip())
                n_bq = int(buy_q_f.value.strip())
                n_sq = int(sell_q_f.value.strip())
                n_profit = float(profit_f.value.strip())

                target['Date'] = n_date
                target['Close'] = n_close
                target['BuyQty'] = n_bq
                target['R'] = n_bq
                target['SellQty'] = n_sq
                target['Profit'] = n_profit
                if n_bq > 0 and (target.get('BuyPrice') is None or float(target.get('BuyPrice', 0.0)) <= 0):
                    target['BuyPrice'] = n_close

                # Recompute Asset
                target_hold = int(target.get('Hold', 0))
                target_cash = float(target.get('Cash', 0.0))
                target['Asset'] = round(target_cash + n_close * target_hold, 2)

                self.am.save_accounts(self.accounts)
                self.page.pop_dialog()
                show_toast(self.page, f"{n_date} 거래 내역이 성공적으로 수정되었습니다.")
                self.reload_data()
            except Exception as ex:
                show_toast(self.page, f"수정 저장 오류: {ex}", is_error=True)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.EDIT_NOTE, color=ACCENT_BLUE),
                ft.Text(f"거래 기록 수정 ({cur_d})", weight=ft.FontWeight.BOLD, size=15, color=TEXT_PRIMARY)
            ], spacing=6),
            content=ft.Container(
                width=340,
                content=ft.Column(
                    controls=[
                        date_f,
                        close_f,
                        ft.Row([buy_q_f, sell_q_f], spacing=6),
                        profit_f,
                        ft.Text("💡 수치 변경 후 [수정 저장]을 누르면 계좌 데이터가 갱신됩니다.", size=10, color=TEXT_SECONDARY)
                    ],
                    spacing=10,
                    tight=True
                )
            ),
            actions=[
                ft.TextButton("취소", on_click=lambda _: self.page.pop_dialog()),
                ft.FilledButton(
                    "수정 저장",
                    style=ft.ButtonStyle(bgcolor=ACCENT_BLUE, color=ft.Colors.BLACK),
                    on_click=handle_save_edit
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=SURFACE_CARD
        )
        self.page.show_dialog(dlg)



# =====================================================================
# 애플리케이션 엔트리 포인트
# =====================================================================
def main(page: ft.Page):
    app = MobileTradingApp(page)
    page.add(app.content_container)


if __name__ == "__main__":
    ft.run(main)
