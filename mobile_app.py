"""
=====================================================================
종종이 & 무한매수 주식 매매 시스템 - 모바일/안드로이드 최적화 앱 (Flet)
=====================================================================
스마트폰 화면 비율(412x860)로 PC에서 직접 마우스/터치로 동작을 점검할 수 있으며,
동일한 코드가 Android APK로 직접 빌드(flet build apk) 가능한 크로스플랫폼 모바일 앱입니다.
"""
import sys
import os
import subprocess
from datetime import datetime

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
from gui.account_manager import AccountManager
from core.market_calendar import is_us_trading_day, get_next_trading_day, parse_date


# =====================================================================
# 색상 테마 및 디자인 상수
# =====================================================================
BG_DARK = "#0B0F19"           # 전체 배경 (매우 깊은 다크)
SURFACE_CARD = "#151C2C"      # 카드 배경
SURFACE_CARD_HOVER = "#1E293B"
BORDER_COLOR = "#243049"      # 구분선 및 카드 테두리
ACCENT_BLUE = "#38BDF8"       # 메인 강조 하늘색
PROFIT_GREEN = "#10B981"      # 수익/매수 에메랄드
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
    # 1. Flet Clipboard
    try:
        cb = ft.Clipboard()
        if cb not in page.overlay:
            page.overlay.append(cb)
            page.update()
        cb.set(text)
    except Exception:
        pass

    # 2. Windows clip.exe 백업 복사 (PC 테스트 완벽 호환)
    if sys.platform == "win32":
        try:
            subprocess.run(["clip.exe"], input=text.encode("utf-16"), check=True)
        except Exception:
            try:
                import tkinter as tk
                r = tk.Tk()
                r.withdraw()
                r.clipboard_clear()
                r.clipboard_append(text)
                r.update()
                r.destroy()
            except Exception:
                pass


def show_toast(page: ft.Page, message: str, is_error: bool = False):
    """
    모바일 스타일의 하단 토스트/스낵바 알림을 표시합니다.
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


# =====================================================================
# 메인 앱 애플리케이션
# =====================================================================
class MobileTradingApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.am = AccountManager()
        self.accounts = []
        self.active_account = None
        self.details = None
        self.current_tab_index = 0

        # Flet 기본 창 설정 (스마트폰 크기 및 테마)
        self.page.title = "종종 투자 (JongJong Mobile)"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = BG_DARK
        self.page.padding = 0

        # 데스크톱에서 실행 시 안드로이드 폰 비율로 창 크기 고정
        if hasattr(self.page, "window"):
            self.page.window.width = 412
            self.page.window.height = 860
            self.page.window.resizable = True
            self.page.window.min_width = 360
            self.page.window.min_height = 600

        # 메인 컨테이너
        self.content_container = ft.Container(
            expand=True,
            padding=ft.Padding.only(left=12, right=12, top=8, bottom=8)
        )

        # 상단 네비게이션 바 & 하단 네비게이션 바 생성
        self._setup_app_bar()
        self._setup_bottom_nav()

        # 데이터 초기 로드
        self.reload_data()

    def _setup_app_bar(self):
        self.title_text = ft.Text("종종 투자", size=16, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
        self.subtitle_text = ft.Text("", size=11, color=TEXT_SECONDARY)

        self.account_dropdown_button = ft.OutlinedButton(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, size=15, color=ACCENT_BLUE),
                    ft.Text("계좌 선택", size=12, weight=ft.FontWeight.W_600, color=TEXT_PRIMARY),
                    ft.Icon(ft.Icons.ARROW_DROP_DOWN, size=18, color=TEXT_SECONDARY)
                ],
                spacing=4,
                alignment=ft.MainAxisAlignment.CENTER
            ),
            style=ft.ButtonStyle(
                padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                shape=ft.RoundedRectangleBorder(radius=8),
                side=ft.BorderSide(1, BORDER_COLOR)
            ),
            on_click=self.open_account_switcher
        )

        self.page.appbar = ft.AppBar(
            leading=ft.Container(
                content=ft.Icon(ft.Icons.SAVINGS_OUTLINED, color=ACCENT_BLUE, size=22),
                padding=ft.Padding.only(left=12)
            ),
            title=ft.Column(
                controls=[self.title_text, self.subtitle_text],
                spacing=1,
                alignment=ft.MainAxisAlignment.CENTER
            ),
            actions=[
                ft.IconButton(
                    icon=ft.Icons.REFRESH_ROUNDED,
                    icon_color=TEXT_SECONDARY,
                    tooltip="새로고침",
                    on_click=lambda e: self.reload_data(show_message=True)
                ),
                ft.IconButton(
                    icon=ft.Icons.SETTINGS_OUTLINED,
                    icon_color=TEXT_SECONDARY,
                    tooltip="계좌 설정",
                    on_click=self.open_settings_dialog
                ),
                ft.IconButton(
                    icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                    icon_color=ACCENT_BLUE,
                    tooltip="새 계좌 추가",
                    on_click=self.open_add_account_dialog
                ),
            ],
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
                    icon=ft.Icons.RECEIPT_LONG_OUTLINED,
                    selected_icon=ft.Icons.RECEIPT_LONG_ROUNDED,
                    label="주문표"
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.FLASH_ON_OUTLINED,
                    selected_icon=ft.Icons.FLASH_ON_ROUNDED,
                    label="일일정산"
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.HISTORY_ROUNDED,
                    selected_icon=ft.Icons.HISTORY_TOGGLE_OFF,
                    label="매매일지"
                ),
            ],
            on_change=self.on_nav_change
        )
        self.page.navigation_bar = self.bottom_nav

    def reload_data(self, target_acc_id: str = None, show_message: bool = False):
        """
        계좌 목록 및 활성 계좌의 상태를 재계산하고 화면을 갱신합니다.
        """
        self.accounts = self.am.load_accounts()

        if not self.accounts:
            self.active_account = None
            self.details = None
            self.title_text.value = "계좌 없음"
            self.subtitle_text.value = "우측 상단 + 버튼으로 새 계좌를 추가하세요"
            self.content_container.content = self._build_empty_view()
            self.page.update()
            return

        # 활성 계좌 결정
        if target_acc_id:
            matched = next((a for a in self.accounts if a['id'] == target_acc_id), None)
            self.active_account = matched if matched else self.accounts[0]
        elif self.active_account:
            curr_id = self.active_account['id']
            matched = next((a for a in self.accounts if a['id'] == curr_id), None)
            self.active_account = matched if matched else self.accounts[0]
        else:
            self.active_account = self.accounts[0]

        # 계좌 세부 연산 수행 (지표, 주문표, 매매일지 등)
        try:
            self.details = self.am.compute_account_details(self.active_account)
        except Exception as ex:
            print(f"계좌 세부 연산 오류: {ex}")
            self.details = None

        # 상단 AppBar 타이틀 갱신
        acc_name = self.active_account.get('name', '계좌')
        ticker = self.active_account.get('ticker', 'TQQQ')
        strat = self.active_account.get('strategy', '종종이 기본전략')
        reserve_pct = float(self.active_account.get('reserve_ratio', 0.05)) * 100.0

        self.title_text.value = f"{acc_name} ({ticker})"
        self.subtitle_text.value = f"{strat} • 위기준비금 {reserve_pct:.1f}%"

        # 현재 탭 렌더링
        self._render_current_tab()

        if show_message:
            show_toast(self.page, "데이터가 새로고침되었습니다.")

    def on_nav_change(self, e):
        self.current_tab_index = e.control.selected_index
        self._render_current_tab()

    def _render_current_tab(self):
        if not self.active_account or not self.details:
            self.content_container.content = self._build_empty_view()
            self.page.update()
            return

        if self.current_tab_index == 0:
            self.content_container.content = self._build_home_tab()
        elif self.current_tab_index == 1:
            self.content_container.content = self._build_orders_tab()
        elif self.current_tab_index == 2:
            self.content_container.content = self._build_settlement_tab()
        elif self.current_tab_index == 3:
            self.content_container.content = self._build_history_tab()

        self.page.update()

    def _build_empty_view(self):
        return ft.Column(
            controls=[
                ft.Container(height=100),
                ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, size=64, color=TEXT_MUTED),
                ft.Text("등록된 계좌가 없습니다.", size=16, weight=ft.FontWeight.W_600, color=TEXT_SECONDARY),
                ft.Text("종종이 8분할 운용을 시작하려면\n새 계좌를 만들어주세요.", size=13, color=TEXT_MUTED, text_align=ft.TextAlign.CENTER),
                ft.Container(height=16),
                ft.FilledButton(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.ADD, size=18),
                            ft.Text("첫 계좌 생성하기", weight=ft.FontWeight.BOLD)
                        ],
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

    # =================================================================
    # TAB 0: 🏠 홈 / 계좌 대시보드
    # =================================================================
    def _build_home_tab(self):
        d = self.details
        total_asset = d.get('current_asset', 0.0)
        krw_asset = total_asset * EXCHANGE_RATE
        total_return_pct = d.get('total_return_pct', 0.0)
        total_profit = d.get('total_profit', 0.0)
        initial_seed = d.get('initial_seed', 0.0)

        ar_val = d.get('ar_val', 0.0)
        ak_val = d.get('ak_val', 0.0)
        reserve_ratio = d.get('reserve_ratio', 0.05) * 100.0
        cash = d.get('current_cash', 0.0)
        hold = d.get('current_hold', 0)
        avg_p = d.get('avg_price', 0.0)
        stock_eval = hold * d.get('current_price', avg_p)

        budget = d.get('daily_budget', 0.0)
        mode = d.get('mode', 'Normal')
        op_state = d.get('operational_state', 'WAITING_FOR_FILL')
        target_date = d.get('target_order_date', '')

        is_profit = total_profit >= 0
        profit_color = PROFIT_GREEN if is_profit else LOSS_RED
        profit_icon = ft.Icons.ARROW_DROP_UP if is_profit else ft.Icons.ARROW_DROP_DOWN

        # 1. 메인 자산 히어로 카드
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
                                ft.Text("총 평가 자산", size=13, color=TEXT_SECONDARY, weight=ft.FontWeight.W_500),
                                ft.Container(
                                    content=ft.Text(
                                        "🟢 주문대기" if op_state == 'WAITING_FOR_FILL' else "⚪ 마감완료",
                                        size=11,
                                        color=PROFIT_GREEN if op_state == 'WAITING_FOR_FILL' else TEXT_SECONDARY,
                                        weight=ft.FontWeight.BOLD
                                    ),
                                    bgcolor=ft.Colors.with_opacity(0.12, PROFIT_GREEN if op_state == 'WAITING_FOR_FILL' else TEXT_SECONDARY),
                                    padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                                    border_radius=12
                                )
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        ft.Container(height=4),
                        ft.Text(f"${total_asset:,.2f}", size=30, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        ft.Text(f"약 {krw_asset:,.0f}원 (환율 {EXCHANGE_RATE:,.0f}원)", size=12, color=TEXT_MUTED),
                        ft.Container(height=10),
                        ft.Divider(color=BORDER_COLOR, height=1),
                        ft.Container(height=6),
                        ft.Row(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Icon(profit_icon, color=profit_color, size=20),
                                        ft.Text(f"{total_return_pct:+.2f}%", size=14, weight=ft.FontWeight.BOLD, color=profit_color),
                                        ft.Text(f"({total_profit:+,.2f}달러)", size=12, color=profit_color),
                                    ],
                                    spacing=2
                                ),
                                ft.Text(f"원금: ${initial_seed:,.0f}", size=12, color=TEXT_SECONDARY)
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        )
                    ]
                )
            )
        )

        # 2. 시장 모드 및 당일 운용 배너
        mode_banner = ft.Container(
            bgcolor=ft.Colors.with_opacity(0.15, ACCENT_BLUE),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.3, ACCENT_BLUE)),
            border_radius=12,
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.TRENDING_UP, color=ACCENT_BLUE, size=20),
                    ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text(f"{mode} 모드 (8분할 운용)", size=12, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                                    ft.Container(
                                        content=ft.Text(f"기준: {target_date}", size=10, color=ACCENT_BLUE),
                                        padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                        bgcolor=ft.Colors.with_opacity(0.2, ACCENT_BLUE),
                                        border_radius=6
                                    )
                                ],
                                spacing=8
                            ),
                            ft.Text(f"하루 매수 배분 예산: ${budget:,.2f} (실가동시드의 1/8)", size=11, color=TEXT_SECONDARY)
                        ],
                        spacing=2,
                        expand=True
                    )
                ],
                spacing=10
            )
        )

        # 3. 4대 핵심 지표 그리드
        def make_metric_card(title, value, subtext, icon, icon_color, border_tint=None):
            return ft.Container(
                bgcolor=SURFACE_CARD,
                border=ft.Border.all(1, border_tint or BORDER_COLOR),
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
                        ft.Container(height=4),
                        ft.Text(value, size=16, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        ft.Text(subtext, size=10, color=TEXT_MUTED)
                    ],
                    spacing=1
                )
            )

        row1 = ft.Row(
            controls=[
                make_metric_card("🛡️ 위기준비금 (AK)", f"${ak_val:,.0f}", f"{reserve_ratio:.1f}% 폭락 안전판", ft.Icons.SHIELD_OUTLINED, RESERVE_AMBER, ft.Colors.with_opacity(0.3, RESERVE_AMBER)),
                make_metric_card("🚀 실가동 시드 (AR)", f"${ar_val:,.0f}", f"{100-reserve_ratio:.1f}% 8분할 엔진", ft.Icons.ROCKET_LAUNCH_OUTLINED, ACCENT_BLUE),
            ],
            spacing=8
        )

        row2 = ft.Row(
            controls=[
                make_metric_card("💵 예수금 (Cash)", f"${cash:,.2f}", "매수 대기 자금", ft.Icons.ATTACH_MONEY, PROFIT_GREEN),
                make_metric_card("📈 보유 주식", f"{hold:,}주", f"평단 ${avg_p:,.2f} (약 ${stock_eval:,.0f})", ft.Icons.PIE_CHART_OUTLINE, ft.Colors.PURPLE_300),
            ],
            spacing=8
        )

        # 4. 빠른 바로가기 버튼들
        quick_actions = ft.Row(
            controls=[
                ft.FilledButton(
                    content=ft.Row(
                        controls=[ft.Icon(ft.Icons.RECEIPT_LONG, size=16), ft.Text("당일 주문표", size=13, weight=ft.FontWeight.BOLD)],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=6
                    ),
                    style=ft.ButtonStyle(
                        bgcolor=ACCENT_BLUE,
                        color=ft.Colors.BLACK,
                        shape=ft.RoundedRectangleBorder(radius=10),
                        padding=ft.Padding.symmetric(vertical=12)
                    ),
                    expand=True,
                    on_click=lambda e: self._goto_tab(1)
                ),
                ft.FilledButton(
                    content=ft.Row(
                        controls=[ft.Icon(ft.Icons.FLASH_ON, size=16), ft.Text("일일 정산", size=13, weight=ft.FontWeight.BOLD)],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=6
                    ),
                    style=ft.ButtonStyle(
                        bgcolor=PROFIT_GREEN,
                        color=ft.Colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=10),
                        padding=ft.Padding.symmetric(vertical=12)
                    ),
                    expand=True,
                    on_click=lambda e: self._goto_tab(2)
                )
            ],
            spacing=8
        )

        return ft.ListView(
            controls=[
                hero_card,
                ft.Container(height=8),
                mode_banner,
                ft.Container(height=8),
                row1,
                row2,
                ft.Container(height=12),
                quick_actions,
                ft.Container(height=16),
            ],
            spacing=6,
            expand=True
        )

    def _goto_tab(self, index: int):
        self.bottom_nav.selected_index = index
        self.current_tab_index = index
        self._render_current_tab()

    # =================================================================
    # TAB 1: 📋 당일 주문표 (LOC 퉁치기 반영)
    # =================================================================
    def _build_orders_tab(self):
        d = self.details
        target_date = d.get('target_order_date', '')
        sell_orders = d.get('sell_orders', [])
        buy_orders = d.get('buy_orders', [])
        ticker = d.get('ticker', 'TQQQ')
        budget = d.get('daily_budget', 0.0)

        # 복사 버튼 클릭 핸들러
        def handle_copy_orders(e):
            lines = [
                f"[{ticker} 당일 주문표 - {target_date}]",
                f"전략: {d.get('strategy_name', '종종이')} ({d.get('mode', 'Normal')} 모드)",
                f"하루 배분 예산: ${budget:,.2f}",
                "----------------------------------------"
            ]
            if sell_orders:
                lines.append("■ LOC 매도 주문:")
                for s in sell_orders:
                    lines.append(f"  • {s.get('구분', '매도')}: {s.get('주문단가', '')} | {s.get('주문수량', '')} | {s.get('체결조건', '')}")
            if buy_orders:
                lines.append("■ LOC 매수 주문 (퉁치기 순매수):")
                for b in buy_orders:
                    lines.append(f"  • {b.get('호가단계', '매수')}: {b.get('주문단가', '')} | {b.get('주문수량', '')} | {b.get('체결조건', '')}")
            lines.append("----------------------------------------")
            lines.append("※ 위기준비금(AK)이 제외된 안전 예산 주문입니다.")

            copy_text = "\n".join(lines)
            copy_text_to_clipboard(self.page, copy_text)
            show_toast(self.page, "주문표가 클립보드에 복사되었습니다! 증권사 앱에 붙여넣기 하세요.")

        # 상단 헤더 및 복사 버튼
        header_card = ft.Container(
            bgcolor=SURFACE_CARD,
            border=ft.Border.all(1, BORDER_COLOR),
            border_radius=12,
            padding=12,
            content=ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text(f"📅 {target_date} 주문표", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                            ft.Text(f"LOC 퉁치기 반영 순주문 ({ticker})", size=11, color=TEXT_SECONDARY),
                        ],
                        spacing=2,
                        expand=True
                    ),
                    ft.FilledButton(
                        content=ft.Row(
                            controls=[ft.Icon(ft.Icons.CONTENT_COPY_ROUNDED, size=15), ft.Text("주문 복사", size=12, weight=ft.FontWeight.BOLD)],
                            spacing=4
                        ),
                        style=ft.ButtonStyle(
                            bgcolor=ACCENT_BLUE,
                            color=ft.Colors.BLACK,
                            shape=ft.RoundedRectangleBorder(radius=8),
                            padding=ft.Padding.symmetric(horizontal=10, vertical=8)
                        ),
                        on_click=handle_copy_orders
                    )
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            )
        )

        order_cards = []

        # 1. 매도 주문 카드 생성
        if sell_orders:
            order_cards.append(ft.Text("🔴 LOC 매도 주문", size=13, weight=ft.FontWeight.BOLD, color=LOSS_RED))
            for s in sell_orders:
                title = s.get('구분', '익절 매도')
                price = s.get('주문단가', '$0.00')
                qty = s.get('주문수량', '0주')
                amt = s.get('예상금액', '$0.00')
                cond = s.get('체결조건', '')
                note = s.get('비고', '')

                card = ft.Container(
                    bgcolor=SURFACE_CARD,
                    border=ft.Border.all(1, ft.Colors.with_opacity(0.4, LOSS_RED)),
                    border_radius=10,
                    padding=12,
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Container(
                                        content=ft.Text("LOC 매도", size=10, weight=ft.FontWeight.BOLD, color=LOSS_RED),
                                        bgcolor=ft.Colors.with_opacity(0.15, LOSS_RED),
                                        padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                        border_radius=4
                                    ),
                                    ft.Text(title, size=12, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                                ],
                                spacing=8
                            ),
                            ft.Container(height=4),
                            ft.Row(
                                controls=[
                                    ft.Column([
                                        ft.Text("주문 단가", size=10, color=TEXT_SECONDARY),
                                        ft.Text(price, size=16, weight=ft.FontWeight.BOLD, color=LOSS_RED)
                                    ], spacing=1),
                                    ft.Column([
                                        ft.Text("주문 수량", size=10, color=TEXT_SECONDARY),
                                        ft.Text(qty, size=16, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                                    ], spacing=1),
                                    ft.Column([
                                        ft.Text("예상 금액", size=10, color=TEXT_SECONDARY),
                                        ft.Text(amt, size=14, weight=ft.FontWeight.W_600, color=TEXT_PRIMARY)
                                    ], spacing=1),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                            ),
                            ft.Container(height=4),
                            ft.Divider(color=BORDER_COLOR, height=1),
                            ft.Container(height=2),
                            ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=13, color=TEXT_MUTED),
                                    ft.Text(cond, size=11, color=TEXT_MUTED, expand=True)
                                ],
                                spacing=4
                            ),
                            ft.Text(f"💡 {note}", size=10, color=TEXT_MUTED) if note else ft.Container()
                        ],
                        spacing=2
                    )
                )
                order_cards.append(card)

        # 2. 매수 주문 카드 생성
        if buy_orders:
            order_cards.append(ft.Container(height=4))
            order_cards.append(ft.Text("🟢 LOC 매수 주문 (퉁치기 상계 순매수)", size=13, weight=ft.FontWeight.BOLD, color=PROFIT_GREEN))
            for b in buy_orders:
                stage = b.get('호가단계', '순매수')
                price = b.get('주문단가', '$0.00')
                qty = b.get('주문수량', '0주')
                amt = b.get('예상금액', '$0.00')
                cond = b.get('체결조건', '')
                note = b.get('비고', '')

                card = ft.Container(
                    bgcolor=SURFACE_CARD,
                    border=ft.Border.all(1, ft.Colors.with_opacity(0.3, PROFIT_GREEN)),
                    border_radius=10,
                    padding=12,
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Container(
                                        content=ft.Text("LOC 매수", size=10, weight=ft.FontWeight.BOLD, color=PROFIT_GREEN),
                                        bgcolor=ft.Colors.with_opacity(0.15, PROFIT_GREEN),
                                        padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                        border_radius=4
                                    ),
                                    ft.Text(stage, size=12, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY, expand=True),
                                ],
                                spacing=8
                            ),
                            ft.Container(height=4),
                            ft.Row(
                                controls=[
                                    ft.Column([
                                        ft.Text("주문 단가", size=10, color=TEXT_SECONDARY),
                                        ft.Text(price, size=16, weight=ft.FontWeight.BOLD, color=PROFIT_GREEN)
                                    ], spacing=1),
                                    ft.Column([
                                        ft.Text("주문 수량", size=10, color=TEXT_SECONDARY),
                                        ft.Text(qty, size=16, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                                    ], spacing=1),
                                    ft.Column([
                                        ft.Text("예상 금액", size=10, color=TEXT_SECONDARY),
                                        ft.Text(amt, size=14, weight=ft.FontWeight.W_600, color=TEXT_PRIMARY)
                                    ], spacing=1),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                            ),
                            ft.Container(height=4),
                            ft.Divider(color=BORDER_COLOR, height=1),
                            ft.Container(height=2),
                            ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=13, color=TEXT_MUTED),
                                    ft.Text(cond, size=11, color=TEXT_MUTED, expand=True)
                                ],
                                spacing=4
                            ),
                            ft.Text(f"💡 {note}", size=10, color=TEXT_MUTED) if note else ft.Container()
                        ],
                        spacing=2
                    )
                )
                order_cards.append(card)

        # 안내 푸터
        footer = ft.Container(
            padding=ft.Padding.all(12),
            bgcolor=ft.Colors.with_opacity(0.1, RESERVE_AMBER),
            border_radius=10,
            border=ft.Border.all(1, ft.Colors.with_opacity(0.2, RESERVE_AMBER)),
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=16, color=RESERVE_AMBER),
                    ft.Text(
                        f"위기준비금(AK ${d.get('ak_val', 0.0):,.0f})이 보호된 상태로 하루 배분 예산(${budget:,.2f}) 한도 내에서 안전하게 생성되었습니다.",
                        size=11,
                        color=TEXT_SECONDARY,
                        expand=True
                    )
                ],
                spacing=8
            )
        )

        return ft.ListView(
            controls=[
                header_card,
                ft.Container(height=4),
                *order_cards,
                ft.Container(height=8),
                footer,
                ft.Container(height=16),
            ],
            spacing=8,
            expand=True
        )

    # =================================================================
    # TAB 2: ⚡ 일일 정산 / Next Day 진행
    # =================================================================
    def _build_settlement_tab(self):
        d = self.details
        acc_id = self.active_account['id']
        op_state = d.get('operational_state', 'WAITING_FOR_FILL')
        curr_d = d.get('current_date', '')
        latest_close = d.get('current_price', 0.0)

        # 추천 체결 수량 (1차 매수 주문 수량 파싱)
        default_buy_q = 0
        buy_orders = d.get('buy_orders', [])
        if buy_orders:
            first_b = buy_orders[0]
            raw_q = str(first_b.get('주문수량', '0')).replace('주', '').replace(',', '').strip()
            try:
                default_buy_q = int(raw_q)
            except Exception:
                default_buy_q = 0

        # 입력 필드들
        close_field = ft.TextField(
            label="당일 종가 ($)",
            value=f"{latest_close:.2f}" if latest_close > 0 else "142.50",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY,
            text_size=14,
            content_padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            expand=True
        )

        buy_qty_field = ft.TextField(
            label="체결 매수 수량 (주)",
            value=str(default_buy_q),
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=BORDER_COLOR,
            focused_border_color=PROFIT_GREEN,
            color=TEXT_PRIMARY,
            text_size=14,
            content_padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            expand=True
        )

        sell_qty_field = ft.TextField(
            label="체결 매도 수량 (주)",
            value="0",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=BORDER_COLOR,
            focused_border_color=LOSS_RED,
            color=TEXT_PRIMARY,
            text_size=14,
            content_padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            expand=True
        )

        fill_price_field = ft.TextField(
            label="실제 매수 체결 단가 ($)",
            value=f"{latest_close:.2f}" if latest_close > 0 else "142.50",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY,
            text_size=14,
            content_padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            expand=True
        )

        memo_field = ft.TextField(
            label="정산 메모 (선택)",
            hint_text="특이사항 기록",
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY,
            text_size=13,
            content_padding=ft.Padding.symmetric(horizontal=12, vertical=10)
        )

        # 정산 완료 확정 핸들러
        def handle_confirm_settle(e):
            try:
                c_p = float(close_field.value.strip())
                b_q = int(buy_qty_field.value.strip())
                s_q = int(sell_qty_field.value.strip())
                f_p = float(fill_price_field.value.strip()) if fill_price_field.value.strip() else c_p
                note = memo_field.value.strip()

                if c_p <= 0:
                    show_toast(self.page, "유효한 당일 종가를 입력하세요.", is_error=True)
                    return

                res = self.am.record_daily_close(
                    acc_id=acc_id,
                    close_price=c_p,
                    buy_qty=b_q,
                    sell_qty=s_q,
                    buy_price=f_p,
                    memo=note
                )
                if res:
                    show_toast(self.page, f"{curr_d} 장 마감 정산이 완료되었습니다!")
                    self.reload_data(target_acc_id=acc_id)
                else:
                    show_toast(self.page, "정산 처리에 실패했습니다.", is_error=True)
            except ValueError:
                show_toast(self.page, "숫자 입력 형식을 확인해주세요.", is_error=True)
            except Exception as ex:
                show_toast(self.page, f"정산 중 오류: {ex}", is_error=True)

        # 다음 거래일 진행 핸들러
        def handle_advance_next_day(e):
            res = self.am.advance_next_day(acc_id)
            if res:
                new_date = res.get('current_date')
                show_toast(self.page, f"다음 거래일({new_date})로 진행되었습니다!")
                self.reload_data(target_acc_id=acc_id)
            else:
                show_toast(self.page, "다음 거래일 진행에 실패했습니다.", is_error=True)

        # 상태 안내 배너
        if op_state == 'WAITING_FOR_FILL':
            status_banner = ft.Container(
                bgcolor=ft.Colors.with_opacity(0.12, PROFIT_GREEN),
                border=ft.Border.all(1, ft.Colors.with_opacity(0.3, PROFIT_GREEN)),
                border_radius=12,
                padding=14,
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.SCHEDULE, color=PROFIT_GREEN, size=24),
                        ft.Column(
                            controls=[
                                ft.Text(f"운용 기준일: {curr_d} (장전 대기 중)", size=13, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                                ft.Text("미국 장 마감 후 당일 종가와 체결 내역을 입력하고 정산을 완료하세요.", size=11, color=TEXT_SECONDARY),
                            ],
                            spacing=2,
                            expand=True
                        )
                    ],
                    spacing=10
                )
            )
        else:
            status_banner = ft.Container(
                bgcolor=ft.Colors.with_opacity(0.12, ACCENT_BLUE),
                border=ft.Border.all(1, ft.Colors.with_opacity(0.3, ACCENT_BLUE)),
                border_radius=12,
                padding=14,
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color=ACCENT_BLUE, size=24),
                        ft.Column(
                            controls=[
                                ft.Text(f"{curr_d} 마감 정산 완료!", size=13, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                                ft.Text("아래 [다음 거래일(Next Day) 진행] 버튼을 눌러 다음 증시 개장일로 이동하세요.", size=11, color=TEXT_SECONDARY),
                            ],
                            spacing=2,
                            expand=True
                        )
                    ],
                    spacing=10
                )
            )

        # 정산 입력 폼 카드
        form_card = ft.Card(
            bgcolor=SURFACE_CARD,
            elevation=2,
            shape=ft.RoundedRectangleBorder(radius=14),
            content=ft.Container(
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.EDIT_DOCUMENT, size=18, color=ACCENT_BLUE),
                                ft.Text("당일 체결 및 종가 입력", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                            ],
                            spacing=6
                        ),
                        ft.Container(height=4),
                        ft.Row(controls=[close_field, fill_price_field], spacing=8),
                        ft.Row(controls=[buy_qty_field, sell_qty_field], spacing=8),
                        memo_field,
                        ft.Container(height=6),
                        ft.FilledButton(
                            content=ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.SAVE, size=16),
                                    ft.Text("당일 정산 및 마감 확정", size=13, weight=ft.FontWeight.BOLD)
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                                spacing=6
                            ),
                            style=ft.ButtonStyle(
                                bgcolor=PROFIT_GREEN,
                                color=ft.Colors.WHITE,
                                shape=ft.RoundedRectangleBorder(radius=10),
                                padding=ft.Padding.symmetric(vertical=12)
                            ),
                            width=380,
                            on_click=handle_confirm_settle
                        )
                    ],
                    spacing=10
                )
            )
        )

        # 다음 거래일 진행 버튼 카드
        next_day_button = ft.FilledButton(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.FAST_FORWARD_ROUNDED, size=18),
                    ft.Text("다음 거래일(Next Day)로 진행", size=14, weight=ft.FontWeight.BOLD)
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8
            ),
            style=ft.ButtonStyle(
                bgcolor=ACCENT_BLUE,
                color=ft.Colors.BLACK,
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.Padding.symmetric(vertical=13)
            ),
            width=380,
            on_click=handle_advance_next_day
        )

        # 마지막 거래일 Undo 버튼
        undo_button = ft.OutlinedButton(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.UNDO, size=16, color=LOSS_RED),
                    ft.Text("최근 거래일 기록 취소 (Undo)", size=12, color=LOSS_RED, weight=ft.FontWeight.W_600)
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=6
            ),
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=10),
                side=ft.BorderSide(1, ft.Colors.with_opacity(0.4, LOSS_RED)),
                padding=ft.Padding.symmetric(vertical=10)
            ),
            width=380,
            on_click=lambda e: self.open_undo_dialog()
        )

        return ft.ListView(
            controls=[
                status_banner,
                ft.Container(height=4),
                form_card,
                ft.Container(height=6),
                next_day_button,
                ft.Container(height=4),
                undo_button,
                ft.Container(height=20),
            ],
            spacing=8,
            expand=True
        )

    # =================================================================
    # TAB 3: 📜 매매 일지 (Trade Log History)
    # =================================================================
    def _build_history_tab(self):
        records = self.active_account.get('trade_records', [])

        if not records:
            return ft.Column(
                controls=[
                    ft.Container(height=80),
                    ft.Icon(ft.Icons.HISTORY_TOGGLE_OFF, size=56, color=TEXT_MUTED),
                    ft.Text("아직 저장된 매매 일지가 없습니다.", size=15, weight=ft.FontWeight.W_600, color=TEXT_SECONDARY),
                    ft.Text("첫 거래일 정산을 완료하면 이곳에 누적 기록됩니다.", size=12, color=TEXT_MUTED, text_align=ft.TextAlign.CENTER)
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True
            )

        # 요약 헤더
        total_recs = len(records)
        cum_profit = sum(float(r.get('Profit', 0.0) or 0.0) for r in records)
        p_color = PROFIT_GREEN if cum_profit >= 0 else LOSS_RED

        summary_card = ft.Container(
            bgcolor=SURFACE_CARD,
            border=ft.Border.all(1, BORDER_COLOR),
            border_radius=12,
            padding=14,
            content=ft.Row(
                controls=[
                    ft.Column([
                        ft.Text("누적 운용 기록", size=11, color=TEXT_SECONDARY),
                        ft.Text(f"{total_recs} 거래일", size=16, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                    ], spacing=1),
                    ft.Column([
                        ft.Text("누적 실현 손익", size=11, color=TEXT_SECONDARY),
                        ft.Text(f"{cum_profit:+,.2f}달러", size=16, weight=ft.FontWeight.BOLD, color=p_color)
                    ], spacing=1),
                ],
                alignment=ft.MainAxisAlignment.SPACE_AROUND
            )
        )

        history_items = []
        # 최신 기록이 맨 위로 오도록 역순(reversed) 정렬
        for r in reversed(records):
            d_str = r.get('Date', '')
            c_p = float(r.get('Close', 0.0))
            b_q = int(r.get('BuyQty', r.get('R', 0)))
            b_p = float(r.get('BuyPrice', c_p))
            s_q = int(r.get('SellQty', 0))
            profit = float(r.get('Profit', 0.0) or 0.0)
            cash = float(r.get('Cash', 0.0))
            hold = int(r.get('Hold', 0))
            asset = float(r.get('Asset', 0.0))
            status_text = r.get('StatusText', '')
            mode = r.get('Mode', 'Normal')

            tag_color = PROFIT_GREEN if b_q > 0 else (LOSS_RED if s_q > 0 else TEXT_MUTED)

            card = ft.Container(
                bgcolor=SURFACE_CARD,
                border=ft.Border.all(1, BORDER_COLOR),
                border_radius=10,
                padding=12,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Text(d_str, size=13, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                                        ft.Container(
                                            content=ft.Text(mode, size=9, color=TEXT_SECONDARY),
                                            padding=ft.Padding.symmetric(horizontal=5, vertical=1),
                                            bgcolor=ft.Colors.with_opacity(0.15, TEXT_SECONDARY),
                                            border_radius=4
                                        )
                                    ],
                                    spacing=6
                                ),
                                ft.Text(
                                    f"실현손익: {profit:+,.2f}달러" if s_q > 0 else f"종가: ${c_p:.2f}",
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                    color=PROFIT_GREEN if profit > 0 else (LOSS_RED if profit < 0 else TEXT_SECONDARY)
                                )
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        ft.Container(height=4),
                        ft.Row(
                            controls=[
                                ft.Column([
                                    ft.Text("매수/매도", size=10, color=TEXT_MUTED),
                                    ft.Text(f"+{b_q}주 / -{s_q}주", size=12, weight=ft.FontWeight.W_600, color=TEXT_PRIMARY)
                                ], spacing=1),
                                ft.Column([
                                    ft.Text("보유 잔고", size=10, color=TEXT_MUTED),
                                    ft.Text(f"{hold:,}주", size=12, weight=ft.FontWeight.W_600, color=TEXT_PRIMARY)
                                ], spacing=1),
                                ft.Column([
                                    ft.Text("예수금", size=10, color=TEXT_MUTED),
                                    ft.Text(f"${cash:,.0f}", size=12, weight=ft.FontWeight.W_600, color=TEXT_PRIMARY)
                                ], spacing=1),
                                ft.Column([
                                    ft.Text("총 자산", size=10, color=TEXT_MUTED),
                                    ft.Text(f"${asset:,.0f}", size=12, weight=ft.FontWeight.BOLD, color=ACCENT_BLUE)
                                ], spacing=1),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        ft.Container(height=4),
                        ft.Text(f"상태: {status_text}", size=10, color=TEXT_SECONDARY) if status_text else ft.Container()
                    ],
                    spacing=2
                )
            )
            history_items.append(card)

        return ft.ListView(
            controls=[
                summary_card,
                ft.Container(height=6),
                *history_items,
                ft.Container(height=20)
            ],
            spacing=8,
            expand=True
        )

    # =================================================================
    # 모달 / 다이얼로그 (계좌 전환, 추가, 설정, 실행 취소)
    # =================================================================
    def open_account_switcher(self, e=None):
        """
        계좌 목록을 보여주고 선택 또는 변경하는 모달 바텀시트
        """
        def handle_select(acc_id):
            self.page.pop_dialog()
            self.reload_data(target_acc_id=acc_id)

        items = []
        for a in self.accounts:
            is_cur = self.active_account and a['id'] == self.active_account['id']
            item = ft.ListTile(
                leading=ft.Icon(
                    ft.Icons.CHECK_CIRCLE if is_cur else ft.Icons.RADIO_BUTTON_UNCHECKED,
                    color=ACCENT_BLUE if is_cur else TEXT_MUTED
                ),
                title=ft.Text(a.get('name', '계좌'), weight=ft.FontWeight.BOLD if is_cur else ft.FontWeight.NORMAL, color=TEXT_PRIMARY),
                subtitle=ft.Text(f"{a.get('ticker', 'TQQQ')} • 시드 ${a.get('initial_seed', 0.0):,.0f} • 위기 {float(a.get('reserve_ratio', 0.05))*100:.0f}%", size=11, color=TEXT_SECONDARY),
                on_click=lambda evt, aid=a['id']: handle_select(aid)
            )
            items.append(item)

        bs = ft.BottomSheet(
            content=ft.Container(
                padding=18,
                bgcolor=SURFACE_CARD,
                border_radius=ft.BorderRadius.only(top_left=16, top_right=16),
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Text("운용 계좌 선택", size=15, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                                ft.IconButton(icon=ft.Icons.CLOSE, on_click=lambda _: self.page.pop_dialog())
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        ft.Divider(color=BORDER_COLOR, height=1),
                        *items,
                        ft.Container(height=8),
                        ft.FilledButton(
                            content=ft.Row(
                                controls=[ft.Icon(ft.Icons.ADD, size=16), ft.Text("새 계좌 추가")],
                                alignment=ft.MainAxisAlignment.CENTER,
                                spacing=6
                            ),
                            style=ft.ButtonStyle(
                                bgcolor=ACCENT_BLUE,
                                color=ft.Colors.BLACK,
                                shape=ft.RoundedRectangleBorder(radius=8),
                                padding=ft.Padding.symmetric(vertical=10)
                            ),
                            width=380,
                            on_click=lambda _: (self.page.pop_dialog(), self.open_add_account_dialog())
                        )
                    ],
                    spacing=6,
                    tight=True
                )
            )
        )
        self.page.show_dialog(bs)

    def open_add_account_dialog(self, e=None):
        """
        신규 계좌 추가 다이얼로그 (디폴트: 시작일=오늘, 시드=$100,000, 위기준비금=5%)
        """
        today_str = datetime.now().strftime('%Y-%m-%d')
        existing_count = len(self.accounts) + 1

        name_field = ft.TextField(
            label="계좌 별칭",
            value=f"SOXL 종종이 {existing_count}호",
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY
        )
        ticker_field = ft.TextField(
            label="종목 티커",
            value="SOXL",
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY
        )
        start_date_field = ft.TextField(
            label="시작일 (YYYY-MM-DD)",
            value=today_str,
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY
        )
        seed_field = ft.TextField(
            label="초기 시드 머니 ($)",
            value="100000",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY
        )
        reserve_field = ft.TextField(
            label="위기준비금 비율 (기본 5%)",
            value="5",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=BORDER_COLOR,
            focused_border_color=RESERVE_AMBER,
            color=TEXT_PRIMARY,
            suffix=ft.Text("%")
        )
        memo_field = ft.TextField(
            label="메모 (선택)",
            value="실전 8분할 운용",
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY
        )

        def handle_save_account(evt):
            name = name_field.value.strip()
            ticker = ticker_field.value.strip().upper()
            s_d = start_date_field.value.strip()
            memo = memo_field.value.strip()

            if not name:
                show_toast(self.page, "계좌명을 입력해주세요.", is_error=True)
                return

            try:
                seed = float(seed_field.value.strip())
                reserve_pct = float(reserve_field.value.strip())
                reserve_ratio = max(0.0, min(1.0, reserve_pct / 100.0))
            except ValueError:
                show_toast(self.page, "시드 및 위기준비금 숫자를 확인해주세요.", is_error=True)
                return

            new_acc = self.am.add_account(
                name=name,
                strategy="종종이 기본전략",
                ticker=ticker,
                start_date=s_d,
                initial_seed=seed,
                memo=memo,
                reserve_ratio=reserve_ratio
            )
            self.page.pop_dialog()
            show_toast(self.page, f"'{name}' 계좌가 성공적으로 생성되었습니다!")
            self.reload_data(target_acc_id=new_acc['id'])

        dlg = ft.AlertDialog(
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET, color=ACCENT_BLUE),
                    ft.Text("새 계좌 추가", weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                ],
                spacing=8
            ),
            content=ft.Container(
                width=340,
                content=ft.Column(
                    controls=[
                        name_field,
                        ft.Row([ticker_field, start_date_field], spacing=8),
                        ft.Row([seed_field, reserve_field], spacing=8),
                        memo_field,
                    ],
                    spacing=8,
                    tight=True
                )
            ),
            actions=[
                ft.TextButton("취소", on_click=lambda _: self.page.pop_dialog()),
                ft.FilledButton(
                    "계좌 생성",
                    style=ft.ButtonStyle(bgcolor=ACCENT_BLUE, color=ft.Colors.BLACK),
                    on_click=handle_save_account
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=SURFACE_CARD
        )
        self.page.show_dialog(dlg)

    def open_settings_dialog(self, e=None):
        """
        계좌 설정 수정 다이얼로그 (위기준비금 비율, 계좌명, 시드, 메모 변경)
        """
        if not self.active_account:
            return

        acc = self.active_account
        acc_id = acc['id']
        cur_reserve_pct = float(acc.get('reserve_ratio', 0.05)) * 100.0

        name_field = ft.TextField(
            label="계좌 별칭",
            value=acc.get('name', ''),
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY
        )
        seed_field = ft.TextField(
            label="초기 시드 ($)",
            value=str(acc.get('initial_seed', 100000.0)),
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY
        )
        reserve_slider = ft.Slider(
            min=0,
            max=20,
            divisions=20,
            value=cur_reserve_pct,
            label="{value}%",
            active_color=RESERVE_AMBER,
            thumb_color=RESERVE_AMBER
        )
        reserve_text = ft.Text(f"위기준비금: {cur_reserve_pct:.1f}%", size=13, weight=ft.FontWeight.BOLD, color=RESERVE_AMBER)

        def on_slider_change(evt):
            reserve_text.value = f"위기준비금: {evt.control.value:.1f}%"
            self.page.update()

        reserve_slider.on_change = on_slider_change

        memo_field = ft.TextField(
            label="계좌 메모",
            value=acc.get('memo', ''),
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY
        )

        def handle_save_settings(evt):
            try:
                new_seed = float(seed_field.value.strip())
                new_reserve = reserve_slider.value / 100.0
                new_name = name_field.value.strip()
                new_memo = memo_field.value.strip()

                self.am.update_account_settings(
                    acc_id=acc_id,
                    name=new_name,
                    reserve_ratio=new_reserve,
                    memo=new_memo,
                    initial_seed=new_seed
                )
                self.page.pop_dialog()
                show_toast(self.page, "계좌 설정이 성공적으로 저장되었습니다.")
                self.reload_data(target_acc_id=acc_id)
            except Exception as ex:
                show_toast(self.page, f"설정 저장 실패: {ex}", is_error=True)

        dlg = ft.AlertDialog(
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.SETTINGS, color=ACCENT_BLUE),
                    ft.Text("계좌 설정 변경", weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                ],
                spacing=8
            ),
            content=ft.Container(
                width=340,
                content=ft.Column(
                    controls=[
                        name_field,
                        seed_field,
                        ft.Container(height=4),
                        reserve_text,
                        reserve_slider,
                        memo_field,
                    ],
                    spacing=8,
                    tight=True
                )
            ),
            actions=[
                ft.TextButton("취소", on_click=lambda _: self.page.pop_dialog()),
                ft.FilledButton(
                    "설정 저장",
                    style=ft.ButtonStyle(bgcolor=ACCENT_BLUE, color=ft.Colors.BLACK),
                    on_click=handle_save_settings
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=SURFACE_CARD
        )
        self.page.show_dialog(dlg)

    def open_undo_dialog(self):
        """
        최근 거래일 Undo 확인 다이얼로그
        """
        if not self.active_account:
            return

        acc_id = self.active_account['id']
        curr_d = self.active_account.get('current_date', '')

        def handle_confirm_undo(evt):
            self.page.pop_dialog()
            success = self.am.delete_last_day_record(acc_id)
            if success:
                show_toast(self.page, f"최근 거래일({curr_d}) 기록이 취소되었습니다.")
                self.reload_data(target_acc_id=acc_id)
            else:
                show_toast(self.page, "취소할 이전 기록이 없습니다.", is_error=True)

        dlg = ft.AlertDialog(
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=LOSS_RED),
                    ft.Text("기록 취소 확인", weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                ],
                spacing=8
            ),
            content=ft.Text(
                f"가장 최근 거래일({curr_d})의 매매 기록 및 정산 결과를 삭제하고 이전 상태로 되돌리시겠습니까?",
                size=13,
                color=TEXT_SECONDARY
            ),
            actions=[
                ft.TextButton("닫기", on_click=lambda _: self.page.pop_dialog()),
                ft.FilledButton(
                    "취소 실행",
                    style=ft.ButtonStyle(bgcolor=LOSS_RED, color=ft.Colors.WHITE),
                    on_click=handle_confirm_undo
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
