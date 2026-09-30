"""
GUI 테마 및 스타일 설정 모듈
현대적이고 직관적인 Dark & Clean Pro-Trader 테마를 제공합니다.
"""
import tkinter as tk
from tkinter import ttk

# 테마 색상 팔레트
COLORS = {
    'bg_dark': '#1e1e2e',          # 기본 최상위 배경
    'bg_card': '#27273a',          # 카드/패널 배경
    'bg_card_alt': '#313244',      # 서브 패널 배경
    'bg_input': '#181825',         # 입력창/테이블 배경
    'border': '#45475a',           # 테두리 선
    'border_focus': '#89b4fa',     # 포커스 테두리

    'text_primary': '#cdd6f4',     # 기본 밝은 텍스트
    'text_secondary': '#a6adc8',   # 보조 텍스트
    'text_muted': '#6c7086',       # 비활성/설명 텍스트
    'text_white': '#ffffff',

    'accent_blue': '#89b4fa',      # 메인 블루 포인트
    'accent_cyan': '#89dceb',      # 사이언
    'accent_green': '#a6e3a1',     # 상승/매수/수익 (그린)
    'accent_red': '#f38ba8',       # 하락/매도/손실 (레드)
    'accent_yellow': '#f9e2af',    # 경고/Safe 모드 (옐로우)
    'accent_purple': '#cba6f7',    # AK 위기준비금 / 특별 표시
    'accent_orange': '#fab387',    # 리스크오프 모드

    'btn_primary': '#3b82f6',
    'btn_primary_hover': '#2563eb',
    'btn_success': '#10b981',
    'btn_success_hover': '#059669',
    'btn_secondary': '#4b5563',
    'btn_secondary_hover': '#374151'
}

FONTS = {
    'title': ('Malgun Gothic', 16, 'bold'),
    'subtitle': ('Malgun Gothic', 12, 'bold'),
    'heading': ('Malgun Gothic', 11, 'bold'),
    'body': ('Malgun Gothic', 10),
    'body_bold': ('Malgun Gothic', 10, 'bold'),
    'caption': ('Malgun Gothic', 9),
    'mono': ('Consolas', 10),
    'mono_bold': ('Consolas', 10, 'bold'),
    'kpi_num': ('Segoe UI', 18, 'bold'),
    'kpi_label': ('Malgun Gothic', 9)
}


def apply_theme(root: tk.Tk):
    """
    Tkinter 루트 윈도우 및 ttk 위젯 스타일에 현대적인 다크 테마를 적용합니다.
    """
    root.configure(bg=COLORS['bg_dark'])
    style = ttk.Style()
    try:
        style.theme_use('clam')
    except Exception:
        pass

    # 일반 프레임
    style.configure('TFrame', background=COLORS['bg_dark'])
    style.configure('Card.TFrame', background=COLORS['bg_card'])
    style.configure('CardAlt.TFrame', background=COLORS['bg_card_alt'])

    # 라벨
    style.configure('TLabel', background=COLORS['bg_dark'], foreground=COLORS['text_primary'], font=FONTS['body'])
    style.configure('Card.TLabel', background=COLORS['bg_card'], foreground=COLORS['text_primary'], font=FONTS['body'])
    style.configure('CardMuted.TLabel', background=COLORS['bg_card'], foreground=COLORS['text_muted'], font=FONTS['caption'])
    style.configure('Title.TLabel', background=COLORS['bg_dark'], foreground=COLORS['accent_blue'], font=FONTS['title'])
    style.configure('CardTitle.TLabel', background=COLORS['bg_card'], foreground=COLORS['accent_cyan'], font=FONTS['subtitle'])
    style.configure('KPIVal.TLabel', background=COLORS['bg_card'], foreground=COLORS['text_white'], font=FONTS['kpi_num'])
    style.configure('KPILbl.TLabel', background=COLORS['bg_card'], foreground=COLORS['text_secondary'], font=FONTS['kpi_label'])

    # 노트북 (탭)
    style.configure('TNotebook', background=COLORS['bg_dark'], tabmargins=[4, 4, 4, 0])
    style.configure('TNotebook.Tab',
                    background=COLORS['bg_card'],
                    foreground=COLORS['text_secondary'],
                    padding=[16, 8],
                    font=FONTS['body_bold'],
                    borderwidth=0)
    style.map('TNotebook.Tab',
              background=[('selected', COLORS['btn_primary']), ('active', COLORS['bg_card_alt'])],
              foreground=[('selected', COLORS['text_white']), ('active', COLORS['text_white'])])

    # 라벨프레임
    style.configure('TLabelframe', background=COLORS['bg_card'], foreground=COLORS['accent_blue'], bordercolor=COLORS['border'])
    style.configure('TLabelframe.Label', background=COLORS['bg_card'], foreground=COLORS['accent_cyan'], font=FONTS['heading'])

    # 버튼
    style.configure('TButton',
                    background=COLORS['btn_secondary'],
                    foreground=COLORS['text_white'],
                    font=FONTS['body_bold'],
                    padding=[12, 6],
                    borderwidth=0)
    style.map('TButton',
              background=[('active', COLORS['btn_secondary_hover']), ('disabled', COLORS['border'])],
              foreground=[('disabled', COLORS['text_muted'])])

    style.configure('Primary.TButton',
                    background=COLORS['btn_primary'],
                    foreground=COLORS['text_white'],
                    font=FONTS['body_bold'],
                    padding=[14, 7],
                    borderwidth=0)
    style.map('Primary.TButton',
              background=[('active', COLORS['btn_primary_hover']), ('disabled', COLORS['border'])])

    style.configure('Success.TButton',
                    background=COLORS['btn_success'],
                    foreground=COLORS['text_white'],
                    font=FONTS['body_bold'],
                    padding=[14, 7],
                    borderwidth=0)
    style.map('Success.TButton',
              background=[('active', COLORS['btn_success_hover'])])

    # 콤보박스 & 엔트리
    style.configure('TCombobox',
                    fieldbackground=COLORS['bg_input'],
                    background=COLORS['bg_card'],
                    foreground=COLORS['text_primary'],
                    font=FONTS['body'],
                    bordercolor=COLORS['border'])
    style.map('TCombobox',
              fieldbackground=[('readonly', COLORS['bg_input'])],
              selectbackground=[('readonly', COLORS['btn_primary'])],
              selectforeground=[('readonly', COLORS['text_white'])])

    style.configure('TEntry',
                    fieldbackground=COLORS['bg_input'],
                    foreground=COLORS['text_primary'],
                    font=FONTS['body'],
                    bordercolor=COLORS['border'])

    # 트리뷰 (표)
    style.configure('Treeview',
                    background=COLORS['bg_input'],
                    foreground=COLORS['text_primary'],
                    fieldbackground=COLORS['bg_input'],
                    font=FONTS['body'],
                    rowheight=26,
                    borderwidth=0)
    style.map('Treeview',
              background=[('selected', COLORS['btn_primary'])],
              foreground=[('selected', COLORS['text_white'])])

    style.configure('Treeview.Heading',
                    background=COLORS['bg_card_alt'],
                    foreground=COLORS['text_white'],
                    font=FONTS['body_bold'],
                    padding=[6, 6],
                    borderwidth=1,
                    relief='flat')
    style.map('Treeview.Heading',
              background=[('active', COLORS['btn_secondary'])])

    # 스크롤바
    style.configure('Vertical.TScrollbar',
                    background=COLORS['bg_card'],
                    troughcolor=COLORS['bg_input'],
                    borderwidth=0,
                    arrowsize=12)
    style.configure('Horizontal.TScrollbar',
                    background=COLORS['bg_card'],
                    troughcolor=COLORS['bg_input'],
                    borderwidth=0,
                    arrowsize=12)
