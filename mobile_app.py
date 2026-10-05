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
import subprocess
import threading
from datetime import datetime, timedelta
import pandas as pd

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
from core.data import fetch_market_data, get_db_date_range
from core.metrics import calculate_metrics
from strategies.jongjong import JongJongStrategy
from strategies.infinite_buying_v4 import InfiniteBuyingV4Strategy
from strategies.vr_v5 import ValueRebalancingV5Strategy
from strategies.buy_and_hold import BuyAndHoldStrategy
from core.cloud_sync import (
    get_sync_config, save_sync_config, is_sync_enabled,
    test_connection, upload_accounts_to_drive, download_accounts_from_drive,
    sync_local_with_drive, get_gas_script_code
)
from core.app_update import (
    APP_VERSION, APP_BUILD_DATE_STR, get_update_config, save_update_config, parse_download_url,
    DEFAULT_UPDATE_CHANNEL_URL, DEFAULT_RELEASES_WEB_URL,
    check_remote_version_info, trigger_apk_download
)


from mobile.theme import (
    BG_DARK, SURFACE_CARD, SURFACE_CONTAINER, BORDER_COLOR, ACCENT_BLUE, PROFIT_GREEN,
    LOSS_RED, RESERVE_AMBER, VR_PURPLE, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
)
from mobile.helpers import (
    copy_text_to_clipboard, show_toast, make_bug_report_mailto, parse_picked_date_str,
    compute_suggested_trades, extract_pct_str, format_kr_date,
)
from mobile.charts import render_portfolio_chart, render_multi_backtest_chart
from core.data import get_stock_price_for_date

EXCHANGE_RATE = 1380.0        # USD/KRW ?? ??


class MobileTradingApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.am = AccountManager()
        self.accounts = []
        self.accounts_details = []
        self.current_tab_index = 0       # 0: 홈, 1: 계좌 현황, 2: 백테스트, 3: 투자 전략, 4: 설정
        self.viewing_account_id = None    # None이면 메인 탭 표시, 특정 ID면 계좌 상세 화면 표시

        # 백테스트 상태 및 폼 입력값 영구 보존용
        self.bt_results = None
        self.bt_is_loading = False
        self.bt_ticker = "SOXL"
        self.bt_period = "최근 3년"
        self.bt_seed = "200000"
        self.bt_strat_jongjong = True
        self.bt_strat_infinite = True
        self.bt_strat_vr = True
        self.bt_strat_bnh = True
        self.bt_start_date = "2022-01-03"
        self.bt_end_date = datetime.now().strftime('%Y-%m-%d')
        self.bt_custom_visible = False

        # 차트 롱프레스 터치 인스펙션 상태
        self.home_chart_dates = []
        self.home_chart_vals = []
        self.home_val_banner = None

        self.bt_chart_dates = []
        self.bt_chart_series = []
        self.bt_val_banner = None

        # Flet 기본 창 설정 (스마트폰 크기 및 테마)
        self.page.title = "종종 투자 (JongJong Mobile)"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = BG_DARK
        self.page.padding = 0

        # 데스크톱 실행 시 안드로이드 폰 비율로 크기 고정
        if hasattr(self.page, "window") and self.page.window:
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

        # 구글 드라이브 실시간 동기화가 켜져 있는 경우 백그라운드에서 최신 계좌 자동 확인
        if is_sync_enabled():
            import threading
            def _startup_sync():
                try:
                    ok, msg = sync_local_with_drive(self.am)
                    if ok:
                        self.reload_data()
                except Exception:
                    pass
            threading.Thread(target=_startup_sync, daemon=True).start()

    def open_date_picker_for_field(self, target_field: ft.TextField, on_change_callback=None):
        """달력 모달을 띄워 날짜(YYYY-MM-DD)를 선택할 수 있게 합니다."""
        cur_val = datetime.now()
        if target_field.value:
            try:
                cur_val = datetime.strptime(target_field.value.strip()[:10], '%Y-%m-%d')
            except Exception:
                pass

        def on_date_picked(e):
            val = e.control.value or dp.value
            date_str = parse_picked_date_str(val, getattr(e, 'data', None))
            if date_str:
                target_field.value = date_str
                try:
                    target_field.update()
                except Exception:
                    pass
                if on_change_callback:
                    try:
                        on_change_callback(target_field.value)
                    except Exception:
                        pass
                try:
                    self.page.update()
                except Exception:
                    pass

        dp = ft.DatePicker(
            first_date=datetime(2000, 1, 1),
            last_date=datetime(2035, 12, 31),
            value=cur_val,
            on_change=on_date_picked
        )
        self.page.show_dialog(dp)

    def open_custom_date_dialog(self, start_field: ft.TextField, end_field: ft.TextField, summary_text: ft.Text = None):
        """백테스트 날짜 범위를 직접 지정할 수 있는 전용 팝업 창을 띄웁니다."""
        cur_s = start_field.value or "2022-01-03"
        cur_e = end_field.value or datetime.now().strftime('%Y-%m-%d')

        dlg_start_f = ft.TextField(
            label="시작일 (YYYY-MM-DD)",
            value=cur_s,
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY,
            keyboard_type=ft.KeyboardType.DATETIME,
            expand=True,
            suffix=ft.IconButton(
                icon=ft.Icons.CALENDAR_MONTH,
                icon_color=ACCENT_BLUE,
                tooltip="달력 선택",
                on_click=lambda _: self.open_date_picker_for_field(dlg_start_f)
            )
        )

        dlg_end_f = ft.TextField(
            label="종료일 (YYYY-MM-DD)",
            value=cur_e,
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY,
            keyboard_type=ft.KeyboardType.DATETIME,
            expand=True,
            suffix=ft.IconButton(
                icon=ft.Icons.CALENDAR_MONTH,
                icon_color=ACCENT_BLUE,
                tooltip="달력 선택",
                on_click=lambda _: self.open_date_picker_for_field(dlg_end_f)
            )
        )

        def apply_preset(s, e):
            dlg_start_f.value = s
            dlg_end_f.value = e
            try:
                dlg_start_f.update()
                dlg_end_f.update()
            except Exception:
                pass

        now = datetime.now()
        presets = [
            ("최근 6개월", (now - timedelta(days=180)).strftime('%Y-%m-%d'), now.strftime('%Y-%m-%d')),
            ("최근 1년", (now - timedelta(days=365)).strftime('%Y-%m-%d'), now.strftime('%Y-%m-%d')),
            ("최근 2년", (now - timedelta(days=730)).strftime('%Y-%m-%d'), now.strftime('%Y-%m-%d')),
            ("2024~현재", "2024-01-02", now.strftime('%Y-%m-%d')),
            ("2023 랠리", "2023-01-03", "2023-12-29"),
            ("2022 하락장", "2022-01-03", "2022-12-30"),
            ("2020 코로나", "2020-01-02", "2020-09-30"),
            ("2019~2020", "2019-09-20", "2020-12-31"),
        ]

        preset_chips = [
            ft.Container(
                content=ft.Text(label, size=11, color=TEXT_PRIMARY, weight=ft.FontWeight.W_500),
                bgcolor=SURFACE_CONTAINER,
                border=ft.Border.all(1, BORDER_COLOR),
                border_radius=8,
                padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                on_click=lambda _, s=s, e=e: apply_preset(s, e)
            )
            for label, s, e in presets
        ]

        def handle_confirm(e):
            s_val = dlg_start_f.value.strip()
            e_val = dlg_end_f.value.strip()
            try:
                dt_s = datetime.strptime(s_val, '%Y-%m-%d')
                dt_e = datetime.strptime(e_val, '%Y-%m-%d')
            except Exception:
                show_toast(self.page, "날짜 형식이 올바르지 않습니다 (YYYY-MM-DD)", is_error=True)
                return

            if dt_s >= dt_e:
                show_toast(self.page, "종료일은 시작일보다 이후여야 합니다.", is_error=True)
                return

            start_field.value = s_val
            end_field.value = e_val
            self.bt_start_date = s_val
            self.bt_end_date = e_val
            try:
                start_field.update()
                end_field.update()
            except Exception:
                pass

            if summary_text is not None:
                summary_text.value = f"직접 기간: {s_val} ~ {e_val}"
                try:
                    summary_text.update()
                except Exception:
                    pass

            self.page.pop_dialog()
            self.page.update()
            show_toast(self.page, f"백테스트 기간이 설정되었습니다: {s_val} ~ {e_val}")

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.DATE_RANGE, color=ACCENT_BLUE, size=20),
                ft.Text("백테스트 날짜 직접 선택", size=16, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
            ], spacing=8),
            content=ft.Container(
                width=340,
                content=ft.Column(
                    controls=[
                        ft.Text("원하는 날짜를 직접 입력하거나 달력/추천 프리셋을 터치하세요.", size=12, color=TEXT_SECONDARY),
                        ft.Container(height=4),
                        dlg_start_f,
                        dlg_end_f,
                        ft.Container(height=6),
                        ft.Text("자주 쓰는 추천 기간 프리셋:", size=11, color=TEXT_MUTED, weight=ft.FontWeight.BOLD),
                        ft.Row(controls=preset_chips, wrap=True, spacing=6),
                    ],
                    spacing=8
                )
            ),
            actions=[
                ft.TextButton("취소", on_click=lambda _: self.page.pop_dialog()),
                ft.FilledButton(
                    "설정 적용",
                    style=ft.ButtonStyle(bgcolor=ACCENT_BLUE, color=ft.Colors.BLACK),
                    on_click=handle_confirm
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=SURFACE_CARD,
            shape=ft.RoundedRectangleBorder(radius=14)
        )
        self.page.show_dialog(dlg)

    def _on_home_chart_inspect(self, local_x: float):
        """홈 포트폴리오 그래프 롱프레스/터치 시 해당 X좌표의 통합 자산 수치를 배너에 표시합니다."""
        if not self.home_chart_dates or not self.home_chart_vals or not self.home_val_banner:
            return
        pad_left = 65
        pad_right = 25
        chart_w = 650 - pad_left - pad_right
        ratio = max(0.0, min(1.0, (local_x - pad_left) / max(1.0, chart_w)))
        idx = int(round(ratio * (len(self.home_chart_dates) - 1)))
        dt = self.home_chart_dates[idx]
        val = self.home_chart_vals[idx]
        krw_text = f"약 {val * EXCHANGE_RATE / 1e8:.2f}억원"
        first_val = self.home_chart_vals[0] if self.home_chart_vals else val
        is_up = val >= first_val

        self.home_val_banner.content = ft.Row(
            controls=[
                ft.Icon(ft.Icons.EVENT_NOTE, color=ACCENT_BLUE, size=15),
                ft.Text(f"{dt}", size=12, weight=ft.FontWeight.BOLD, color=ACCENT_BLUE),
                ft.Container(width=4),
                ft.Text(f"${val:,.0f}", size=13, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                ft.Text(f"({krw_text})", size=11, color=PROFIT_GREEN if is_up else LOSS_RED, weight=ft.FontWeight.W_500),
            ],
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )
        self.page.update()

    def _on_bt_chart_inspect(self, local_x: float):
        """백테스트 차트 롱프레스/터치 시 해당 X좌표의 각 검증 전략별 Y 자산 수치를 배너에 표시합니다."""
        if not self.bt_chart_dates or not self.bt_chart_series or not self.bt_val_banner:
            return
        pad_left = 65
        pad_right = 25
        chart_w = 650 - pad_left - pad_right
        ratio = max(0.0, min(1.0, (local_x - pad_left) / max(1.0, chart_w)))
        idx = int(round(ratio * (len(self.bt_chart_dates) - 1)))
        dt = self.bt_chart_dates[idx]

        items = [
            ft.Icon(ft.Icons.CALENDAR_MONTH, color=ACCENT_BLUE, size=14),
            ft.Text(f"{dt}", size=12, weight=ft.FontWeight.BOLD, color=ACCENT_BLUE),
        ]
        for s in self.bt_chart_series:
            v = s['vals'][idx] if idx < len(s['vals']) else 0.0
            s_name_short = s['name'].split()[0]
            items.append(ft.Container(width=4))
            items.append(ft.Container(width=7, height=7, bgcolor=s['color'], border_radius=4))
            items.append(ft.Text(f"{s_name_short}: ${v:,.0f}", size=11, weight=ft.FontWeight.BOLD, color=s['color']))

        self.bt_val_banner.content = ft.Row(
            controls=items,
            spacing=3,
            wrap=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )
        self.page.update()

    def _setup_app_bar(self):
        self.title_text = ft.Text("종종 투자 포트폴리오", size=16, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
        self.subtitle_text = ft.Text("전체 계좌 통합 자산", size=11, color=TEXT_SECONDARY)

        self.leading_icon = ft.Container(
            content=ft.Icon(ft.Icons.SAVINGS_OUTLINED, color=ACCENT_BLUE, size=22),
            padding=ft.Padding.only(left=12)
        )

        self.action_buttons = [
            ft.IconButton(
                icon=ft.Icons.CLOUD_SYNC_ROUNDED,
                icon_color=ACCENT_BLUE,
                tooltip="구글 드라이브 동기화",
                on_click=lambda e: self.handle_quick_cloud_sync()
            ),
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

    def handle_quick_cloud_sync(self):
        """상단 앱바 클라우드 아이콘 터치 시 구글 드라이브 동기화를 실행합니다."""
        if not is_sync_enabled():
            show_toast(self.page, "설정 탭에서 Google Drive 동기화를 켜주세요.")
            return
        show_toast(self.page, "Google Drive와 동기화 진행 중...")
        import threading
        def _bg_sync():
            ok, msg = sync_local_with_drive(self.am)
            if ok:
                show_toast(self.page, msg)
                self.reload_data()
            else:
                show_toast(self.page, f"동기화 실패: {msg}", is_error=True)
        threading.Thread(target=_bg_sync, daemon=True).start()


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
                    icon=ft.Icons.MENU_BOOK_OUTLINED,
                    selected_icon=ft.Icons.MENU_BOOK_ROUNDED,
                    label="투자 전략"
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
            self.content_container.content = self._build_strategies_tab()
        elif self.current_tab_index == 4:
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
            self.subtitle_text.value = "시뮬레이션 및 복수 전략 비교"
            self.leading_icon.content = ft.Icon(ft.Icons.ANALYTICS_OUTLINED, color=ACCENT_BLUE, size=22)
        elif self.current_tab_index == 3:
            self.title_text.value = "투자 전략 가이드"
            self.subtitle_text.value = "종종이 & 무한매수법 v4.0 핵심 원리"
            self.leading_icon.content = ft.Icon(ft.Icons.MENU_BOOK_ROUNDED, color=ACCENT_BLUE, size=22)
        elif self.current_tab_index == 4:
            self.title_text.value = "환경 설정"
            self.subtitle_text.value = "데이터 내보내기 및 시스템 설정"
            self.leading_icon.content = ft.Icon(ft.Icons.SETTINGS_OUTLINED, color=ACCENT_BLUE, size=22)

        if self.page.appbar:
            self.page.appbar.leading = self.leading_icon
            self.page.appbar.actions = [
                ft.IconButton(
                    icon=ft.Icons.CLOUD_SYNC_ROUNDED,
                    icon_color=ACCENT_BLUE,
                    tooltip="구글 드라이브 동기화",
                    on_click=lambda e: self.handle_quick_cloud_sync()
                ),
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

        if self.page.appbar:
            # 뒤로가기 버튼
            self.page.appbar.leading = ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                icon_color=TEXT_PRIMARY,
                tooltip="계좌 목록으로",
                on_click=self.back_to_accounts
            )
            self.page.appbar.actions = [
                ft.IconButton(
                    icon=ft.Icons.CLOUD_SYNC_ROUNDED,
                    icon_color=ACCENT_BLUE,
                    tooltip="구글 드라이브 동기화",
                    on_click=lambda e: self.handle_quick_cloud_sync()
                ),
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
        chart_base64, dates, vals = render_portfolio_chart(self.accounts_details, tot_asset)
        self.home_chart_dates = dates
        self.home_chart_vals = vals

        self.home_val_banner = ft.Container(
            bgcolor=SURFACE_CONTAINER,
            border=ft.Border.all(1, BORDER_COLOR),
            border_radius=8,
            padding=ft.Padding.symmetric(horizontal=10, vertical=6),
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.TOUCH_APP_OUTLINED, color=ACCENT_BLUE, size=15),
                    ft.Text("그래프를 길게 누르면 해당 위치의 자산 수치가 표시됩니다", size=11, color=TEXT_MUTED)
                ],
                spacing=6
            )
        )

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
                                ft.Row([
                                    ft.Icon(ft.Icons.SHOW_CHART, size=18, color=ACCENT_BLUE),
                                    ft.Text("포트폴리오 자산 성장 추이", size=13, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                                ], spacing=6),
                                ft.Text("길게 누르기: 수치확인 | 핀치: 확대", size=10, color=TEXT_MUTED)
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        ft.Container(height=4),
                        self.home_val_banner,
                        ft.Container(height=4),
                        ft.Container(
                            height=200,
                            border_radius=8,
                            clip_behavior=ft.ClipBehavior.HARD_EDGE,
                            content=ft.InteractiveViewer(
                                content=ft.GestureDetector(
                                    content=ft.Image(src=chart_base64, fit="contain", width=650, height=200),
                                    on_long_press_start=lambda e: self._on_home_chart_inspect(e.local_position.x),
                                    on_long_press_move_update=lambda e: self._on_home_chart_inspect(e.local_position.x),
                                    on_tap_down=lambda e: self._on_home_chart_inspect(e.local_position.x)
                                ),
                                constrained=True,
                                min_scale=1.0,
                                max_scale=4.0,
                                pan_enabled=True,
                                scale_enabled=True,
                                clip_behavior=ft.ClipBehavior.HARD_EDGE
                            )
                        ),
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
                    ],
                    alignment=ft.MainAxisAlignment.START
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
                                    ft.Icon(ft.Icons.CHEVRON_RIGHT, color=TEXT_MUTED, size=20)
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
                                        ft.Text(f"{strat} • {mode} (2주 리밸런싱)" if 'VR' in strat.upper() else f"{strat} • {mode} 모드 (8분할 운용)", size=11, color=VR_PURPLE if 'VR' in strat.upper() else TEXT_SECONDARY)
                                    ],
                                    spacing=2
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.START
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
                                    ft.Text("2주 사이클" if 'VR' in strat.upper() else "위기준비금 (AK)", size=10, color=VR_PURPLE if 'VR' in strat.upper() else RESERVE_AMBER),
                                    ft.Text(f"{mode}" if 'VR' in strat.upper() else f"${ak_val:,.0f}", size=13 if 'VR' in strat.upper() else 14, weight=ft.FontWeight.BOLD, color=VR_PURPLE if 'VR' in strat.upper() else RESERVE_AMBER)
                                ], spacing=1),
                                ft.Column([
                                    ft.Text("보유 수량" if 'VR' in strat.upper() else "실가동시드 (AR)", size=10, color=ACCENT_BLUE),
                                    ft.Text(f"{hold:,}주" if 'VR' in strat.upper() else f"${ar_val:,.0f}", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                                ], spacing=1),
                                ft.Column([
                                    ft.Text("가용 Pool 예산" if 'VR' in strat.upper() else "하루 배분 예산", size=10, color=TEXT_SECONDARY),
                                    ft.Text(f"${budget:,.2f}", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                                ], spacing=1),
                                ft.Column([
                                    ft.Text("예수금 (Pool)" if 'VR' in strat.upper() else "예수금", size=10, color=TEXT_SECONDARY),
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

        if 'VR' in strat.upper():
            holdings_section = ft.Container(
                bgcolor=SURFACE_CARD,
                border=ft.Border.all(1, ft.Colors.with_opacity(0.35, VR_PURPLE)),
                border_radius=12,
                padding=14,
                content=ft.Column(
                    controls=[
                        ft.Row([
                            ft.Icon(ft.Icons.AUTO_AWESOME, color=VR_PURPLE, size=18),
                            ft.Text("VR 5.0 밸류리밸런싱 2주 사이클 안내", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        ], spacing=6),
                        ft.Text(
                            f"현재 보유: {hold:,}주 (평가액: ${hold*latest_price:,.2f}) • 예수금(Pool): ${cash:,.2f}\n"
                            f"2주(10거래일) 동안 아래의 예약 주문표를 증권사에 기간예약 주문으로 걸어두세요. "
                            f"주가가 밴드를 이탈할 때만 자동 매매되어 밴드 안으로 복귀합니다.",
                            size=11.5, color=TEXT_SECONDARY
                        )
                    ],
                    spacing=6
                )
            )
        else:
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

        # 3-1. 매도 주문 박스 (얼마에 몇 주 걸건지 + 변동률만 심플 표시)
        sell_items = []
        ref_p = latest_price if latest_price > 0 else 142.29
        if sell_orders:
            for s in sell_orders:
                price = str(s.get('주문단가', '$0.00'))
                qty = str(s.get('주문수량', s.get('qty', '0'))).replace('주', '').replace(',', '').strip()
                pct_str = extract_pct_str(s, ref_p)

                row = ft.Container(
                    padding=ft.Padding.symmetric(vertical=8, horizontal=10),
                    bgcolor=ft.Colors.with_opacity(0.06, LOSS_RED),
                    border_radius=8,
                    content=ft.Row(
                        controls=[
                            ft.Row([
                                ft.Text(price, size=15, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                                ft.Text(pct_str, size=13, weight=ft.FontWeight.W_600, color=LOSS_RED if '-' in pct_str else PROFIT_GREEN) if pct_str else ft.Container(),
                            ], spacing=6),
                            ft.Text(f"{qty}주", size=15, weight=ft.FontWeight.BOLD, color=LOSS_RED)
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
                            ft.Text("체결 대상 매도 주문 없음 (보유 홀딩)", size=12, color=TEXT_MUTED)
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
                                ft.Text("🔴 2주 매도 예약 (상단 밴드)" if 'VR' in strat.upper() else "🔴 매도 주문", size=13, weight=ft.FontWeight.BOLD, color=LOSS_RED),
                            ], spacing=6),
                            ft.Container(
                                content=ft.Text(f"총 {total_sell_qty:,}주" if total_sell_qty > 0 else "0건", size=10, color=LOSS_RED, weight=ft.FontWeight.BOLD),
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

        # 3-2. 매수 주문 박스 (얼마에 몇 주 걸건지 + 변동률만 심플 표시)
        buy_items = []
        if buy_orders:
            for b in buy_orders:
                price = str(b.get('주문단가', '$0.00'))
                qty = str(b.get('주문수량', b.get('qty', '0'))).replace('주', '').replace(',', '').strip()
                pct_str = extract_pct_str(b, ref_p)

                row = ft.Container(
                    padding=ft.Padding.symmetric(vertical=8, horizontal=10),
                    bgcolor=ft.Colors.with_opacity(0.06, PROFIT_GREEN),
                    border_radius=8,
                    content=ft.Row(
                        controls=[
                            ft.Row([
                                ft.Text(price, size=15, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                                ft.Text(pct_str, size=13, weight=ft.FontWeight.W_600, color=LOSS_RED if '-' in pct_str else PROFIT_GREEN) if pct_str else ft.Container(),
                            ], spacing=6),
                            ft.Text(f"{qty}주", size=15, weight=ft.FontWeight.BOLD, color=PROFIT_GREEN)
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
                            ft.Text("체결 대상 매수 주문 없음", size=12, color=TEXT_MUTED)
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
                                ft.Text("🟢 2주 매수 예약 (하단 밴드)" if 'VR' in strat.upper() else "🟢 매수 주문", size=13, weight=ft.FontWeight.BOLD, color=PROFIT_GREEN),
                            ], spacing=6),
                            ft.Container(
                                content=ft.Text(f"총 {total_buy_qty:,}주" if total_buy_qty > 0 else "0건", size=10, color=PROFIT_GREEN, weight=ft.FontWeight.BOLD),
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

        # 입력해야 하는 정산 대상 일자 결정 (현재 표시 운용일)
        default_settle_date = curr_d or target_date or datetime.now().strftime('%Y-%m-%d')

        # 미매도 슬롯 및 전략 정보 추출
        unsold_lots_data = dtl.get('unsold_lots', [])
        if not unsold_lots_data and records:
            unsold_lots_data = [r for r in records if int(r.get('R', 0)) > 0 and not bool(r.get('Sold', False))]
        strat_name = acc.get('strategy', '')
        net_info = dtl.get('netting_info', {})

        # 입력해야 하는 날짜의 종가를 기본값(default)으로 조회
        init_close = get_stock_price_for_date(ticker, default_settle_date, fallback_price=fallback_p)
        calc_buy_q, calc_sell_q = compute_suggested_trades(
            init_close, buy_orders, sell_orders, unsold_lots=unsold_lots_data, strategy_name=strat_name, netting_info=net_info
        )

        # 첫날 신규 계좌이고 매수 대기 중인데 계산이 0이면 1차 주문 수량으로 기본 제안
        if calc_buy_q == 0 and not records and buy_orders:
            try:
                calc_buy_q = int(str(buy_orders[0].get('주문수량', '0')).replace('주', '').replace(',', '').strip())
            except Exception:
                pass

        settle_date_field = ft.TextField(
            label="정산 일자 (YYYY-MM-DD)",
            label_style=ft.TextStyle(size=11, color=TEXT_SECONDARY),
            value=default_settle_date,
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY,
            text_size=12,
            content_padding=ft.Padding.symmetric(horizontal=10, vertical=8),
            expand=True
        )

        close_field = ft.TextField(
            label="종가($)",
            label_style=ft.TextStyle(size=11, color=TEXT_SECONDARY),
            value=f"{init_close:.2f}",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY,
            text_size=12,
            text_align=ft.TextAlign.RIGHT,
            dense=True,
            content_padding=ft.Padding.symmetric(horizontal=8, vertical=8),
            expand=True
        )

        buy_qty_field = ft.TextField(
            label="매수(주)",
            label_style=ft.TextStyle(size=11, color=PROFIT_GREEN),
            value=str(calc_buy_q),
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=BORDER_COLOR,
            focused_border_color=PROFIT_GREEN,
            color=TEXT_PRIMARY,
            text_size=12,
            text_align=ft.TextAlign.RIGHT,
            dense=True,
            content_padding=ft.Padding.symmetric(horizontal=8, vertical=8),
            expand=True
        )

        sell_qty_field = ft.TextField(
            label="매도(자동)",
            label_style=ft.TextStyle(size=11, color=LOSS_RED),
            value=str(calc_sell_q),
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=BORDER_COLOR,
            focused_border_color=LOSS_RED,
            color=LOSS_RED,
            text_size=12,
            text_align=ft.TextAlign.RIGHT,
            dense=True,
            content_padding=ft.Padding.symmetric(horizontal=8, vertical=8),
            expand=True,
            read_only=True
        )

        def on_settle_date_picked(new_date_str):
            if not new_date_str:
                return
            d_clean = str(new_date_str).strip()[:10]
            if len(d_clean) == 10:
                p = get_stock_price_for_date(ticker, d_clean, fallback_price=fallback_p)
                close_field.value = f"{p:.2f}"
                b_q, s_q = compute_suggested_trades(
                    p, buy_orders, sell_orders, unsold_lots=unsold_lots_data, strategy_name=strat_name, netting_info=net_info
                )
                buy_qty_field.value = str(b_q)
                sell_qty_field.value = str(s_q)
                try:
                    close_field.update()
                    buy_qty_field.update()
                    sell_qty_field.update()
                except Exception:
                    pass

        settle_date_field.on_change = lambda e: on_settle_date_picked(settle_date_field.value)

        def on_close_changed(e):
            try:
                val = float(close_field.value.strip())
                b_q, s_q = compute_suggested_trades(
                    val, buy_orders, sell_orders, unsold_lots=unsold_lots_data, strategy_name=strat_name, netting_info=net_info
                )
                buy_qty_field.value = str(b_q)
                sell_qty_field.value = str(s_q)
                buy_qty_field.update()
                sell_qty_field.update()
            except Exception:
                pass

        close_field.on_change = on_close_changed

        def handle_settle(e):
            try:
                s_date = settle_date_field.value.strip()
                c_p = float(close_field.value.strip())
                b_q = int(buy_qty_field.value.strip())
                s_q = int(sell_qty_field.value.strip())
                self.am.record_daily_close(acc_id=acc_id, close_price=c_p, buy_qty=b_q, sell_qty=s_q, buy_price=c_p, trade_date=s_date, mode=dtl.get('mode', 'Normal'))
                show_toast(self.page, f"{s_date} 정산 데이터가 저장되었습니다! 다음 날짜 주문표로 넘어가려면 [다음 거래일 진행]을 누르세요.")
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
                            ft.Icon(ft.Icons.CALCULATE_ROUNDED, color=ACCENT_BLUE, size=18),
                            ft.Text("일일 정산 입력 (매도 자동 체결 / 매수 입력)", size=13, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        ], spacing=6),
                        ft.Row([
                            settle_date_field,
                            ft.IconButton(
                                icon=ft.Icons.CALENDAR_MONTH,
                                icon_color=ACCENT_BLUE,
                                tooltip="정산 일자 달력 선택",
                                on_click=lambda _: self.open_date_picker_for_field(settle_date_field, on_change_callback=on_settle_date_picked)
                            )
                        ], spacing=4),
                        ft.Row([close_field, buy_qty_field, sell_qty_field], spacing=6),
                        ft.Container(
                            padding=ft.Padding.symmetric(horizontal=4, vertical=2),
                            content=ft.Row([
                                ft.Icon(ft.Icons.INFO_OUTLINE, size=13, color=TEXT_MUTED),
                                ft.Text(
                                    "목표가 이상 도달 슬롯은 매도 자동 체결(수정불가)되며, 매수 수량만 확인/입력하세요.",
                                    size=10.5,
                                    color=TEXT_MUTED
                                )
                            ], spacing=4)
                        ),
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
        # -------------------------------------------------------------
        # 5. 최근 거래 내역 (슬롯 단위 라이프사이클 & 4대 섹션 구분 표)
        #    한 행 = 하나의 매수 슬롯(Lot) 정보
        #    섹션 1: 거래일자/종가/변동률/모드 , 섹션 2: 매수량/목표가 , 섹션 3: 매도일/매도가 , 섹션 4: 손익금액/손익률/누적손익
        # -------------------------------------------------------------
        table_rows = []
        if records:
            # 1. 누적 실현손익 사전 계산 (시간순 t=0부터)
            cum_profits = {}
            running_cum = 0.0
            for i, rec in enumerate(records):
                is_s = bool(rec.get('Sold', False))
                p_val = rec.get('Profit')
                if is_s and p_val is not None:
                    try:
                        running_cum += float(p_val)
                        cum_profits[i] = running_cum
                    except Exception:
                        cum_profits[i] = running_cum
                else:
                    cum_profits[i] = None

            for orig_idx, r in reversed(list(enumerate(records))):
                r_d = str(r.get('Date', ''))
                r_d_kr = format_kr_date(r_d)
                r_cp = float(r.get('Close', 0.0))

                # 변동률 계산
                chg_val = r.get('Chg')
                if chg_val is None or (chg_val == 0.0 and orig_idx > 0):
                    prev_close = float(records[orig_idx - 1].get('Close', 0.0))
                    if prev_close > 0:
                        chg_val = (r_cp / prev_close - 1.0)
                    else:
                        chg_val = 0.0
                try:
                    chg_f = float(chg_val)
                except Exception:
                    chg_f = 0.0
                chg_str = f"{chg_f * 100:+.2f}%" if (orig_idx > 0 or chg_f != 0.0) else "-"
                chg_color = LOSS_RED if chg_f > 0 else (ACCENT_BLUE if chg_f < 0 else TEXT_MUTED)

                # 시장 모드
                r_mode = str(r.get('Mode', 'Normal'))
                mode_color = "#3B82F6" if r_mode == 'Normal' else ("#EAB308" if r_mode == 'Safe' else "#EF4444")

                # 매수 정보
                r_bq = int(r.get('BuyQty', r.get('R', 0)))
                r_u = float(r.get('U', 0.0)) if r.get('U') is not None else 0.0
                if r_u == 0.0 and r_bq > 0:
                    t_y = 0.0275 if '종종이' in strat else 0.05
                    r_u = round_up(r_cp * (1.0 + t_y), 2)

                # 매도 정보
                is_sold = bool(r.get('Sold', False)) and (r.get('W') is not None)
                if is_sold:
                    r_wd = format_kr_date(r.get('W'))
                    r_sp = float(r.get('X', 0.0))
                    sell_price_str = f"${r_sp:.2f}"
                else:
                    if r_bq > 0:
                        h_days = len(records) - 1 - int(r.get('t', orig_idx))
                        r_wd = f"보유중({h_days}d)"
                    else:
                        r_wd = "-"
                    sell_price_str = "-"

                # 손익 정보
                r_p = r.get('Profit')
                if is_sold and r_p is not None:
                    p_num = float(r_p)
                    profit_str = f"{p_num:+,.0f}$"
                    profit_color = PROFIT_GREEN if p_num >= 0 else LOSS_RED

                    # 손익률
                    r_pr = r.get('ProfitRate')
                    if r_pr is not None:
                        pr_num = float(r_pr)
                    else:
                        bp = float(r.get('BuyPrice', r_cp))
                        pr_num = ((r_sp / bp - 1.0) * 100.0) if (bp > 0 and r_sp > 0) else 0.0
                    pr_str = f"{pr_num:+.1f}%"
                else:
                    profit_str = "-"
                    profit_color = TEXT_MUTED
                    pr_str = "-"

                # 누적손익
                cum_num = cum_profits.get(orig_idx)
                if cum_num is not None:
                    cum_str = f"{cum_num:+,.0f}$"
                    cum_color = PROFIT_GREEN if cum_num >= 0 else LOSS_RED
                else:
                    cum_str = "-"
                    cum_color = TEXT_MUTED

                def make_edit_fn(idx_to_edit):
                    return lambda _: self.open_edit_trade_dialog(acc_id, idx_to_edit)

                table_rows.append(
                    ft.DataRow(
                        cells=[
                            # 섹션 1: 시장 정보
                            ft.DataCell(ft.Text(r_d_kr, size=11, color=TEXT_PRIMARY, weight=ft.FontWeight.W_600)),
                            ft.DataCell(ft.Text(f"${r_cp:.2f}", size=11, color=TEXT_PRIMARY)),
                            ft.DataCell(ft.Text(chg_str, size=11, color=chg_color, weight=ft.FontWeight.W_500)),
                            ft.DataCell(
                                ft.Container(
                                    content=ft.Text(r_mode, size=9, weight=ft.FontWeight.BOLD, color=mode_color),
                                    bgcolor=ft.Colors.with_opacity(0.15, mode_color),
                                    padding=ft.Padding.symmetric(horizontal=5, vertical=2),
                                    border_radius=4,
                                    border=ft.Border(right=ft.BorderSide(1.5, ft.Colors.with_opacity(0.35, BORDER_COLOR)))
                                )
                            ),
                            # 섹션 2: 매수 정보
                            ft.DataCell(ft.Text(f"{r_bq:,}주" if r_bq > 0 else "관망", size=11, color=PROFIT_GREEN if r_bq > 0 else TEXT_MUTED, weight=ft.FontWeight.BOLD if r_bq > 0 else ft.FontWeight.NORMAL)),
                            ft.DataCell(
                                ft.Container(
                                    content=ft.Text(f"${r_u:.2f}" if r_u > 0 else "-", size=11, color=TEXT_SECONDARY),
                                    border=ft.Border(right=ft.BorderSide(1.5, ft.Colors.with_opacity(0.35, BORDER_COLOR)))
                                )
                            ),
                            # 섹션 3: 매도 정보
                            ft.DataCell(
                                ft.Container(
                                    content=ft.Text(r_wd, size=10.5, color=RESERVE_AMBER if "보유중" in r_wd else (TEXT_PRIMARY if r_wd != "-" else TEXT_MUTED), weight=ft.FontWeight.W_600 if "보유중" in r_wd else ft.FontWeight.NORMAL),
                                    bgcolor=ft.Colors.with_opacity(0.12, RESERVE_AMBER) if "보유중" in r_wd else ft.Colors.TRANSPARENT,
                                    padding=ft.Padding.symmetric(horizontal=4, vertical=2) if "보유중" in r_wd else None,
                                    border_radius=4 if "보유중" in r_wd else 0
                                )
                            ),
                            ft.DataCell(
                                ft.Container(
                                    content=ft.Text(sell_price_str, size=11, color=TEXT_PRIMARY if sell_price_str != "-" else TEXT_MUTED),
                                    border=ft.Border(right=ft.BorderSide(1.5, ft.Colors.with_opacity(0.35, BORDER_COLOR)))
                                )
                            ),
                            # 섹션 4: 손익 정보
                            ft.DataCell(ft.Text(profit_str, size=11, color=profit_color, weight=ft.FontWeight.BOLD if profit_str != "-" else ft.FontWeight.NORMAL)),
                            ft.DataCell(ft.Text(pr_str, size=11, color=profit_color, weight=ft.FontWeight.W_600 if pr_str != "-" else ft.FontWeight.NORMAL)),
                            ft.DataCell(ft.Text(cum_str, size=11, color=cum_color, weight=ft.FontWeight.BOLD if cum_str != "-" else ft.FontWeight.NORMAL)),
                            # 관리
                            ft.DataCell(
                                ft.IconButton(
                                    icon=ft.Icons.EDIT_OUTLINED,
                                    icon_size=15,
                                    icon_color=ACCENT_BLUE,
                                    tooltip="슬롯 수정",
                                    on_click=make_edit_fn(orig_idx)
                                )
                            ),
                        ],
                        on_long_press=make_edit_fn(orig_idx)
                    )
                )

            # 상단 섹션 구분 안내 바 (첨부 이미지 스타일: 콤마 구분)
            section_badges = ft.Container(
                bgcolor=BG_DARK,
                border_radius=8,
                padding=ft.Padding.symmetric(horizontal=8, vertical=6),
                border=ft.Border.all(1, BORDER_COLOR),
                content=ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Row([
                                ft.Container(width=7, height=7, border_radius=4, bgcolor="#4ADE80"),
                                ft.Text("거래일자/종가/변동률/모드", size=10.5, weight=ft.FontWeight.BOLD, color="#4ADE80"),
                            ], spacing=4),
                            bgcolor=ft.Colors.with_opacity(0.12, "#4ADE80"),
                            padding=ft.Padding.symmetric(horizontal=6, vertical=3),
                            border_radius=6,
                        ),
                        ft.Text(",", size=14, weight=ft.FontWeight.BOLD, color=TEXT_SECONDARY),
                        ft.Container(
                            content=ft.Row([
                                ft.Container(width=7, height=7, border_radius=4, bgcolor="#F472B6"),
                                ft.Text("매수량/목표가", size=10.5, weight=ft.FontWeight.BOLD, color="#F472B6"),
                            ], spacing=4),
                            bgcolor=ft.Colors.with_opacity(0.12, "#F472B6"),
                            padding=ft.Padding.symmetric(horizontal=6, vertical=3),
                            border_radius=6,
                        ),
                        ft.Text(",", size=14, weight=ft.FontWeight.BOLD, color=TEXT_SECONDARY),
                        ft.Container(
                            content=ft.Row([
                                ft.Container(width=7, height=7, border_radius=4, bgcolor="#60A5FA"),
                                ft.Text("매도일/매도가", size=10.5, weight=ft.FontWeight.BOLD, color="#60A5FA"),
                            ], spacing=4),
                            bgcolor=ft.Colors.with_opacity(0.12, "#60A5FA"),
                            padding=ft.Padding.symmetric(horizontal=6, vertical=3),
                            border_radius=6,
                        ),
                        ft.Text(",", size=14, weight=ft.FontWeight.BOLD, color=TEXT_SECONDARY),
                        ft.Container(
                            content=ft.Row([
                                ft.Container(width=7, height=7, border_radius=4, bgcolor="#FBBF24"),
                                ft.Text("손익금액/손익률/누적손익", size=10.5, weight=ft.FontWeight.BOLD, color="#FBBF24"),
                            ], spacing=4),
                            bgcolor=ft.Colors.with_opacity(0.12, "#FBBF24"),
                            padding=ft.Padding.symmetric(horizontal=6, vertical=3),
                            border_radius=6,
                        ),
                    ],
                    scroll=ft.ScrollMode.AUTO,
                    spacing=5,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                )
            )

            # 엑셀 형식 표 정의 (컬럼 헤더 섹션 컬러링)
            history_table = ft.DataTable(
                columns=[
                    # 섹션 1: 시장 정보
                    ft.DataColumn(ft.Text("거래일자", weight=ft.FontWeight.BOLD, size=11, color="#4ADE80")),
                    ft.DataColumn(ft.Text("종가", weight=ft.FontWeight.BOLD, size=11, color="#4ADE80"), numeric=True),
                    ft.DataColumn(ft.Text("변동률", weight=ft.FontWeight.BOLD, size=11, color="#4ADE80"), numeric=True),
                    ft.DataColumn(ft.Text("모드", weight=ft.FontWeight.BOLD, size=11, color="#4ADE80")),
                    # 섹션 2: 매수 정보
                    ft.DataColumn(ft.Text("매수량", weight=ft.FontWeight.BOLD, size=11, color="#F472B6"), numeric=True),
                    ft.DataColumn(ft.Text("목표가", weight=ft.FontWeight.BOLD, size=11, color="#F472B6"), numeric=True),
                    # 섹션 3: 매도 정보
                    ft.DataColumn(ft.Text("매도일", weight=ft.FontWeight.BOLD, size=11, color="#60A5FA")),
                    ft.DataColumn(ft.Text("매도가", weight=ft.FontWeight.BOLD, size=11, color="#60A5FA"), numeric=True),
                    # 섹션 4: 손익 정보
                    ft.DataColumn(ft.Text("손익금액", weight=ft.FontWeight.BOLD, size=11, color="#FBBF24"), numeric=True),
                    ft.DataColumn(ft.Text("손익률", weight=ft.FontWeight.BOLD, size=11, color="#FBBF24"), numeric=True),
                    ft.DataColumn(ft.Text("누적손익", weight=ft.FontWeight.BOLD, size=11, color="#FBBF24"), numeric=True),
                    # 관리
                    ft.DataColumn(ft.Text("수정", weight=ft.FontWeight.BOLD, size=11, color=TEXT_SECONDARY)),
                ],
                rows=table_rows,
                border=ft.Border.all(1, BORDER_COLOR),
                heading_row_color=ft.Colors.with_opacity(0.4, BG_DARK),
                data_row_min_height=38,
                data_row_max_height=42,
                column_spacing=12,
                horizontal_margin=8,
            )

            history_view = ft.Container(
                bgcolor=SURFACE_CARD,
                border=ft.Border.all(1, BORDER_COLOR),
                border_radius=10,
                padding=6,
                content=ft.Column(
                    controls=[
                        section_badges,
                        ft.Container(height=4),
                        ft.Row(
                            controls=[history_table],
                            scroll=ft.ScrollMode.ALWAYS
                        )
                    ],
                    spacing=2
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
                    ft.Row([
                        ft.Icon(ft.Icons.TABLE_VIEW_ROUNDED, color=ACCENT_BLUE, size=18),
                        ft.Text("거래 슬롯별 상세 내역 (4대 섹션)", size=13, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                    ], spacing=6),
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
        cur_ticker = getattr(self, 'bt_ticker', 'SOXL')
        cur_period = getattr(self, 'bt_period', '최근 3년')
        cur_seed = getattr(self, 'bt_seed', '200000')
        cur_jj = getattr(self, 'bt_strat_jongjong', True)
        cur_inf = getattr(self, 'bt_strat_infinite', True)
        cur_vr = getattr(self, 'bt_strat_vr', True)
        cur_bnh = getattr(self, 'bt_strat_bnh', True)
        cur_s_date = getattr(self, 'bt_start_date', '2022-01-03')
        cur_e_date = getattr(self, 'bt_end_date', datetime.now().strftime('%Y-%m-%d'))
        cur_custom_vis = getattr(self, 'bt_custom_visible', False) or (cur_period == "직접 날짜 선택 (사용자 지정)")

        ticker_dd = ft.Dropdown(
            label="대상 종목",
            label_style=ft.TextStyle(size=11, color=TEXT_SECONDARY),
            value=cur_ticker,
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
            text_size=12.5,
            dense=True,
            content_padding=ft.Padding.only(left=8, right=2, top=4, bottom=4),
            expand=True
        )

        def on_ticker_change(e):
            self.bt_ticker = ticker_dd.value

        ticker_dd.on_change = on_ticker_change

        # 복수 선택 가능한 전략 체크박스
        cb_jongjong = ft.Checkbox(
            label="종종이 전략",
            value=cur_jj,
            active_color=PROFIT_GREEN,
            label_style=ft.TextStyle(color=TEXT_PRIMARY, size=12, weight=ft.FontWeight.W_600)
        )
        cb_infinite = ft.Checkbox(
            label="무한매수 v4",
            value=cur_inf,
            active_color=RESERVE_AMBER,
            label_style=ft.TextStyle(color=TEXT_PRIMARY, size=12, weight=ft.FontWeight.W_600)
        )
        cb_vr = ft.Checkbox(
            label="VR 5.0",
            value=cur_vr,
            active_color=VR_PURPLE,
            label_style=ft.TextStyle(color=TEXT_PRIMARY, size=12, weight=ft.FontWeight.W_600)
        )
        cb_bnh = ft.Checkbox(
            label="단순보유(B&H)",
            value=cur_bnh,
            active_color=ACCENT_BLUE,
            label_style=ft.TextStyle(color=TEXT_PRIMARY, size=12, weight=ft.FontWeight.W_600)
        )

        def on_cb_change(e):
            self.bt_strat_jongjong = cb_jongjong.value
            self.bt_strat_infinite = cb_infinite.value
            self.bt_strat_vr = cb_vr.value
            self.bt_strat_bnh = cb_bnh.value

        cb_jongjong.on_change = on_cb_change
        cb_infinite.on_change = on_cb_change
        cb_vr.on_change = on_cb_change
        cb_bnh.on_change = on_cb_change

        strat_selector = ft.Container(
            bgcolor=SURFACE_CONTAINER,
            border=ft.Border.all(1, BORDER_COLOR),
            border_radius=10,
            padding=ft.Padding.symmetric(horizontal=10, vertical=8),
            content=ft.Column(
                controls=[
                    ft.Row([
                        ft.Icon(ft.Icons.CHECKLIST, color=ACCENT_BLUE, size=15),
                        ft.Text("검증 전략 선택 (복수 선택 시 한 그래프에 동시 비교)", size=12, weight=ft.FontWeight.BOLD, color=TEXT_SECONDARY),
                    ], spacing=6),
                    ft.Row([cb_jongjong, cb_infinite, cb_vr, cb_bnh], spacing=6, wrap=True)
                ],
                spacing=4
            )
        )

        period_dd = ft.Dropdown(
            label="테스트 기간",
            label_style=ft.TextStyle(size=11, color=TEXT_SECONDARY),
            value=cur_period,
            options=[
                ft.dropdown.Option("최근 1년"),
                ft.dropdown.Option("최근 2년"),
                ft.dropdown.Option("최근 3년"),
                ft.dropdown.Option("최근 5년"),
                ft.dropdown.Option("2019년~현재"),
                ft.dropdown.Option("직접 날짜 선택 (사용자 지정)")
            ],
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY,
            text_size=11.5,
            dense=True,
            content_padding=ft.Padding.only(left=8, right=2, top=4, bottom=4),
            expand=True
        )

        seed_field = ft.TextField(
            label="초기 투자 원금 ($)",
            value=cur_seed,
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY,
            text_size=12.5,
            dense=True,
            content_padding=ft.Padding.symmetric(horizontal=10, vertical=8),
            expand=True
        )

        def on_seed_change(e):
            self.bt_seed = seed_field.value

        seed_field.on_change = on_seed_change

        # 직접 날짜 선택 필드
        default_start_date = cur_s_date
        default_end_date = cur_e_date

        custom_date_summary = ft.Text(
            f"직접 기간: {default_start_date} ~ {default_end_date}",
            size=12,
            weight=ft.FontWeight.BOLD,
            color=ACCENT_BLUE
        )

        start_date_field = ft.TextField(
            label="시작일 (YYYY-MM-DD)",
            value=default_start_date,
            read_only=True,
            on_click=lambda _: self.open_custom_date_dialog(start_date_field, end_date_field, custom_date_summary),
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY,
            expand=True,
            suffix=ft.IconButton(
                icon=ft.Icons.CALENDAR_MONTH,
                icon_color=ACCENT_BLUE,
                tooltip="시작일 달력 선택",
                on_click=lambda _: self.open_custom_date_dialog(start_date_field, end_date_field, custom_date_summary)
            )
        )

        end_date_field = ft.TextField(
            label="종료일 (YYYY-MM-DD)",
            value=default_end_date,
            read_only=True,
            on_click=lambda _: self.open_custom_date_dialog(start_date_field, end_date_field, custom_date_summary),
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY,
            expand=True,
            suffix=ft.IconButton(
                icon=ft.Icons.CALENDAR_MONTH,
                icon_color=ACCENT_BLUE,
                tooltip="종료일 달력 선택",
                on_click=lambda _: self.open_custom_date_dialog(start_date_field, end_date_field, custom_date_summary)
            )
        )

        custom_date_container = ft.Container(
            visible=cur_custom_vis,
            bgcolor=SURFACE_CONTAINER,
            border=ft.Border.all(1, ACCENT_BLUE),
            border_radius=10,
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            content=ft.Column(
                controls=[
                    ft.Row([
                        ft.Icon(ft.Icons.DATE_RANGE, color=ACCENT_BLUE, size=16),
                        custom_date_summary,
                        ft.Container(expand=True),
                        ft.FilledButton(
                            "날짜 변경 창 열기",
                            icon=ft.Icons.EDIT_CALENDAR,
                            style=ft.ButtonStyle(
                                bgcolor=ACCENT_BLUE,
                                color=ft.Colors.BLACK,
                                padding=ft.Padding.symmetric(horizontal=10, vertical=6)
                            ),
                            on_click=lambda _: self.open_custom_date_dialog(start_date_field, end_date_field, custom_date_summary)
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Row([start_date_field, end_date_field], spacing=8)
                ],
                spacing=8
            )
        )

        def open_custom_date_flow(e=None):
            period_dd.value = "직접 날짜 선택 (사용자 지정)"
            self.bt_period = "직접 날짜 선택 (사용자 지정)"
            custom_date_container.visible = True
            self.bt_custom_visible = True
            try:
                period_dd.update()
                custom_date_container.update()
                self.page.update()
            except Exception:
                pass
            self.open_custom_date_dialog(start_date_field, end_date_field, custom_date_summary)

        def on_period_change(e):
            val = getattr(e.control, 'value', None) or period_dd.value
            self.bt_period = val
            if val and "직접" in val:
                open_custom_date_flow()
            else:
                custom_date_container.visible = False
                self.bt_custom_visible = False
                try:
                    custom_date_container.update()
                    self.page.update()
                except Exception:
                    pass

        period_dd.on_select = on_period_change
        period_dd.on_change = on_period_change

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
            p_val = period_dd.value

            # 사용자가 선택한 입력 상태 보존
            self.bt_ticker = t
            self.bt_period = p_val
            self.bt_seed = seed_field.value
            self.bt_strat_jongjong = cb_jongjong.value
            self.bt_strat_infinite = cb_infinite.value
            self.bt_strat_vr = cb_vr.value
            self.bt_strat_bnh = cb_bnh.value
            self.bt_start_date = start_date_field.value
            self.bt_end_date = end_date_field.value
            self.bt_custom_visible = custom_date_container.visible

            selected_strats = []
            if cb_jongjong.value:
                selected_strats.append(('종종이 기본전략', PROFIT_GREEN, False))
            if cb_infinite.value:
                selected_strats.append(('무한매수법 v4.0', RESERVE_AMBER, False))
            if cb_vr.value:
                selected_strats.append(('VR 5.0 (밸류리밸런싱)', VR_PURPLE, False))
            if cb_bnh.value:
                selected_strats.append((f'{t} 단순보유(B&H)', ACCENT_BLUE, True))

            if not selected_strats:
                show_toast(self.page, "비교 검증할 전략을 최소 1개 이상 선택해주세요.", is_error=True)
                return

            try:
                cap = float(seed_field.value.strip())
            except Exception:
                cap = 200000.0

            # 기간 환산
            now = datetime.now()
            if p_val == "직접 날짜 선택 (사용자 지정)":
                s_date = start_date_field.value.strip()
                e_date = end_date_field.value.strip()
                try:
                    datetime.strptime(s_date, '%Y-%m-%d')
                    datetime.strptime(e_date, '%Y-%m-%d')
                except Exception:
                    show_toast(self.page, "날짜 형식이 올바르지 않습니다 (YYYY-MM-DD)", is_error=True)
                    return
                if s_date >= e_date:
                    show_toast(self.page, "종료일은 시작일보다 이후여야 합니다.", is_error=True)
                    return
            elif p_val == "최근 1년":
                s_date = (now - timedelta(days=365)).strftime('%Y-%m-%d')
                e_date = now.strftime('%Y-%m-%d')
            elif p_val == "최근 2년":
                s_date = (now - timedelta(days=730)).strftime('%Y-%m-%d')
                e_date = now.strftime('%Y-%m-%d')
            elif p_val == "최근 3년":
                s_date = (now - timedelta(days=1095)).strftime('%Y-%m-%d')
                e_date = now.strftime('%Y-%m-%d')
            elif p_val == "최근 5년":
                s_date = (now - timedelta(days=1825)).strftime('%Y-%m-%d')
                e_date = now.strftime('%Y-%m-%d')
            else:
                s_date = '2019-01-01'
                e_date = now.strftime('%Y-%m-%d')

            loading_icon_hourglass = ft.Icon(ft.Icons.HOURGLASS_TOP, color=RESERVE_AMBER, size=24)
            loading_icon_gear = ft.Icon(ft.Icons.SETTINGS, color=ACCENT_BLUE, size=24)

            loading_status_text = ft.Text(
                "[1/3] 📡 야후 파이낸스 시세 데이터 다운로드 중...",
                size=12,
                color=TEXT_PRIMARY,
                weight=ft.FontWeight.W_600,
                text_align=ft.TextAlign.CENTER
            )
            loading_sub_text = ft.Text(
                f"{t} ({s_date} ~ {e_date}) 일봉 데이터를 수신하고 있습니다.",
                size=11,
                color=TEXT_SECONDARY,
                text_align=ft.TextAlign.CENTER
            )

            loading_dlg = ft.AlertDialog(
                modal=True,
                content=ft.Container(
                    width=330,
                    padding=ft.Padding.symmetric(horizontal=18, vertical=22),
                    content=ft.Column(
                        controls=[
                            ft.Row([
                                # 모래시계 회전 인디케이터
                                ft.Stack([
                                    ft.ProgressRing(color=RESERVE_AMBER, width=56, height=56, stroke_width=3.5),
                                    ft.Container(
                                        content=loading_icon_hourglass,
                                        alignment=ft.Alignment(0, 0),
                                        width=56,
                                        height=56
                                    )
                                ]),
                                # 톱니바퀴 회전 인디케이터
                                ft.Stack([
                                    ft.ProgressRing(color=ACCENT_BLUE, width=56, height=56, stroke_width=3.5),
                                    ft.Container(
                                        content=loading_icon_gear,
                                        alignment=ft.Alignment(0, 0),
                                        width=56,
                                        height=56
                                    )
                                ]),
                            ], alignment=ft.MainAxisAlignment.CENTER, spacing=24),
                            ft.Container(height=8),
                            ft.Text("백테스트 시뮬레이션 진행 중", size=16, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                            ft.Container(height=4),
                            ft.ProgressBar(color=ACCENT_BLUE, bgcolor=SURFACE_CONTAINER, value=None, width=280),
                            ft.Container(height=6),
                            loading_status_text,
                            loading_sub_text,
                            ft.Container(height=4),
                            ft.Container(
                                content=ft.Text(
                                    "연산 중 잠시만 기다려주세요 (화면이 멈춘 것이 아닙니다)",
                                    size=10,
                                    color=TEXT_MUTED,
                                    text_align=ft.TextAlign.CENTER
                                ),
                                alignment=ft.Alignment(0, 0)
                            )
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=6,
                        tight=True
                    )
                ),
                bgcolor=SURFACE_CARD,
                shape=ft.RoundedRectangleBorder(radius=16)
            )

            progress_ring.visible = True
            original_btn_content = run_btn.content
            run_btn.content = ft.Row([
                ft.ProgressRing(width=16, height=16, stroke_width=2.5, color=ft.Colors.BLACK),
                ft.Text("시뮬레이션 연산 진행 중...", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=8)
            run_btn.disabled = True

            self.page.show_dialog(loading_dlg)
            self.page.update()

            def worker():
                try:
                    # 1. 시세 데이터 다운로드
                    loading_icon_hourglass.name = ft.Icons.HOURGLASS_TOP
                    loading_status_text.value = f"[1/3] 📡 {t} 시세 데이터 수신 중..."
                    loading_sub_text.value = f"{s_date} ~ {e_date} 일봉 데이터를 다운로드하고 있습니다."
                    self.page.update()

                    df_market = fetch_market_data(t, s_date, e_date)
                    if df_market is None or df_market.empty:
                        try:
                            self.page.pop_dialog()
                        except Exception:
                            pass
                        show_toast(self.page, f"{t} 시장 데이터를 불러오지 못했습니다.", is_error=True)
                        return

                    # 2. 전략별 시뮬레이션
                    loading_icon_hourglass.name = ft.Icons.HOURGLASS_BOTTOM
                    loading_status_text.value = "[2/3] ⚙️ 전략별 매매 & 복리 시뮬레이션 연산 중..."
                    loading_sub_text.value = f"총 {len(selected_strats)}개 전략의 조각 매수/익절/시간손절을 계산 중입니다."
                    self.page.update()

                    multi_results = []
                    series_for_chart = []

                    for strat_name, color, is_dash in selected_strats:
                        if "종종이" in strat_name:
                            st = JongJongStrategy(initial_capital=cap, reserve_ratio=0.05)
                        elif "무한" in strat_name:
                            st = InfiniteBuyingV4Strategy(ticker=t, initial_capital=cap, divisions=40)
                        elif "VR" in strat_name:
                            st = ValueRebalancingV5Strategy(ticker=t, initial_capital=cap, g_value=10.0, band_pct=0.15)
                        else:
                            st = BuyAndHoldStrategy(name=f"{t} 단순보유", initial_capital=cap)

                        df_s = st.run(df_market, s_date, e_date)
                        m_s = calculate_metrics(df_s, cap)

                        multi_results.append({
                            'name': strat_name,
                            'color': color,
                            'metrics': m_s,
                            'df': df_s
                        })

                        date_fmt = '%y/%m' if len(df_s) > 365 else '%m/%d'
                        series_for_chart.append({
                            'name': strat_name,
                            'color': color,
                            'dash': is_dash,
                            'dates': [pd.to_datetime(d).strftime(date_fmt) for d in df_s['Date']],
                            'vals': df_s['Asset'].values.tolist()
                        })

                    # 3. 차트 렌더링
                    loading_icon_hourglass.name = ft.Icons.HOURGLASS_FULL
                    loading_status_text.value = "[3/3] 📊 고해상도 성과 차트 및 지표 렌더링 중..."
                    loading_sub_text.value = "결과 대시보드를 생성하고 있습니다."
                    self.page.update()

                    chart_b64, bt_dates, valid_series = render_multi_backtest_chart(series_for_chart, t)
                    self.bt_chart_dates = bt_dates
                    self.bt_chart_series = valid_series

                    self.bt_results = {
                        'ticker': t,
                        'period': f"{s_date} ~ {e_date}",
                        'initial_capital': cap,
                        'chart_b64': chart_b64,
                        'results': multi_results
                    }

                    try:
                        self.page.pop_dialog()
                    except Exception:
                        pass
                    show_toast(self.page, f"{t} ({len(multi_results)}개 전략) 백테스트 완료!")
                except Exception as ex:
                    try:
                        self.page.pop_dialog()
                    except Exception:
                        pass
                    show_toast(self.page, f"백테스트 실패: {ex}", is_error=True)
                finally:
                    run_btn.content = original_btn_content
                    run_btn.disabled = False
                    progress_ring.visible = False
                    self._render_current_view()

            self.page.run_thread(worker)

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
                        ft.Row([
                            ft.Container(content=ticker_dd, width=125),
                            period_dd,
                            ft.OutlinedButton(
                                content=ft.Row([
                                    ft.Icon(ft.Icons.CALENDAR_MONTH, size=14, color=ACCENT_BLUE),
                                    ft.Text("직접선택", size=11, color=ACCENT_BLUE)
                                ], spacing=3),
                                style=ft.ButtonStyle(
                                    side=ft.BorderSide(1, ACCENT_BLUE),
                                    shape=ft.RoundedRectangleBorder(radius=8),
                                    padding=ft.Padding.symmetric(horizontal=6, vertical=8)
                                ),
                                tooltip="직접 시작일/종료일 선택 창을 엽니다.",
                                on_click=open_custom_date_flow
                            )
                        ], spacing=6),
                        custom_date_container,
                        strat_selector,
                        seed_field,
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
            res_list = res.get('results', [])

            self.bt_val_banner = ft.Container(
                bgcolor=SURFACE_CONTAINER,
                border=ft.Border.all(1, BORDER_COLOR),
                border_radius=8,
                padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.TOUCH_APP_OUTLINED, color=ACCENT_BLUE, size=15),
                        ft.Text("그래프를 길게 누르면 해당 위치의 각 전략별 Y 수치가 표시됩니다", size=11, color=TEXT_MUTED)
                    ],
                    spacing=6
                )
            )

            chart_display = ft.Card(
                bgcolor=SURFACE_CARD,
                elevation=2,
                shape=ft.RoundedRectangleBorder(radius=12),
                content=ft.Container(
                    padding=12,
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text(f"{res['ticker']} 전략 비교 자산 곡선", size=13, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                                    ft.Text("길게 누르기: 수치확인 | 핀치: 확대", size=10, color=TEXT_MUTED)
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                            ),
                            ft.Container(height=4),
                            self.bt_val_banner,
                            ft.Container(height=4),
                            ft.Container(
                                height=220,
                                border_radius=8,
                                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                                content=ft.InteractiveViewer(
                                    content=ft.GestureDetector(
                                        content=ft.Image(src=res['chart_b64'], fit="contain", width=650, height=220),
                                        on_long_press_start=lambda e: self._on_bt_chart_inspect(e.local_position.x),
                                        on_long_press_move_update=lambda e: self._on_bt_chart_inspect(e.local_position.x),
                                        on_tap_down=lambda e: self._on_bt_chart_inspect(e.local_position.x)
                                    ),
                                    constrained=True,
                                    min_scale=1.0,
                                    max_scale=4.0,
                                    pan_enabled=True,
                                    scale_enabled=True,
                                    clip_behavior=ft.ClipBehavior.HARD_EDGE
                                )
                            )
                        ]
                    )
                )
            )

            # 각 전략별 비교 성과 요약 카드 리스트
            strat_cards = []
            for r in res_list:
                m = r['metrics']
                col = r['color']
                name = r['name']
                f_asset = m.get('final_asset', 0.0)
                tot_ret = m.get('total_return', 0.0)
                cagr = m.get('cagr', 0.0)
                mdd = m.get('mdd', 0.0)
                sharpe = m.get('sharpe', 0.0)
                t_days = m.get('trading_days', 0)
                is_win = tot_ret >= 0

                card = ft.Container(
                    bgcolor=SURFACE_CARD,
                    border=ft.Border.all(1, col if len(res_list) > 1 else BORDER_COLOR),
                    border_radius=12,
                    padding=12,
                    content=ft.Column(
                        controls=[
                            ft.Row([
                                ft.Container(width=10, height=10, bgcolor=col, border_radius=5),
                                ft.Text(f"{name}", size=13, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY, expand=True),
                                ft.Text(f"{tot_ret:+.2f}%", size=14, weight=ft.FontWeight.BOLD, color=PROFIT_GREEN if is_win else LOSS_RED)
                            ], spacing=6),
                            ft.Divider(color=BORDER_COLOR, height=1),
                            ft.Row([
                                ft.Column([
                                    ft.Text("최종 자산", size=10, color=TEXT_MUTED),
                                    ft.Text(f"${f_asset:,.0f}", size=13, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                                ], spacing=1, expand=True),
                                ft.Column([
                                    ft.Text("CAGR (연복리)", size=10, color=TEXT_MUTED),
                                    ft.Text(f"{cagr:+.2f}%", size=13, weight=ft.FontWeight.BOLD, color=ACCENT_BLUE),
                                ], spacing=1, expand=True),
                                ft.Column([
                                    ft.Text("MDD (최대낙폭)", size=10, color=TEXT_MUTED),
                                    ft.Text(f"{mdd:.2f}%", size=13, weight=ft.FontWeight.BOLD, color=LOSS_RED),
                                ], spacing=1, expand=True),
                                ft.Column([
                                    ft.Text("샤프 / 거래일", size=10, color=TEXT_MUTED),
                                    ft.Text(f"{sharpe:.2f} ({t_days}일)", size=12, color=TEXT_SECONDARY),
                                ], spacing=1, expand=True),
                            ], spacing=6)
                        ],
                        spacing=6
                    )
                )
                strat_cards.append(card)

            results_widgets = [
                ft.Container(height=4),
                ft.Row([
                    ft.Text(f"📊 검증 결과 비교 ({res['period']})", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                ]),
                chart_display,
                ft.Container(height=2),
                *strat_cards
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
                            ft.Text("종목, 복수 전략 및 기간을 설정한 후 [백테스트 실행]을 눌러보세요.", size=11, color=TEXT_MUTED, text_align=ft.TextAlign.CENTER)
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
    # TAB 3: 💡 투자 전략 (종종이 & 무한매수 전략 상세 소개)
    # =================================================================
    def _build_strategies_tab(self):
        # 1. 헤더 카드
        header_card = ft.Card(
            bgcolor=SURFACE_CARD,
            elevation=3,
            shape=ft.RoundedRectangleBorder(radius=14),
            content=ft.Container(
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Row([
                            ft.Icon(ft.Icons.LIGHTBULB, color=ACCENT_BLUE, size=22),
                            ft.Text("투자 전략 가이드", size=16, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        ], spacing=8),
                        ft.Container(height=2),
                        ft.Text(
                            "미국 3배 레버리지 ETF(SOXL, TQQQ 등)의 극심한 변동성을 역이용하여, "
                            "시장 예측과 인간의 감정(공포·탐욕)을 배제하고 수학적 분할 매매와 기계적 원칙으로 "
                            "안정적이고 지속적인 우상향 복리 수익을 달성하는 2대 핵심 시스템입니다.",
                            size=12,
                            color=TEXT_SECONDARY
                        )
                    ],
                    spacing=4
                )
            )
        )

        # 2. 종종이 기본전략 카드
        def make_section_title(icon, title, color):
            return ft.Row([
                ft.Icon(icon, color=color, size=16),
                ft.Text(title, size=13, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
            ], spacing=6)

        def make_bullet_point(title, desc):
            return ft.Column([
                ft.Text(f"• {title}", size=12, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                ft.Container(
                    padding=ft.Padding.only(left=12),
                    content=ft.Text(desc, size=11, color=TEXT_SECONDARY)
                )
            ], spacing=2)

        # 2. 종종이 기본전략 카드 (실제 코드 logic 100% 정밀 반영)
        jongjong_card = ft.Card(
            bgcolor=SURFACE_CARD,
            elevation=2,
            shape=ft.RoundedRectangleBorder(radius=14),
            content=ft.Container(
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Row([
                            ft.Container(
                                content=ft.Text("전략 1", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK),
                                bgcolor=PROFIT_GREEN,
                                padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                                border_radius=6
                            ),
                            ft.Text("종종이 기본전략 (JongJong)", size=15, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        ], spacing=8),
                        ft.Container(height=4),
                        ft.Text("3단계 시장 모드(8/7/5 분할) & 조각별 100% 독립 운영 시스템", size=12, color=PROFIT_GREEN, weight=ft.FontWeight.W_500),
                        ft.Divider(color=BORDER_COLOR, height=1),

                        make_section_title(ft.Icons.AUTO_GRAPH, "핵심 운용 철학", PROFIT_GREEN),
                        ft.Text(
                            "레버리지 ETF의 추세와 변동성을 3단계 시장 모드(Normal/Safe/Riskoff)로 자동 진단하고, "
                            "모드별로 차등 분할 매수합니다. 매수 체결된 각 조각(Lot)은 전체 평단가에 묶이지 않고 "
                            "각각 고유 매입가와 목표가를 가진 '100% 독립 조각'으로 운영되며, 목표가 도달 시 개별 익절하고 "
                            "10거래일 내 미익절 시 기계적으로 시간손절(MOC)하여 시드 고착을 완벽 차단합니다.",
                            size=11, color=TEXT_SECONDARY
                        ),
                        ft.Container(height=4),

                        make_section_title(ft.Icons.SPEED, "3단계 시장 모드 & 차등 분할 전략", PROFIT_GREEN),
                        make_bullet_point(
                            "Normal 모드 (일반 상승/횡보장, 8분할)",
                            "가용 시드(AR)를 8등분(AR / 8.0)하여 매일 LOC 매수 주문을 제출합니다. "
                            "목표 익절 수익률은 +2.75%이며, 정상 변동성 밴드(±12.8%) 내에서 적극적으로 수익을 창출합니다."
                        ),
                        make_bullet_point(
                            "Safe 모드 (단기 급락 감지 / 안전 모드, 7분할)",
                            "주가가 20일 이평선(MA20)을 하회한 상태에서 -3% 이상 급락하거나 단기 -8% 이상 급락 시 자동 발동합니다. "
                            "가용 시드를 7등분(AR / 7.0)하여 매수하고, 목표 익절률을 +0.25%로 극도로 낮추어 원금 방어 및 신속한 본전 탈출에 집중합니다."
                        ),
                        make_bullet_point(
                            "Riskoff 모드 (위험 회피 / 추세 붕괴, 5분할)",
                            "전일 급락 Flag 경고가 발생했거나 고점 대비 위험 낙폭에 도달했을 때 발동합니다. "
                            "가용 시드를 5등분(AR / 5.0)으로 초긴축 방어 운용하며, 전일 종가 대비 -5.5% 이하 저가에서만 매수하여 목표 익절률 +0.70%로 자산을 지킵니다."
                        ),
                        ft.Container(height=4),

                        make_section_title(ft.Icons.VIEW_QUILT, "조각(Lot)별 100% 독립 운영 메커니즘", PROFIT_GREEN),
                        make_bullet_point(
                            "조각별 개별 목표가 익절 (독립 체결)",
                            "매일 매수한 주식은 다른 날짜 매수분과 물타기(합산)되지 않고, 각각의 고유 매입단가(S)와 개별 목표가(U)를 갖는 독자적 조각으로 살아있습니다. "
                            "당일 종가가 특정 조각의 목표가에 도달하면 해당 조각만 단독 익절 매도되어 현금이 즉시 회수됩니다."
                        ),
                        make_bullet_point(
                            "10거래일 기계적 시간손절 (10-Day Time Cut / MOC)",
                            "매수 후 10거래일이 경과하도록 목표가에 도달하지 못한 조각은 10일째 장 마감(MOC)에 기계적으로 전량 시장가 매도(손절)합니다. "
                            "이를 통해 하락장에 물량이 영구 고착되는 것을 막고, 회수된 현금으로 바닥 구간에서 새로운 조각을 매수하여 가파른 복리 반등을 만듭니다."
                        ),
                        ft.Container(height=4),

                        make_section_title(ft.Icons.SCHEDULE_SEND, "당일 5분할 비선형 LOC 예약 매수", PROFIT_GREEN),
                        make_bullet_point(
                            "수학적 곡률(Curvature 0.7) 5분할 주문",
                            "당일 매수 예정 예산(P = AR / 모드별분할수)을 5개의 LOC 호가로 비선형 분할하여, "
                            "주가가 깊게 하락할수록 기하급수적으로 더 많은 수량이 체결되도록 설계된 스마트 주문표입니다."
                        ),
                        ft.Container(height=4),

                        make_section_title(ft.Icons.ACCOUNT_BALANCE_WALLET, "위기준비금(AK, 5%) & 10거래일 복리 주기", PROFIT_GREEN),
                        make_bullet_point(
                            "위기준비금(AK, 5%) 영구 격리",
                            "전체 자본의 5%는 비상금으로 분리하여 평상시 매수에 투입하지 않고 계좌 최후의 안전판으로 보존합니다."
                        ),
                        make_bullet_point(
                            "10거래일 복리 정산 및 재투자",
                            "매 10거래일마다 누적 실현손익을 정산하여 5%는 위기준비금으로 적립하고, 95%는 실가동 시드(AR)에 합산하여 원금을 키우는 복리 시스템이 자동 가동됩니다."
                        ),
                    ],
                    spacing=8
                )
            )
        )

        # 3. 라오어 무한매수법 v4.0 카드
        infinite_card = ft.Card(
            bgcolor=SURFACE_CARD,
            elevation=2,
            shape=ft.RoundedRectangleBorder(radius=14),
            content=ft.Container(
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Row([
                            ft.Container(
                                content=ft.Text("전략 2", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK),
                                bgcolor=RESERVE_AMBER,
                                padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                                border_radius=6
                            ),
                            ft.Text("라오어 무한매수법 v4.0", size=15, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        ], spacing=8),
                        ft.Container(height=4),
                        ft.Text("매일 40분할 기계적 루틴 매수 & 사이클당 10% 확정 익절", size=12, color=RESERVE_AMBER, weight=ft.FontWeight.W_500),
                        ft.Divider(color=BORDER_COLOR, height=1),

                        make_section_title(ft.Icons.ACCESS_TIME, "핵심 운용 철학", RESERVE_AMBER),
                        ft.Text(
                            "정해진 원금을 40분할하여 매일 밤 LOC(Limit-on-Close) 주문을 제출, "
                            "시장 상승/하락에 상관없이 1일 1회 정해진 규칙대로 매매하여 사이클당 +10% 수익을 확정 짓는 직장인 최적화 전략입니다.",
                            size=11, color=TEXT_SECONDARY
                        ),
                        ft.Container(height=4),

                        make_section_title(ft.Icons.LOOKS_ONE, "전반전 (1회차 ~ 20회차)", RESERVE_AMBER),
                        make_bullet_point("0.5회분 LOC 평단 매수", "종가가 내 평단가 이하일 때만 체결되어 평단가를 적극적으로 낮춥니다."),
                        make_bullet_point("0.5회분 LOC 큰수 매수", "종가가 평단가 * 1.05 이하일 때 체결되도록 하여 무조건 1회분 매수를 채웁니다."),
                        make_bullet_point("전량 +10% 지정가 매도", "보유 중인 모든 수량을 평단가 +10% 가격에 매일 지정가 매도 주문을 걸어둡니다."),
                        ft.Container(height=4),

                        make_section_title(ft.Icons.LOOKS_TWO, "후반전 (21회차 ~ 40회차)", RESERVE_AMBER),
                        make_bullet_point("0.5회분만 보수적 매수", "원금 소진을 늦추기 위해 매일 0.5회분만 평단가 이하 LOC로 매수하고, 나머지 0.5회분은 현금을 보존합니다."),
                        make_bullet_point("본전 탈출 및 분할 매도", "평단가 +5%~+10% 구간에서 보유 수량을 분할 매도하여 안전하게 사이클을 마무리합니다."),
                        ft.Container(height=4),

                        make_section_title(ft.Icons.REFRESH, "쿼터 손절 및 리셋 룰", RESERVE_AMBER),
                        make_bullet_point("40회차 소진 시 대응", "40회차까지 익절하지 못했을 경우, 보유 주식의 25%(1/4)를 기계적으로 손절하여 새로운 매수 시드를 창출하고 사이클을 연장합니다.")
                    ],
                    spacing=8
                )
            )
        )

        # 4. 라오어 밸류리밸런싱 VR 5.0 카드
        vr_card = ft.Card(
            bgcolor=SURFACE_CARD,
            elevation=2,
            shape=ft.RoundedRectangleBorder(radius=14),
            content=ft.Container(
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Row([
                            ft.Container(
                                content=ft.Text("전략 3", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                bgcolor=VR_PURPLE,
                                padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                                border_radius=6
                            ),
                            ft.Text("라오어 밸류리밸런싱 VR 5.0", size=15, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        ], spacing=8),
                        ft.Container(height=4),
                        ft.Text("2주 사이클 밸류 밴드(±15%) & 풀(Pool) 기반 자동 리밸런싱", size=12, color=VR_PURPLE, weight=ft.FontWeight.W_500),
                        ft.Divider(color=BORDER_COLOR, height=1),

                        make_section_title(ft.Icons.AUTO_AWESOME, "핵심 운용 철학", VR_PURPLE),
                        ft.Text(
                            "목표 평가액 가이드라인 곡선 V를 설정하고, 2주(10거래일)마다 증권사에 기간예약 주문을 걸어두어 "
                            "주가가 상하단 밴드(V ±15%)를 벗어날 때만 기계적으로 매수/매도하여 밴드로 복귀시키는 중장기 레버리지 자산배분 전략입니다.",
                            size=11, color=TEXT_SECONDARY
                        ),
                        ft.Container(height=4),

                        make_section_title(ft.Icons.CALENDAR_MONTH, "2주(10거래일) 사이클 & V 갱신 공식", VR_PURPLE),
                        make_bullet_point("V 갱신 공식", "다음 V = 현재 V + (Pool / G) ± (적립금 or 인출금)"),
                        make_bullet_point("G(기울기) 인자", "G=10(기본/적립·거치) ~ G=20(인출식/보수적)으로 V의 상승 속도를 조절합니다."),
                        make_bullet_point("현금 풀(Pool)", "하락장에서 든든한 매수 방패 역할을 하며, 상승 익절 시 수익금을 흡수하여 현금을 비축합니다."),
                        ft.Container(height=4),

                        make_section_title(ft.Icons.SWAP_VERT, "2주치 예약 주문 (상·하단 밴드)", VR_PURPLE),
                        make_bullet_point("하단 밴드 매수 (V * 0.85)", "주가 하락 시 P_buy = V_min / n 가격에 순차 매수하여 Pool을 소진하고 주식 비중을 늘립니다."),
                        make_bullet_point("상단 밴드 매도 (V * 1.15)", "주가 급등 시 P_sell = V_max / n 가격에 분할 익절하여 확정 수익을 Pool로 회수합니다."),
                        ft.Container(height=4),

                        make_section_title(ft.Icons.SAVINGS, "운용 유형별 Pool 한도", VR_PURPLE),
                        make_bullet_point("적립식 VR", "2주마다 적립금 추가 투입 + 사이클당 Pool의 75%까지 매수 사용"),
                        make_bullet_point("거치식 VR", "원금 일시 거치 + 사이클당 Pool의 50%까지 매수 사용"),
                        make_bullet_point("인출식 VR", "2주마다 생활비 인출 + 사이클당 Pool의 25%까지 보수적 매수 사용")
                    ],
                    spacing=8
                )
            )
        )

        # 5. 전략 비교 매트릭스 카드
        def make_comparison_row(title, v1, v2, v3):
            return ft.Container(
                padding=ft.Padding.symmetric(vertical=6),
                border=ft.Border(bottom=ft.BorderSide(1, BORDER_COLOR)),
                content=ft.Row([
                    ft.Text(title, size=11, weight=ft.FontWeight.BOLD, color=TEXT_MUTED, width=65),
                    ft.Text(v1, size=10, color=PROFIT_GREEN, expand=1),
                    ft.Text(v2, size=10, color=RESERVE_AMBER, expand=1),
                    ft.Text(v3, size=10, color=VR_PURPLE, expand=1),
                ], spacing=4)
            )

        comparison_card = ft.Card(
            bgcolor=SURFACE_CARD,
            elevation=2,
            shape=ft.RoundedRectangleBorder(radius=14),
            content=ft.Container(
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Row([
                            ft.Icon(ft.Icons.COMPARE_ARROWS, color=ACCENT_BLUE, size=18),
                            ft.Text("3대 투자 전략 한눈에 비교", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        ], spacing=6),
                        ft.Container(height=4),
                        ft.Row([
                            ft.Text("구분", size=11, weight=ft.FontWeight.BOLD, color=TEXT_MUTED, width=65),
                            ft.Text("종종이 기본", size=10.5, weight=ft.FontWeight.BOLD, color=PROFIT_GREEN, expand=1),
                            ft.Text("무한매수 v4", size=10.5, weight=ft.FontWeight.BOLD, color=RESERVE_AMBER, expand=1),
                            ft.Text("VR 5.0", size=10.5, weight=ft.FontWeight.BOLD, color=VR_PURPLE, expand=1),
                        ], spacing=4),
                        ft.Divider(color=BORDER_COLOR, height=1),
                        make_comparison_row("주요 대상", "SOXL 등 3X", "TQQQ/SOXL", "TQQQ/QLD 3X/2X"),
                        make_comparison_row("매매 주기", "매일 밤 LOC", "매일 밤 LOC", "2주(10일) 1회 예약"),
                        make_comparison_row("시드 분할", "8/7/5 분할", "40분할 고정", "V ±15% 밴드 분할"),
                        make_comparison_row("조각 운용", "조각별 독립 익절", "전체 평단 통합", "전체 밸류 밴드"),
                        make_comparison_row("현금 관리", "위기준비금 5%", "전액 시드 소진", "Pool 현금 (15~50%)"),
                        make_comparison_row("목표 수익", "0.25% ~ 2.75%", "사이클당 +10%", "밴드 상단 돌파 익절"),
                        make_comparison_row("손절 원칙", "10일 MOC 청산", "40회차 쿼터손절", "원칙적 손절 없음"),
                        make_comparison_row("추천 성향", "고변동성 공략", "정형화된 루틴", "게으른 장기 투자"),
                    ],
                    spacing=2
                )
            )
        )

        return ft.ListView(
            controls=[
                header_card,
                ft.Container(height=6),
                jongjong_card,
                ft.Container(height=6),
                infinite_card,
                ft.Container(height=6),
                vr_card,
                ft.Container(height=6),
                comparison_card,
                ft.Container(height=24)
            ],
            spacing=8,
            expand=True
        )

    # =================================================================
    # TAB 3: ⚙ 설정 (CSV 내보내기 & 시스템 환경 설정)
    # =================================================================
    def _build_settings_tab(self):

        storage_base = os.environ.get("FLET_APP_STORAGE_DATA") or CURRENT_DIR
        exports_dir = os.path.join(storage_base, "exports")
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

        # 2. Google Drive 클라우드 실시간 동기화 (Multi-Device Sync) 카드
        sync_cfg = get_sync_config()
        is_enabled = sync_cfg.get("sync_enabled", False)
        curr_url = sync_cfg.get("web_app_url", "")
        last_t = sync_cfg.get("last_sync_time") or "기록 없음"
        last_m = sync_cfg.get("last_sync_message") or ""

        sync_url_field = ft.TextField(
            label="Google Apps Script 웹 앱 URL",
            label_style=ft.TextStyle(size=11, color=TEXT_SECONDARY),
            value=curr_url,
            hint_text="https://script.google.com/macros/s/.../exec",
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY,
            text_size=11.5,
            dense=True,
            content_padding=ft.Padding.symmetric(horizontal=10, vertical=8),
            expand=True
        )

        sync_status_text = ft.Text(
            f"• 상태: {'실시간 자동 동기화 가동 중 (Sync ON)' if (is_enabled and curr_url) else '동기화 꺼짐 (Sync OFF - 로컬 기기 보관)'}\n"
            f"• 최근 동기화: {last_t} ({last_m})\n"
            f"• 드라이브 폴더: Google Drive / JongJongTrader / accounts.json",
            size=11,
            color=PROFIT_GREEN if (is_enabled and curr_url) else TEXT_MUTED
        )

        sync_loading = ft.ProgressBar(visible=False, color=ACCENT_BLUE)

        def update_sync_status_ui():
            cfg = get_sync_config()
            en = cfg.get("sync_enabled", False)
            u = cfg.get("web_app_url", "")
            t = cfg.get("last_sync_time") or "기록 없음"
            m = cfg.get("last_sync_message") or ""
            is_active = bool(en and u)
            sync_status_text.value = (
                f"• 상태: {'실시간 자동 동기화 가동 중 (Sync ON)' if is_active else '동기화 꺼짐 (Sync OFF - 로컬 기기 보관)'}\n"
                f"• 최근 동기화: {t} ({m})\n"
                f"• 드라이브 폴더: Google Drive / JongJongTrader / accounts.json"
            )
            sync_status_text.color = PROFIT_GREEN if is_active else TEXT_MUTED
            sync_badge.content = ft.Text("Sync ON" if is_active else "Sync OFF", color=ft.Colors.WHITE, size=11, weight=ft.FontWeight.BOLD)
            sync_badge.bgcolor = PROFIT_GREEN if is_active else LOSS_RED
            sync_control_box.border = ft.Border.all(1, PROFIT_GREEN if is_active else BORDER_COLOR)
            sync_switch.value = is_active
            try:
                sync_status_text.update()
                sync_badge.update()
                sync_control_box.update()
                sync_switch.update()
            except Exception:
                pass

        def on_sync_switch_change(e):
            val = e.control.value
            cfg = get_sync_config()
            u = sync_url_field.value.strip()
            if val and (not u or not u.startswith("http")):
                e.control.value = False
                e.control.update()
                show_toast(self.page, "Google Apps Script 웹 앱 URL을 먼저 입력해주세요.", is_error=True)
                return
            cfg["sync_enabled"] = val
            cfg["web_app_url"] = u
            save_sync_config(cfg)
            update_sync_status_ui()
            if val:
                show_toast(self.page, "Google Drive 실시간 동기화가 활성화되었습니다!")
                import threading
                def _initial_sync():
                    sync_loading.visible = True
                    sync_loading.update()
                    ok, msg = sync_local_with_drive(self.am)
                    sync_loading.visible = False
                    sync_loading.update()
                    update_sync_status_ui()
                    if ok:
                        show_toast(self.page, msg)
                        self.reload_data()
                    else:
                        show_toast(self.page, f"동기화 오류: {msg}", is_error=True)
                threading.Thread(target=_initial_sync, daemon=True).start()
            else:
                show_toast(self.page, "Google Drive 동기화가 비활성화되었습니다. (로컬 단독 저장)")

        sync_badge = ft.Container(
            content=ft.Text("Sync ON" if is_enabled else "Sync OFF", color=ft.Colors.WHITE, size=11, weight=ft.FontWeight.BOLD),
            bgcolor=PROFIT_GREEN if is_enabled else LOSS_RED,
            padding=ft.Padding.symmetric(horizontal=8, vertical=3),
            border_radius=6
        )

        sync_switch = ft.Switch(
            value=is_enabled,
            active_color=PROFIT_GREEN,
            inactive_thumb_color=ft.Colors.GREY_500,
            on_change=on_sync_switch_change
        )

        sync_control_box = ft.Container(
            bgcolor=SURFACE_CONTAINER,
            border=ft.Border.all(1, PROFIT_GREEN if is_enabled else BORDER_COLOR),
            border_radius=10,
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            content=ft.Row(
                controls=[
                    ft.Row([
                        ft.Icon(ft.Icons.POWER_SETTINGS_NEW, size=18, color=PROFIT_GREEN if is_enabled else TEXT_MUTED),
                        ft.Text("실시간 동기화 상태:", size=12.5, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        sync_badge
                    ], spacing=6),
                    sync_switch
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            )
        )

        def handle_save_url(e):
            u = sync_url_field.value.strip()
            if not u or not u.startswith("http"):
                show_toast(self.page, "올바른 URL을 입력하세요 (https://...)", is_error=True)
                return
            cfg = get_sync_config()
            cfg["web_app_url"] = u
            save_sync_config(cfg)
            show_toast(self.page, "Google Apps Script URL이 저장되었습니다.")
            update_sync_status_ui()

        def handle_test_conn(e):
            u = sync_url_field.value.strip()
            if not u or not u.startswith("http"):
                show_toast(self.page, "Google Apps Script URL을 입력하세요.", is_error=True)
                return
            sync_loading.visible = True
            sync_loading.update()
            import threading
            def _bg():
                ok, msg = test_connection(u)
                sync_loading.visible = False
                sync_loading.update()
                if ok:
                    show_toast(self.page, msg)
                else:
                    show_toast(self.page, f"연결 실패: {msg}", is_error=True)
            threading.Thread(target=_bg, daemon=True).start()

        def handle_sync_now(e):
            if not is_sync_enabled():
                show_toast(self.page, "Google Drive 동기화 스위치를 먼저 켜주세요.", is_error=True)
                return
            sync_loading.visible = True
            sync_loading.update()
            import threading
            def _bg():
                ok, msg = sync_local_with_drive(self.am)
                sync_loading.visible = False
                sync_loading.update()
                update_sync_status_ui()
                if ok:
                    show_toast(self.page, msg)
                    self.reload_data()
                else:
                    show_toast(self.page, f"동기화 실패: {msg}", is_error=True)
            threading.Thread(target=_bg, daemon=True).start()

        def handle_force_upload(e):
            u = sync_url_field.value.strip()
            if not u or not u.startswith("http"):
                show_toast(self.page, "웹 앱 URL을 먼저 입력해주세요.", is_error=True)
                return
            sync_loading.visible = True
            sync_loading.update()
            import threading
            def _bg():
                accs = self.am.load_accounts()
                ok, msg = upload_accounts_to_drive(accs, u)
                sync_loading.visible = False
                sync_loading.update()
                update_sync_status_ui()
                if ok:
                    show_toast(self.page, f"구글 드라이브로 계좌 백업 업로드 완료 ({len(accs)}개 계좌)")
                else:
                    show_toast(self.page, f"업로드 실패: {msg}", is_error=True)
            threading.Thread(target=_bg, daemon=True).start()

        def handle_force_download(e):
            u = sync_url_field.value.strip()
            if not u or not u.startswith("http"):
                show_toast(self.page, "웹 앱 URL을 먼저 입력해주세요.", is_error=True)
                return
            sync_loading.visible = True
            sync_loading.update()
            import threading
            def _bg():
                ok, drive_accs, msg = download_accounts_from_drive(u)
                sync_loading.visible = False
                sync_loading.update()
                update_sync_status_ui()
                if ok and drive_accs is not None:
                    try:
                        if os.path.exists(self.am.filepath):
                            with open(self.am.filepath, 'r', encoding='utf-8') as rf:
                                with open(os.path.join(os.path.dirname(self.am.filepath), "accounts.backup.json"), 'w', encoding='utf-8') as wf:
                                    wf.write(rf.read())
                    except Exception:
                        pass
                    self.am.save_accounts(drive_accs, skip_cloud_sync=True)
                    show_toast(self.page, f"구글 드라이브에서 {len(drive_accs)}개 계좌를 복원했습니다!")
                    self.reload_data()
                else:
                    show_toast(self.page, f"다운로드 실패: {msg}", is_error=True)
            threading.Thread(target=_bg, daemon=True).start()

        def open_gas_guide_dialog(e):
            script_code = get_gas_script_code()
            guide_dlg = ft.AlertDialog(
                modal=True,
                title=ft.Row([
                    ft.Icon(ft.Icons.CLOUD_DONE, color=ACCENT_BLUE, size=20),
                    ft.Text("Google Drive 1분 연동 가이드", size=15, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                ], spacing=8),
                content=ft.Container(
                    width=380,
                    content=ft.Column(
                        controls=[
                            ft.Container(
                                padding=10,
                                bgcolor=SURFACE_CONTAINER,
                                border_radius=8,
                                content=ft.Column(
                                    controls=[
                                        ft.Row([
                                            ft.Icon(ft.Icons.DESKTOP_WINDOWS, size=16, color=ACCENT_BLUE),
                                            ft.Text("PC 브라우저에서 1회 배포 권장 (1분 소요)", size=12, weight=ft.FontWeight.BOLD, color=ACCENT_BLUE)
                                        ], spacing=6),
                                        ft.Text(
                                            "모바일 웹 브라우저는 구글 정책상 개발자 도구('Google Apps Script') 메뉴가 보이지 않습니다.\n"
                                            "PC 브라우저에서 1분 만에 배포 후, 발급된 URL만 카카오톡(나에게 보내기) 등으로 폰에 복사해 오시면 가장 간편합니다!",
                                            size=11, color=TEXT_SECONDARY
                                        ),
                                        ft.Text("※ 폰에서 직접 하려면: 모바일 브라우저 메뉴(⋮)에서 '데스크톱 사이트'를 체크하세요.", size=10, color=TEXT_MUTED),
                                    ],
                                    spacing=4
                                )
                            ),
                            ft.Container(height=4),
                            ft.Container(
                                padding=10,
                                bgcolor=SURFACE_CONTAINER,
                                border_radius=8,
                                content=ft.Column(
                                    controls=[
                                        ft.Text("1. PC 브라우저로 drive.google.com (또는 script.google.com) 접속", size=11, color=TEXT_PRIMARY),
                                        ft.Text("2. '+ 새로 만들기' -> '더보기' -> 'Google Apps Script' 생성", size=11, color=TEXT_PRIMARY),
                                        ft.Text("3. 기존 내용을 지우고 아래 스크립트 코드 전체 붙여넣기", size=11, color=TEXT_PRIMARY),
                                        ft.Text("4. 우측 상단 파란색 [배포] -> [새 배포] 클릭", size=11, color=TEXT_PRIMARY),
                                        ft.Text("   • 유형: [웹 앱(Web App)] 선택", size=11, color=ACCENT_BLUE),
                                        ft.Text("   • 다음 사용자 권한으로 실행: '나(내 이메일)'", size=11, color=TEXT_PRIMARY),
                                        ft.Text("   • 액세스 권한: '모든 사용자(Anyone)' 선택 (필수!)", size=11, color=PROFIT_GREEN, weight=ft.FontWeight.BOLD),
                                        ft.Text("5. [배포] 클릭 후 발급된 '웹 앱 URL' 복사 -> 앱에 붙여넣기 끝!", size=11, color=TEXT_PRIMARY),
                                    ],
                                    spacing=4
                                )
                            ),
                            ft.Container(height=4),
                            ft.Text("Google Apps Script 소스 코드 (길게 눌러 복사 가능):", size=11, color=TEXT_MUTED, weight=ft.FontWeight.BOLD),
                            ft.TextField(
                                value=script_code,
                                multiline=True,
                                min_lines=4,
                                max_lines=6,
                                read_only=True,
                                text_size=10,
                                border_color=BORDER_COLOR,
                                color=TEXT_PRIMARY,
                                content_padding=ft.Padding.all(8)
                            ),
                            ft.FilledButton(
                                content=ft.Row([
                                    ft.Icon(ft.Icons.CONTENT_COPY, size=15),
                                    ft.Text("스크립트 코드 전체 클립보드 복사", size=12, weight=ft.FontWeight.BOLD)
                                ], alignment=ft.MainAxisAlignment.CENTER, spacing=6),
                                style=ft.ButtonStyle(bgcolor=ACCENT_BLUE, color=ft.Colors.BLACK, shape=ft.RoundedRectangleBorder(radius=8)),
                                width=380,
                                on_click=lambda _: (copy_text_to_clipboard(self.page, script_code), show_toast(self.page, "Google Apps Script 코드가 복사되었습니다!"))
                            ),
                            ft.OutlinedButton(
                                content=ft.Row([
                                    ft.Icon(ft.Icons.OPEN_IN_BROWSER, size=15, color=ACCENT_BLUE),
                                    ft.Text("Google Apps Script 에디터 바로 열기", size=12, color=ACCENT_BLUE)
                                ], alignment=ft.MainAxisAlignment.CENTER, spacing=6),
                                style=ft.ButtonStyle(side=ft.BorderSide(1, ACCENT_BLUE), shape=ft.RoundedRectangleBorder(radius=8)),
                                width=380,
                                url="https://script.google.com/home/start"
                            )
                        ],
                        spacing=6,
                        scroll=ft.ScrollMode.AUTO
                    )
                ),
                actions=[
                    ft.TextButton("닫기", on_click=lambda _: self.page.pop_dialog())
                ],
                bgcolor=SURFACE_CARD,
                shape=ft.RoundedRectangleBorder(radius=14)
            )
            self.page.show_dialog(guide_dlg)

        cloud_sync_card = ft.Card(
            bgcolor=SURFACE_CARD,
            elevation=2,
            shape=ft.RoundedRectangleBorder(radius=14),
            content=ft.Container(
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.CLOUD_SYNC_ROUNDED, color=ACCENT_BLUE, size=20),
                                ft.Text("Google Drive 클라우드 실시간 동기화", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                            ],
                            spacing=6
                        ),
                        ft.Text(
                            "폰과 태블릿 등 여러 기기에서 동일한 구글 드라이브 폴더('JongJongTrader')를 통해 계좌 내역을 실시간으로 자동 동기화합니다.",
                            size=11,
                            color=TEXT_SECONDARY
                        ),
                        ft.Container(height=2),
                        sync_control_box,
                        ft.Container(height=2),
                        ft.Row(
                            controls=[
                                sync_url_field,
                                ft.FilledButton(
                                    "적용",
                                    style=ft.ButtonStyle(bgcolor=ACCENT_BLUE, color=ft.Colors.BLACK, shape=ft.RoundedRectangleBorder(radius=8)),
                                    on_click=handle_save_url
                                ),
                                ft.OutlinedButton(
                                    "테스트",
                                    style=ft.ButtonStyle(side=ft.BorderSide(1, ACCENT_BLUE), shape=ft.RoundedRectangleBorder(radius=8)),
                                    on_click=handle_test_conn
                                )
                            ],
                            spacing=6
                        ),
                        sync_status_text,
                        sync_loading,
                        ft.Container(height=2),
                        ft.Row(
                            controls=[
                                ft.FilledButton(
                                    content=ft.Row([ft.Icon(ft.Icons.SYNC, size=15), ft.Text("지금 즉시 동기화", size=12, weight=ft.FontWeight.BOLD)], spacing=4),
                                    style=ft.ButtonStyle(bgcolor=PROFIT_GREEN, color=ft.Colors.WHITE, shape=ft.RoundedRectangleBorder(radius=8), padding=ft.Padding.symmetric(vertical=10)),
                                    expand=True,
                                    on_click=handle_sync_now
                                ),
                                ft.OutlinedButton(
                                    content=ft.Row([ft.Icon(ft.Icons.CLOUD_UPLOAD_OUTLINED, size=15, color=TEXT_PRIMARY), ft.Text("드라이브로 올리기", size=11, color=TEXT_PRIMARY)], spacing=4),
                                    style=ft.ButtonStyle(side=ft.BorderSide(1, BORDER_COLOR), shape=ft.RoundedRectangleBorder(radius=8), padding=ft.Padding.symmetric(vertical=10)),
                                    expand=True,
                                    tooltip="현재 기기의 계좌를 구글 드라이브에 강제 덮어쓰기 백업",
                                    on_click=handle_force_upload
                                ),
                                ft.OutlinedButton(
                                    content=ft.Row([ft.Icon(ft.Icons.CLOUD_DOWNLOAD_OUTLINED, size=15, color=TEXT_PRIMARY), ft.Text("드라이브에서 받기", size=11, color=TEXT_PRIMARY)], spacing=4),
                                    style=ft.ButtonStyle(side=ft.BorderSide(1, BORDER_COLOR), shape=ft.RoundedRectangleBorder(radius=8), padding=ft.Padding.symmetric(vertical=10)),
                                    expand=True,
                                    tooltip="구글 드라이브의 계좌를 기기로 내려받아 적용 (기존 로컬 데이터는 자동 백업)",
                                    on_click=handle_force_download
                                ),
                            ],
                            spacing=6
                        ),
                        ft.OutlinedButton(
                            content=ft.Row([
                                ft.Icon(ft.Icons.HELP_OUTLINE, size=15, color=ACCENT_BLUE),
                                ft.Text("1분 만에 끝내는 구글 드라이브 연동 가이드 & 스크립트 복사", size=11.5, color=ACCENT_BLUE, weight=ft.FontWeight.W_500)
                            ], alignment=ft.MainAxisAlignment.CENTER, spacing=6),
                            style=ft.ButtonStyle(
                                side=ft.BorderSide(1, ACCENT_BLUE),
                                shape=ft.RoundedRectangleBorder(radius=8),
                                padding=ft.Padding.symmetric(vertical=9)
                            ),
                            width=380,
                            on_click=open_gas_guide_dialog
                        )
                    ],
                    spacing=8
                )
            )
        )

        # 3. 환율 설정 카드
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

        # 3. 버그 리포트 (Bug Report) 카드
        mailto_url = make_bug_report_mailto()

        bug_report_card = ft.Card(
            bgcolor=SURFACE_CARD,
            elevation=2,
            shape=ft.RoundedRectangleBorder(radius=14),
            content=ft.Container(
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.BUG_REPORT_OUTLINED, color=LOSS_RED, size=20),
                                ft.Text("버그 리포트 & 피드백 (Bug Report)", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                            ],
                            spacing=6
                        ),
                        ft.Text(
                            "앱 사용 중 오류가 발생했거나 개선 사항이 있으시면 언제든 메일을 보내주세요.\n"
                            "버튼을 누르면 스마트폰 메일 앱이 열리며 수신인과 양식이 자동 입력됩니다.",
                            size=11,
                            color=TEXT_SECONDARY
                        ),
                        ft.Container(height=4),
                        ft.FilledButton(
                            content=ft.Row([
                                ft.Icon(ft.Icons.EMAIL_OUTLINED, size=16),
                                ft.Text("Bug Report 메일 작성하기", size=13, weight=ft.FontWeight.BOLD)
                            ], alignment=ft.MainAxisAlignment.CENTER, spacing=6),
                            style=ft.ButtonStyle(
                                bgcolor=LOSS_RED,
                                color=ft.Colors.WHITE,
                                shape=ft.RoundedRectangleBorder(radius=8),
                                padding=ft.Padding.symmetric(vertical=12)
                            ),
                            width=380,
                            url=mailto_url,
                            on_click=lambda _: show_toast(self.page, "메일 작성 화면으로 이동합니다.")
                        ),
                        ft.Container(
                            padding=ft.Padding.symmetric(vertical=2, horizontal=4),
                            content=ft.Text(
                                "• 직접 전송 시 수신인: wprkfgur@hotmail.com (길게 눌러 복사 가능)",
                                size=11,
                                color=TEXT_MUTED,
                                selectable=True
                            )
                        )
                    ],
                    spacing=8
                )
            )
        )

        # 4. 로컬 시세 DB 캐시 상태 및 동기화 카드
        soxl_min, soxl_max = get_db_date_range('SOXL')
        tqqq_min, tqqq_max = get_db_date_range('TQQQ')
        soxl_status = f"{soxl_min} ~ {soxl_max}" if soxl_min else "미구축"
        tqqq_status = f"{tqqq_min} ~ {tqqq_max}" if tqqq_min else "미구축"

        db_sync_loading = ft.ProgressBar(visible=False, color=ACCENT_BLUE)
        db_status_text = ft.Text(f"• SOXL: {soxl_status}\n• TQQQ: {tqqq_status}", size=11, color=TEXT_MUTED)

        def handle_sync_market_db(e):
            db_sync_loading.visible = True
            db_sync_loading.update()
            try:
                today_s = datetime.now().strftime('%Y-%m-%d')
                fetch_market_data('SOXL', '2019-01-01', today_s)
                fetch_market_data('TQQQ', '2019-01-01', today_s)
                s_min, s_max = get_db_date_range('SOXL')
                t_min, t_max = get_db_date_range('TQQQ')
                db_status_text.value = f"• SOXL: {s_min} ~ {s_max}\n• TQQQ: {t_min} ~ {t_max}"
                db_status_text.update()
                show_toast(self.page, "SOXL, TQQQ 로컬 시세 DB가 최신으로 동기화되었습니다!")
            except Exception as ex:
                show_toast(self.page, f"시세 DB 동기화 실패: {ex}", is_error=True)
            finally:
                db_sync_loading.visible = False
                db_sync_loading.update()

        cache_card = ft.Card(
            bgcolor=SURFACE_CARD,
            elevation=2,
            shape=ft.RoundedRectangleBorder(radius=14),
            content=ft.Container(
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.STORAGE_ROUNDED, color=ACCENT_BLUE, size=20),
                                ft.Text("로컬 시세 DB 캐시 (초고속 로딩)", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                            ],
                            spacing=6
                        ),
                        ft.Text("SOXL, TQQQ 시세를 내부 DB에 영구 보존하여 백테스트와 계좌 조회를 네트워크 지연 없이 0.01초 만에 실행합니다.", size=11, color=TEXT_SECONDARY),
                        db_status_text,
                        db_sync_loading,
                        ft.Container(height=2),
                        ft.OutlinedButton(
                            content=ft.Row([
                                ft.Icon(ft.Icons.SYNC, size=15, color=ACCENT_BLUE),
                                ft.Text("최신 시세 수동 동기화", size=12, color=ACCENT_BLUE)
                            ], alignment=ft.MainAxisAlignment.CENTER, spacing=6),
                            style=ft.ButtonStyle(
                                side=ft.BorderSide(1, ACCENT_BLUE),
                                shape=ft.RoundedRectangleBorder(radius=8),
                                padding=ft.Padding.symmetric(vertical=10)
                            ),
                            width=380,
                            on_click=handle_sync_market_db
                        )
                    ],
                    spacing=8
                )
            )
        )

        # 5. 추후 확장 예정 설정 안내 카드
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
                        ft.Row([ft.Icon(ft.Icons.API, size=16, color=TEXT_MUTED), ft.Text("증권사 Open API 연동 및 자동 주문 전송", size=12, color=TEXT_MUTED)], spacing=8),
                        ft.Row([ft.Icon(ft.Icons.WIDGETS_OUTLINED, size=16, color=TEXT_MUTED), ft.Text("안드로이드 바탕화면 실시간 잔고 위젯", size=12, color=TEXT_MUTED)], spacing=8),
                    ],
                    spacing=6
                )
            )
        )

        # 5-2. 버전 확인 및 GitHub Releases 원클릭 자동 업데이트 카드
        update_cfg = get_update_config()
        saved_update_url = update_cfg.get("apk_update_url") or update_cfg.get("apk_drive_url") or DEFAULT_UPDATE_CHANNEL_URL
        if "drive.google.com" in str(saved_update_url):
            saved_update_url = DEFAULT_UPDATE_CHANNEL_URL

        update_url_field = ft.TextField(
            label="배포 GitHub 저장소 / 채널 링크",
            value=saved_update_url,
            hint_text=DEFAULT_UPDATE_CHANNEL_URL,
            label_style=ft.TextStyle(size=11, color=TEXT_SECONDARY),
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY,
            text_size=11,
            content_padding=ft.Padding.symmetric(horizontal=10, vertical=8),
            expand=True
        )

        update_status_text = ft.Text(
            f"현재 설치 버전: v{APP_VERSION} (최신 ARM64 배포판)",
            size=11,
            color=TEXT_MUTED
        )

        def handle_save_update_url(e):
            url_val = update_url_field.value.strip() or DEFAULT_UPDATE_CHANNEL_URL
            update_url_field.value = url_val
            cfg = get_update_config()
            cfg["apk_update_url"] = url_val
            save_update_config(cfg)
            show_toast(self.page, "업데이트 채널 링크가 저장되었습니다.")
            update_status_text.value = f"현재 버전: v{APP_VERSION} • GitHub 채널 연동 완료"
            self.page.update()

        def handle_reset_update_url(e):
            update_url_field.value = DEFAULT_UPDATE_CHANNEL_URL
            cfg = get_update_config()
            cfg["apk_update_url"] = DEFAULT_UPDATE_CHANNEL_URL
            save_update_config(cfg)
            show_toast(self.page, "기본 GitHub 배포 채널로 초기화되었습니다.")
            update_status_text.value = f"현재 버전: v{APP_VERSION} • GitHub 기본 채널 연결됨"
            self.page.update()

        def handle_check_and_update(e):
            url_val = update_url_field.value.strip() or DEFAULT_UPDATE_CHANNEL_URL
            download_fallback_url = parse_download_url(url_val)

            update_btn.disabled = True
            update_btn.content = ft.Row([
                ft.ProgressRing(width=16, height=16, stroke_width=2, color=ft.Colors.BLACK),
                ft.Text("최신 버전 확인 중...", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK)
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=8)
            update_btn.update()

            def _worker():
                info = check_remote_version_info(url_val)
                update_btn.disabled = False
                update_btn.content = ft.Row([
                    ft.Icon(ft.Icons.SYSTEM_UPDATE_ROUNDED, size=18, color=ft.Colors.BLACK),
                    ft.Text("최신 버전 확인 및 업데이트", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK)
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=8)
                update_btn.update()

                download_target_url = info.get("download_url") or download_fallback_url

                if info.get("status") == "success":
                    cfg = get_update_config()
                    cfg["apk_update_url"] = url_val
                    cfg["last_check_time"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    save_update_config(cfg)
                    update_status_text.value = f"설치 버전: v{APP_VERSION} • 최근 확인: {cfg['last_check_time']} (GitHub 연동)"
                    update_status_text.update()

                    notes_preview = info.get("release_notes", "")
                    notes_ctrl = None
                    if notes_preview:
                        clean_notes = notes_preview.replace("#", "").strip()[:180]
                        notes_ctrl = ft.Container(
                            padding=8,
                            bgcolor=ft.Colors.with_opacity(0.08, ACCENT_BLUE),
                            border_radius=6,
                            content=ft.Text(f"📋 업데이트 요약:\n{clean_notes}...", size=10, color=TEXT_SECONDARY)
                        )

                    if not info.get("is_newer"):
                        # 1. 이미 최신 버전인 경우 (불필요한 대용량 다운로드 방지)
                        dialog_items = [
                            ft.Container(
                                padding=12,
                                bgcolor=ft.Colors.with_opacity(0.12, PROFIT_GREEN),
                                border=ft.Border.all(1, ft.Colors.with_opacity(0.3, PROFIT_GREEN)),
                                border_radius=8,
                                content=ft.Text(
                                    f"현재 이미 가장 최신 버전(v{APP_VERSION})을 사용하고 계십니다!\n새 버전이 없어 불필요한 데이터 다운로드를 방지했습니다.",
                                    size=12,
                                    weight=ft.FontWeight.W_500,
                                    color=PROFIT_GREEN
                                )
                            ),
                            ft.Container(height=4),
                            ft.Row([ft.Text("• 현재 설치 버전:", size=11, color=TEXT_MUTED), ft.Text(f"v{APP_VERSION} (최신)", size=11, color=TEXT_PRIMARY, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Row([ft.Text("• 릴리즈 제목:", size=11, color=TEXT_MUTED), ft.Text(str(info.get('release_name', '최신 릴리즈'))[:22], size=11, color=TEXT_PRIMARY)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Row([ft.Text("• GitHub 배포일:", size=11, color=TEXT_MUTED), ft.Text(info.get('remote_date_str', APP_BUILD_DATE_STR), size=11, color=TEXT_PRIMARY)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Row([ft.Text("• 배포 파일 크기:", size=11, color=TEXT_MUTED), ft.Text(f"{info.get('remote_size_mb', 0)} MB", size=11, color=TEXT_PRIMARY)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ]
                        if notes_ctrl:
                            dialog_items.append(notes_ctrl)
                        dialog_items.extend([
                            ft.Divider(color=BORDER_COLOR, height=1),
                            ft.Text("※ 앱을 초기화하거나 재설치할 목적이 아니라면 다시 다운로드하실 필요가 없습니다.", size=10, color=TEXT_MUTED)
                        ])

                        dlg = ft.AlertDialog(
                            modal=True,
                            title=ft.Row([
                                ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=PROFIT_GREEN, size=22),
                                ft.Text("최신 버전 사용 중", size=15, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                            ], spacing=8),
                            content=ft.Container(
                                width=360,
                                content=ft.Column(
                                    controls=dialog_items,
                                    spacing=6,
                                    tight=True
                                )
                            ),
                            actions=[
                                ft.TextButton("확인 (닫기)", on_click=lambda _: self.page.pop_dialog()),
                                ft.TextButton(
                                    "강제 재다운로드",
                                    url=download_target_url,
                                    style=ft.ButtonStyle(color=TEXT_MUTED),
                                    on_click=lambda _: (self.page.pop_dialog(), trigger_apk_download(download_target_url, self.page), show_toast(self.page, "GitHub에서 최신 APK 다운로드를 시작합니다..."))
                                )
                            ],
                            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            bgcolor=SURFACE_CARD,
                            shape=ft.RoundedRectangleBorder(radius=14)
                        )
                        self.page.show_dialog(dlg)
                    else:
                        # 2. 새로운 최신 버전이 있는 경우 (다운로드 확인 팝업)
                        dialog_items = [
                            ft.Container(
                                padding=12,
                                bgcolor=ft.Colors.with_opacity(0.12, ACCENT_BLUE),
                                border=ft.Border.all(1, ft.Colors.with_opacity(0.3, ACCENT_BLUE)),
                                border_radius=8,
                                content=ft.Text(
                                    "GitHub Releases에 새로운 배포 버전이 등록되었습니다!\n지금 바로 업데이트하시겠습니까?",
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                    color=ACCENT_BLUE
                                )
                            ),
                            ft.Container(height=4),
                            ft.Row([ft.Text("• 현재 설치 버전:", size=11, color=TEXT_MUTED), ft.Text(f"v{APP_VERSION}", size=11, color=TEXT_SECONDARY)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Row([ft.Text("• 최신 배포 버전:", size=11, color=TEXT_MUTED), ft.Text(f"v{info.get('remote_version') or '최신'}", size=11, color=PROFIT_GREEN, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Row([ft.Text("• 릴리즈 제목:", size=11, color=TEXT_MUTED), ft.Text(str(info.get('release_name', '최신 릴리즈'))[:22], size=11, color=TEXT_PRIMARY)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Row([ft.Text("• 배포 일시:", size=11, color=TEXT_MUTED), ft.Text(info.get('remote_date_str', '최신'), size=11, color=TEXT_PRIMARY)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Row([ft.Text("• 파일 크기:", size=11, color=TEXT_MUTED), ft.Text(f"{info.get('remote_size_mb', 0)} MB", size=11, color=TEXT_PRIMARY)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ]
                        if notes_ctrl:
                            dialog_items.append(notes_ctrl)
                        dialog_items.extend([
                            ft.Divider(color=BORDER_COLOR, height=1),
                            ft.Text("※ 다운로드 완료 후 상단 알림을 터치하면 기존 계좌 데이터를 유지한 채 바로 업데이트됩니다.", size=10, color=TEXT_MUTED)
                        ])

                        dlg = ft.AlertDialog(
                            modal=True,
                            title=ft.Row([
                                ft.Icon(ft.Icons.NEW_RELEASES_ROUNDED, color=ACCENT_BLUE, size=22),
                                ft.Text("새로운 업데이트 발견! 🚀", size=15, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                            ], spacing=8),
                            content=ft.Container(
                                width=360,
                                content=ft.Column(
                                    controls=dialog_items,
                                    spacing=6,
                                    tight=True
                                )
                            ),
                            actions=[
                                ft.TextButton("나중에", on_click=lambda _: self.page.pop_dialog()),
                                ft.FilledButton(
                                    "🚀 지금 업데이트 다운로드",
                                    url=download_target_url,
                                    style=ft.ButtonStyle(bgcolor=ACCENT_BLUE, color=ft.Colors.BLACK),
                                    on_click=lambda _: (self.page.pop_dialog(), trigger_apk_download(download_target_url, self.page), show_toast(self.page, "GitHub에서 최신 APK 다운로드를 시작합니다..."))
                                )
                            ],
                            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            bgcolor=SURFACE_CARD,
                            shape=ft.RoundedRectangleBorder(radius=14)
                        )
                        self.page.show_dialog(dlg)
                elif info.get("status") == "no_release":
                    # 3. 릴리즈가 등록되지 않은 경우
                    dlg = ft.AlertDialog(
                        modal=True,
                        title=ft.Row([
                            ft.Icon(ft.Icons.INFO_OUTLINE_ROUNDED, color=ACCENT_BLUE, size=22),
                            ft.Text("GitHub 릴리즈 미등록", size=15, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                        ], spacing=8),
                        content=ft.Container(
                            width=360,
                            content=ft.Column(
                                controls=[
                                    ft.Text(info.get("message", "GitHub 저장소에 등록된 릴리즈가 없습니다."), size=12, color=TEXT_SECONDARY),
                                    ft.Container(height=4),
                                    ft.Text(f"저장소: {info.get('download_url')}", size=11, color=TEXT_MUTED)
                                ],
                                spacing=6,
                                tight=True
                            )
                        ),
                        actions=[
                            ft.TextButton("닫기", on_click=lambda _: self.page.pop_dialog()),
                            ft.FilledButton(
                                "저장소 열기",
                                url=info.get('download_url', DEFAULT_RELEASES_WEB_URL),
                                style=ft.ButtonStyle(bgcolor=ACCENT_BLUE, color=ft.Colors.BLACK),
                                on_click=lambda _: (self.page.pop_dialog(), trigger_apk_download(info.get('download_url', DEFAULT_RELEASES_WEB_URL), self.page))
                            )
                        ],
                        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        bgcolor=SURFACE_CARD,
                        shape=ft.RoundedRectangleBorder(radius=14)
                    )
                    self.page.show_dialog(dlg)
                else:
                    # 4. 네트워크 에러 등으로 확인 실패한 경우
                    dlg = ft.AlertDialog(
                        modal=True,
                        title=ft.Row([
                            ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=RESERVE_AMBER, size=22),
                            ft.Text("버전 확인 실패", size=15, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                        ], spacing=8),
                        content=ft.Container(
                            width=360,
                            content=ft.Column(
                                controls=[
                                    ft.Text(f"GitHub 서버 연결에 실패했습니다.\n사유: {info.get('error', '네트워크 오류')}", size=12, color=TEXT_SECONDARY),
                                    ft.Container(height=4),
                                    ft.Text("직접 다운로드를 시도하시겠습니까?", size=11, color=TEXT_MUTED)
                                ],
                                spacing=6,
                                tight=True
                            )
                        ),
                        actions=[
                            ft.TextButton("닫기", on_click=lambda _: self.page.pop_dialog()),
                            ft.FilledButton(
                                "직접 다운로드 시도",
                                url=download_target_url,
                                style=ft.ButtonStyle(bgcolor=ACCENT_BLUE, color=ft.Colors.BLACK),
                                on_click=lambda _: (self.page.pop_dialog(), trigger_apk_download(download_target_url, self.page), show_toast(self.page, "최신 APK 다운로드를 시작합니다..."))
                            )
                        ],
                        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        bgcolor=SURFACE_CARD,
                        shape=ft.RoundedRectangleBorder(radius=14)
                    )
                    self.page.show_dialog(dlg)

            threading.Thread(target=_worker, daemon=True).start()

        update_btn = ft.FilledButton(
            content=ft.Row([
                ft.Icon(ft.Icons.SYSTEM_UPDATE_ROUNDED, size=18, color=ft.Colors.BLACK),
                ft.Text("최신 버전 확인 및 업데이트", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK)
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=8),
            style=ft.ButtonStyle(
                bgcolor=ACCENT_BLUE,
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.Padding.symmetric(vertical=13, horizontal=14)
            ),
            expand=True,
            on_click=handle_check_and_update
        )

        app_update_card = ft.Card(
            bgcolor=SURFACE_CARD,
            elevation=2,
            shape=ft.RoundedRectangleBorder(radius=14),
            content=ft.Container(
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Row([
                                    ft.Icon(ft.Icons.SYSTEM_UPDATE_ALT, color=ACCENT_BLUE, size=20),
                                    ft.Text("버전 관리 및 GitHub Releases 자동 업데이트", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                                ], spacing=6),
                                ft.Container(
                                    content=ft.Text(f"v{APP_VERSION}", size=11, color=PROFIT_GREEN, weight=ft.FontWeight.BOLD),
                                    bgcolor=ft.Colors.with_opacity(0.15, PROFIT_GREEN),
                                    padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                                    border_radius=6
                                )
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        # 공식 GitHub Releases 연동 상태 뱃지
                        ft.Container(
                            bgcolor=ft.Colors.with_opacity(0.1, PROFIT_GREEN),
                            border=ft.Border.all(1, ft.Colors.with_opacity(0.3, PROFIT_GREEN)),
                            border_radius=8,
                            padding=ft.Padding.symmetric(horizontal=10, vertical=8),
                            content=ft.Row([
                                ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, size=16, color=PROFIT_GREEN),
                                ft.Text(
                                    "GitHub Releases 공식 배포 채널 연결됨 (jj_invest)",
                                    size=11,
                                    weight=ft.FontWeight.BOLD,
                                    color=PROFIT_GREEN,
                                    expand=True
                                )
                            ], spacing=8)
                        ),
                        ft.Text(
                            "버튼을 누르면 먼저 GitHub Releases의 최신 배포본과 현재 버전을 비교합니다. 이미 최신 버전이면 다운로드를 방지하고 팝업으로 안내하며, 새 릴리즈가 등록되었을 때만 안전하게 다운로드합니다.",
                            size=11,
                            color=TEXT_SECONDARY
                        ),
                        ft.Container(height=2),
                        # 원클릭 자동 업데이트 실행 버튼
                        update_btn,
                        update_status_text,
                        ft.Divider(color=BORDER_COLOR, height=1),
                        # 고급 설정: GitHub 링크 확인 및 수동 변경
                        ft.ExpansionTile(
                            title=ft.Text("배포 채널(GitHub 저장소) 확인 및 수동 변경 (선택사항)", size=11, color=TEXT_MUTED),
                            dense=True,
                            controls_padding=ft.Padding.only(top=4, bottom=6),
                            controls=[
                                ft.Row(
                                    controls=[
                                        update_url_field,
                                        ft.IconButton(
                                            icon=ft.Icons.SAVE,
                                            icon_color=ACCENT_BLUE,
                                            tooltip="링크 저장",
                                            on_click=handle_save_update_url
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.RESTART_ALT,
                                            icon_color=TEXT_MUTED,
                                            tooltip="기본 링크로 초기화",
                                            on_click=handle_reset_update_url
                                        )
                                    ],
                                    spacing=2
                                ),
                                ft.Text(
                                    "※ GitHub Releases(wprkfgur-dotcom/jj_invest/releases)에 새 APK가 등록되면 앱에서 즉시 감지하여 업데이트할 수 있습니다.",
                                    size=10,
                                    color=TEXT_MUTED
                                )
                            ]
                        )
                    ],
                    spacing=8
                )
            )
        )


        # 6. 앱 정보 및 개발자 크레딧 카드
        app_info_card = ft.Container(
            padding=16,
            bgcolor=SURFACE_CARD,
            border=ft.Border.all(1, BORDER_COLOR),
            border_radius=12,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.INFO_OUTLINE, size=18, color=ACCENT_BLUE),
                            ft.Text(f"종종 투자 모바일 (JongJong Mobile) v{APP_VERSION}", size=13, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        ],
                        spacing=8
                    ),
                    ft.Divider(color=BORDER_COLOR, height=1),
                    # 프로젝트 크레딧 (역할별 시각적 위계 적용)
                    ft.Container(
                        bgcolor=ft.Colors.with_opacity(0.12, ACCENT_BLUE),
                        border=ft.Border.all(1, ft.Colors.with_opacity(0.35, ACCENT_BLUE)),
                        border_radius=8,
                        padding=ft.Padding.symmetric(horizontal=10, vertical=8),
                        content=ft.Row(
                            controls=[
                                ft.Row([
                                    ft.Icon(ft.Icons.CODE_ROUNDED, size=18, color=ACCENT_BLUE),
                                    ft.Text("App Development:", size=13, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                                ], spacing=6),
                                ft.Container(
                                    content=ft.Text("이혁", size=13.5, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK),
                                    bgcolor=ACCENT_BLUE,
                                    padding=ft.Padding.symmetric(horizontal=9, vertical=3),
                                    border_radius=6
                                )
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        )
                    ),
                    ft.Container(
                        padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                        content=ft.Row(
                            controls=[
                                ft.Row([
                                    ft.Icon(ft.Icons.ANALYTICS_OUTLINED, size=15, color=TEXT_SECONDARY),
                                    ft.Text("Logic Design:", size=12, weight=ft.FontWeight.W_600, color=TEXT_SECONDARY),
                                ], spacing=6),
                                ft.Text("최용민", size=12, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        )
                    ),
                    ft.Container(
                        padding=ft.Padding.symmetric(horizontal=8, vertical=1),
                        content=ft.Row(
                            controls=[
                                ft.Row([
                                    ft.Icon(ft.Icons.COFFEE_ROUNDED, size=13, color=TEXT_MUTED),
                                    ft.Text("Do Nothing:", size=11, color=TEXT_MUTED),
                                ], spacing=6),
                                ft.Text("이종필, 윤석배", size=11, color=TEXT_MUTED)
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        )
                    ),
                    ft.Divider(color=BORDER_COLOR, height=1),
                    ft.Text("엔진: Python 3.12 & Flutter (Flet 1.0.2) • 데이터: data/accounts.json, data/market_data.db", size=10, color=TEXT_MUTED),
                ],
                spacing=8
            )
        )

        return ft.ListView(
            controls=[
                export_card,
                ft.Container(height=6),
                cloud_sync_card,
                ft.Container(height=6),
                rate_card,
                ft.Container(height=6),
                cache_card,
                ft.Container(height=6),
                bug_report_card,
                ft.Container(height=6),
                app_update_card,
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
        ticker_f = ft.TextField(label="종목 티커", value="SOXL", border_color=BORDER_COLOR, focused_border_color=ACCENT_BLUE, color=TEXT_PRIMARY, expand=True)
        strat_f = ft.Dropdown(
            label="전략 선택",
            value="종종이 기본전략",
            options=[ft.dropdown.Option("종종이 기본전략"), ft.dropdown.Option("무한매수법 v4.0"), ft.dropdown.Option("VR 5.0 (밸류리밸런싱)")],
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY
        )
        date_f = ft.TextField(
            label="시작일 (YYYY-MM-DD)",
            value=today_str,
            hint_text="오늘날짜 (달력선택 가능)",
            read_only=True,
            on_click=lambda _: self.open_date_picker_for_field(date_f),
            suffix=ft.IconButton(
                icon=ft.Icons.CALENDAR_MONTH,
                icon_color=ACCENT_BLUE,
                tooltip="달력에서 시작일 선택",
                on_click=lambda _: self.open_date_picker_for_field(date_f)
            ),
            border_color=BORDER_COLOR,
            focused_border_color=ACCENT_BLUE,
            color=TEXT_PRIMARY,
            expand=True
        )
        seed_f = ft.TextField(label="초기 시드 ($)", value="100000", keyboard_type=ft.KeyboardType.NUMBER, border_color=BORDER_COLOR, focused_border_color=ACCENT_BLUE, color=TEXT_PRIMARY, expand=True)
        reserve_f = ft.TextField(label="위기준비금(%)", value="5", keyboard_type=ft.KeyboardType.NUMBER, border_color=BORDER_COLOR, focused_border_color=RESERVE_AMBER, color=TEXT_PRIMARY, expand=True)
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

            self.am.add_account(
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
                width=350,
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
                content=ft.Column(
                    controls=[
                        name_f, seed_f, ft.Container(height=2), slider_text, slider, memo_f,
                        ft.Container(height=4),
                        ft.Row([
                            ft.Icon(ft.Icons.CODE_ROUNDED, size=14, color=ACCENT_BLUE),
                            ft.Text("App Dev: 이혁", size=11, color=ACCENT_BLUE, weight=ft.FontWeight.BOLD)
                        ], alignment=ft.MainAxisAlignment.END, spacing=4)
                    ],
                    spacing=8,
                    tight=True
                )
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
        거래 슬롯 기록을 직접 수정하는 대화상자를 엽니다 (4대 섹션: 시장/매수/매도/손익).
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
        cur_mode = str(target.get('Mode', 'Normal'))
        cur_bq = int(target.get('BuyQty', target.get('R', 0)))
        cur_u = float(target.get('U', 0.0)) if target.get('U') is not None else 0.0
        cur_wd = str(target.get('W', '')) if (target.get('Sold') and target.get('W')) else ""
        cur_sp = float(target.get('X', 0.0)) if (target.get('Sold') and target.get('X') is not None) else 0.0
        cur_profit = float(target.get('Profit', 0.0)) if (target.get('Sold') and target.get('Profit') is not None) else 0.0

        date_f = ft.TextField(
            label="1. 거래일자 (매수일: YYYY-MM-DD)",
            value=cur_d,
            border_color=BORDER_COLOR,
            focused_border_color="#4ADE80",
            color=TEXT_PRIMARY,
            text_size=12,
            expand=True
        )
        close_f = ft.TextField(
            label="종가 ($)",
            value=f"{cur_close:.2f}",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=BORDER_COLOR,
            focused_border_color="#4ADE80",
            color=TEXT_PRIMARY,
            text_size=12,
            expand=True
        )
        mode_dd = ft.Dropdown(
            label="시장 모드",
            value=cur_mode if cur_mode in ["Normal", "Safe", "Riskoff"] else "Normal",
            options=[ft.dropdown.Option("Normal"), ft.dropdown.Option("Safe"), ft.dropdown.Option("Riskoff")],
            border_color=BORDER_COLOR,
            focused_border_color="#4ADE80",
            color=TEXT_PRIMARY,
            text_size=12,
            expand=True
        )

        buy_q_f = ft.TextField(
            label="2. 매수량 (주)",
            value=str(cur_bq),
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=BORDER_COLOR,
            focused_border_color="#F472B6",
            color=TEXT_PRIMARY,
            text_size=12,
            expand=True
        )
        target_u_f = ft.TextField(
            label="익절 목표가 ($)",
            value=f"{cur_u:.2f}" if cur_u > 0 else "",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=BORDER_COLOR,
            focused_border_color="#F472B6",
            color=TEXT_PRIMARY,
            text_size=12,
            expand=True
        )

        sell_d_f = ft.TextField(
            label="3. 매도일 (미매도 시 빈칸)",
            value=cur_wd,
            border_color=BORDER_COLOR,
            focused_border_color="#60A5FA",
            color=TEXT_PRIMARY,
            text_size=12,
            expand=True
        )
        sell_p_f = ft.TextField(
            label="매도가 ($)",
            value=f"{cur_sp:.2f}" if cur_sp > 0 else "",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=BORDER_COLOR,
            focused_border_color="#60A5FA",
            color=TEXT_PRIMARY,
            text_size=12,
            expand=True
        )

        profit_f = ft.TextField(
            label="4. 실현 손익 ($)",
            value=f"{cur_profit:.2f}" if cur_profit != 0.0 else "",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=BORDER_COLOR,
            focused_border_color="#FBBF24",
            color=TEXT_PRIMARY,
            text_size=12,
            expand=True
        )

        def handle_save_edit(e):
            try:
                n_date = date_f.value.strip()
                n_close = float(close_f.value.strip())
                n_mode = mode_dd.value or "Normal"
                n_bq = int(buy_q_f.value.strip())
                n_u = float(target_u_f.value.strip()) if target_u_f.value.strip() else None
                n_sell_d = sell_d_f.value.strip()
                n_sell_p = float(sell_p_f.value.strip()) if sell_p_f.value.strip() else None
                n_profit = float(profit_f.value.strip()) if profit_f.value.strip() else None

                target['Date'] = n_date
                target['Close'] = n_close
                target['Mode'] = n_mode
                target['BuyQty'] = n_bq
                target['R'] = n_bq
                if n_u is not None:
                    target['U'] = n_u

                if n_sell_d and n_sell_p is not None:
                    target['Sold'] = True
                    target['W'] = n_sell_d
                    target['X'] = n_sell_p
                    if n_profit is not None:
                        target['Profit'] = n_profit
                    else:
                        bp = float(target.get('BuyPrice', n_close))
                        target['Profit'] = round((n_sell_p - bp) * n_bq, 2)
                    bp = float(target.get('BuyPrice', n_close))
                    target['ProfitRate'] = round((n_sell_p / bp - 1.0) * 100.0, 2) if bp > 0 else 0.0
                else:
                    target['Sold'] = False
                    target['W'] = None
                    target['X'] = None
                    target['Profit'] = None
                    target['ProfitRate'] = None

                # Recompute Asset
                target_hold = int(target.get('Hold', 0))
                target_cash = float(target.get('Cash', 0.0))
                target['Asset'] = round(target_cash + n_close * target_hold, 2)

                self.am.save_accounts(self.accounts)
                self.page.pop_dialog()
                show_toast(self.page, f"{n_date} 거래 슬롯 정보가 수정되었습니다.")
                self.reload_data()
            except Exception as ex:
                show_toast(self.page, f"수정 저장 오류: {ex}", is_error=True)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.EDIT_NOTE, color=ACCENT_BLUE),
                ft.Text(f"거래 슬롯 수정 ({format_kr_date(cur_d)})", weight=ft.FontWeight.BOLD, size=15, color=TEXT_PRIMARY)
            ], spacing=6),
            content=ft.Container(
                width=360,
                content=ft.Column(
                    controls=[
                        ft.Text("🌿 1. 시장 정보", size=11, weight=ft.FontWeight.BOLD, color="#4ADE80"),
                        ft.Row([date_f, mode_dd], spacing=6),
                        close_f,
                        ft.Container(height=2),
                        ft.Text("🌸 2. 매수 정보", size=11, weight=ft.FontWeight.BOLD, color="#F472B6"),
                        ft.Row([buy_q_f, target_u_f], spacing=6),
                        ft.Container(height=2),
                        ft.Text("🌊 3. 매도 정보", size=11, weight=ft.FontWeight.BOLD, color="#60A5FA"),
                        ft.Row([sell_d_f, sell_p_f], spacing=6),
                        ft.Container(height=2),
                        ft.Text("🌾 4. 손익 정보", size=11, weight=ft.FontWeight.BOLD, color="#FBBF24"),
                        profit_f,
                        ft.Text("💡 한 행은 하나의 슬롯입니다. 매도일/매도가 입력 시 청산 처리됩니다.", size=10, color=TEXT_MUTED)
                    ],
                    spacing=6,
                    tight=True,
                    scroll=ft.ScrollMode.AUTO
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
    if sys.platform == "win32":
        page.title = "종종이 & 무한매수 트레이더 (Windows Debug)"
        page.window.width = 440
        page.window.height = 890
        page.window.resizable = True
    app = MobileTradingApp(page)
    page.add(app.content_container)


if __name__ == "__main__":
    ft.run(main)
