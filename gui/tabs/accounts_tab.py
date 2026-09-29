"""
계좌 관리 및 실시간 상세 대시보드 탭 (Accounts Tab)
다중 계좌 생성(+ 버튼), 계좌별 시작일/초기시드/현재가/자산 조회,
세금 납부를 위한 자산 인출 및 추가 입금, 당일 LOC 주문표, 매매 기록을 종합 제공합니다.
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from datetime import datetime
import pandas as pd

from gui.theme import COLORS, FONTS
from gui.account_manager import AccountManager
from gui.dialogs.trade_entry_dialog import RecordCloseDialog, EditTradeLogDialog


class AddAccountDialog(tk.Toplevel):
    """
    새 계좌 생성을 위한 모달 대화상자
    """

    def __init__(self, parent, on_success_callback):
        super().__init__(parent)
        self.title("➕ 새 투자 계좌 추가")
        self.geometry("520x560")
        self.resizable(False, False)
        self.configure(bg=COLORS['bg_card'])
        self.transient(parent)
        self.grab_set()

        self.mgr = AccountManager()
        self.imported_data = None
        self.on_success_callback = on_success_callback
        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text="새 투자 계좌 정보 등록", style='Title.TLabel', font=FONTS['subtitle']).pack(anchor='w', padx=20, pady=(16, 10))

        # 0. 기존 CSV 이어하기 섹션
        import_card = ttk.LabelFrame(self, text=" 📂 기존 매매 기록 이어하기 (CSV) ", padding=10)
        import_card.pack(fill='x', padx=20, pady=(0, 10))

        btn_import = ttk.Button(import_card, text="📂 기존 CSV 읽어오기", style='Primary.TButton', command=self._on_import_csv)
        btn_import.pack(side='left', padx=(0, 10))

        self.lbl_import_status = ttk.Label(
            import_card, 
            text="기존 매매 일지 CSV 파일이 있다면 불러와서 과거 내역을 그대로 이어가세요.", 
            foreground=COLORS['text_muted'], 
            font=FONTS['caption'], 
            wraplength=310
        )
        self.lbl_import_status.pack(side='left', fill='x', expand=True)

        form = ttk.Frame(self, style='Card.TFrame')
        form.pack(fill='both', expand=True, padx=20)

        # 1. 계좌명
        ttk.Label(form, text="계좌 별칭 (Name):", style='Card.TLabel', font=FONTS['body_bold']).grid(row=0, column=0, sticky='w', pady=6)
        self.entry_name = ttk.Entry(form, width=30)
        self.entry_name.insert(0, "SOXL 종종이 1호")
        self.entry_name.grid(row=0, column=1, sticky='w', pady=6)

        # 2. 투자 전략
        ttk.Label(form, text="투자 전략 (Strategy):", style='Card.TLabel', font=FONTS['body_bold']).grid(row=1, column=0, sticky='w', pady=6)
        self.combo_strat = ttk.Combobox(form, values=['종종이 기본전략', '무한매수법 v4.0'], state='readonly', width=28)
        self.combo_strat.set('종종이 기본전략')
        self.combo_strat.grid(row=1, column=1, sticky='w', pady=6)

        # 3. 대상 종목
        ttk.Label(form, text="대상 종목 (Ticker):", style='Card.TLabel', font=FONTS['body_bold']).grid(row=2, column=0, sticky='w', pady=6)
        self.combo_ticker = ttk.Combobox(form, values=['SOXL', 'TQQQ'], state='readonly', width=28)
        self.combo_ticker.set('SOXL')
        self.combo_ticker.grid(row=2, column=1, sticky='w', pady=6)

        # 4. 시작 일자
        ttk.Label(form, text="운용 시작일 (YYYY-MM-DD):", style='Card.TLabel', font=FONTS['body_bold']).grid(row=3, column=0, sticky='w', pady=6)
        self.entry_start = ttk.Entry(form, width=30)
        today_str = datetime.now().strftime('%Y-%m-%d')
        self.entry_start.insert(0, today_str)
        self.entry_start.grid(row=3, column=1, sticky='w', pady=6)

        # 5. 초기 시드 ($)
        ttk.Label(form, text="초기 투자 시드 ($):", style='Card.TLabel', font=FONTS['body_bold']).grid(row=4, column=0, sticky='w', pady=6)
        self.entry_seed = ttk.Entry(form, width=30)
        self.entry_seed.insert(0, "100000")
        self.entry_seed.grid(row=4, column=1, sticky='w', pady=6)

        # 6. 위기준비금 비율 (%)
        ttk.Label(form, text="위기준비금 비율 (%):", style='Card.TLabel', font=FONTS['body_bold']).grid(row=5, column=0, sticky='w', pady=6)
        self.combo_reserve = ttk.Combobox(form, values=['0%', '5%', '10%', '15%', '20%'], width=28)
        self.combo_reserve.set('5%')
        self.combo_reserve.grid(row=5, column=1, sticky='w', pady=6)

        # 7. 메모
        ttk.Label(form, text="계좌 설명 / 메모:", style='Card.TLabel', font=FONTS['body_bold']).grid(row=6, column=0, sticky='w', pady=6)
        self.entry_memo = ttk.Entry(form, width=30)
        self.entry_memo.insert(0, "메인 계좌 운용")
        self.entry_memo.grid(row=6, column=1, sticky='w', pady=6)

        # 버튼 박스
        btn_box = ttk.Frame(self, style='Card.TFrame')
        btn_box.pack(fill='x', padx=20, pady=(16, 20))

        btn_cancel = ttk.Button(btn_box, text="취소", command=self.destroy)
        btn_cancel.pack(side='right', padx=(8, 0))

        btn_save = ttk.Button(btn_box, text="계좌 생성 완료", style='Success.TButton', command=self._save_account)
        btn_save.pack(side='right')

    def _on_import_csv(self):
        file_path = filedialog.askopenfilename(
            parent=self,
            title="기존 매매 기록 CSV 파일 선택",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if not file_path:
            return

        try:
            parsed = self.mgr.parse_trade_records_csv(file_path)
        except Exception as e:
            messagebox.showerror("CSV 로드 실패", f"CSV 파일을 분석하는 중 오류가 발생했습니다:\n{e}", parent=self)
            return

        self.imported_data = parsed

        # 폼 입력값 자동 완성
        self.entry_name.delete(0, 'end')
        self.entry_name.insert(0, parsed['account_name'])

        if parsed['strategy'] in self.combo_strat['values']:
            self.combo_strat.set(parsed['strategy'])

        if parsed['ticker'] in self.combo_ticker['values']:
            self.combo_ticker.set(parsed['ticker'])

        self.entry_start.delete(0, 'end')
        self.entry_start.insert(0, parsed['start_date'])

        self.entry_seed.delete(0, 'end')
        self.entry_seed.insert(0, f"{parsed['initial_seed']:,.0f}")

        self.entry_memo.delete(0, 'end')
        self.entry_memo.insert(0, f"CSV 복원 연동 ({parsed['start_date']}~{parsed['current_date']}, {parsed['record_count']}일분)")

        status_msg = (
            f"✔ CSV 연동 준비 완료 (총 {parsed['record_count']}일치 기록)\n"
            f"• 운용 기간: {parsed['start_date']} ~ {parsed['current_date']}\n"
            f"• 최종 자산: ${parsed['total_asset']:,.0f} | 보유: {parsed['current_hold']:,}주 | 예수금: ${parsed['current_cash']:,.0f}\n"
            f"계좌 생성 시 위 거래 내역이 그대로 이어서 등록됩니다."
        )
        self.lbl_import_status.config(text=status_msg, foreground=COLORS['accent_green'])

    def _save_account(self):
        name = self.entry_name.get().strip()
        strat = self.combo_strat.get()
        ticker = self.combo_ticker.get()
        start_date = self.entry_start.get().strip()
        seed_str = self.entry_seed.get().replace(',', '').strip()
        reserve_str = self.combo_reserve.get().replace('%', '').strip()
        memo = self.entry_memo.get().strip()

        if not name:
            messagebox.showwarning("입력 오류", "계좌명을 입력해주세요.", parent=self)
            return

        try:
            seed = float(seed_str)
            if seed <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showwarning("입력 오류", "초기 시드는 0보다 큰 숫자로 입력해주세요.", parent=self)
            return

        try:
            reserve_ratio = float(reserve_str) / 100.0
            if reserve_ratio < 0.0 or reserve_ratio > 1.0:
                raise ValueError()
        except ValueError:
            messagebox.showwarning("입력 오류", "위기준비금 비율은 0% ~ 100% 사이의 숫자로 입력해주세요.", parent=self)
            return

        try:
            datetime.strptime(start_date, '%Y-%m-%d')
        except ValueError:
            messagebox.showwarning("입력 오류", "시작일자는 YYYY-MM-DD 형식으로 입력해주세요.", parent=self)
            return

        if self.imported_data:
            acc = self.mgr.add_account(
                name=name,
                strategy=strat,
                ticker=ticker,
                start_date=start_date,
                initial_seed=seed,
                memo=memo,
                trade_records=self.imported_data['trade_records'],
                current_date=self.imported_data['current_date'],
                reserve_ratio=reserve_ratio
            )
        else:
            acc = self.mgr.add_account(name, strat, ticker, start_date, seed, memo, reserve_ratio=reserve_ratio)

        self.on_success_callback(acc['id'])
        self.destroy()


class EditAccountDialog(tk.Toplevel):
    """
    계좌 기본 설정(계좌 별칭, 위기준비금 비율, 메모, 초기 시드) 변경 모달 다이얼로그
    """

    def __init__(self, parent, account: dict, on_success_callback):
        super().__init__(parent)
        self.title("⚙ 계좌 설정 변경")
        self.geometry("490x440")
        self.resizable(False, False)
        self.configure(bg=COLORS['bg_card'])
        self.transient(parent)
        self.grab_set()

        self.account = account
        self.mgr = AccountManager()
        self.on_success_callback = on_success_callback
        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text="⚙ 계좌 기본 설정 및 위기준비금 수정", style='Title.TLabel', font=FONTS['subtitle']).pack(anchor='w', padx=20, pady=(16, 12))

        form = ttk.Frame(self, style='Card.TFrame')
        form.pack(fill='both', expand=True, padx=20)

        # 1. 대상 종목 및 전략 (조회 전용)
        ttk.Label(form, text="종목 / 전략:", style='Card.TLabel', font=FONTS['body_bold']).grid(row=0, column=0, sticky='w', pady=6)
        info_txt = f"{self.account.get('ticker', '')} | {self.account.get('strategy', '')}"
        ttk.Label(form, text=info_txt, style='CardMuted.TLabel', font=FONTS['body']).grid(row=0, column=1, sticky='w', pady=6)

        # 2. 계좌 별칭
        ttk.Label(form, text="계좌 별칭 (Name):", style='Card.TLabel', font=FONTS['body_bold']).grid(row=1, column=0, sticky='w', pady=6)
        self.entry_name = ttk.Entry(form, width=28)
        self.entry_name.insert(0, self.account.get('name', ''))
        self.entry_name.grid(row=1, column=1, sticky='w', pady=6)

        # 3. 위기준비금 비율 (%)
        ttk.Label(form, text="위기준비금 비율 (%):", style='Card.TLabel', font=FONTS['body_bold']).grid(row=2, column=0, sticky='w', pady=6)
        current_r = float(self.account.get('reserve_ratio', 0.05)) * 100.0
        self.combo_reserve = ttk.Combobox(form, values=['0%', '5%', '10%', '15%', '20%'], width=26)
        self.combo_reserve.set(f"{current_r:.0f}%" if current_r.is_integer() else f"{current_r:.1f}%")
        self.combo_reserve.grid(row=2, column=1, sticky='w', pady=6)

        # 위기준비금 안내 카드
        lbl_hint = ttk.Label(
            form,
            text="💡 위기준비금(AK): 급락장 대비 안전자산으로 차감 보관됩니다.\n"
                 "남은 순운용 시드(AR)를 기준으로 시장 모드별 분할 매수(8분할 등)가 집행됩니다.",
            foreground=COLORS['accent_cyan'],
            font=FONTS['caption'],
            wraplength=380
        )
        lbl_hint.grid(row=3, column=0, columnspan=2, sticky='w', pady=(2, 8))

        # 4. 초기 투자 시드 ($)
        ttk.Label(form, text="초기 투자 시드 ($):", style='Card.TLabel', font=FONTS['body_bold']).grid(row=4, column=0, sticky='w', pady=6)
        self.entry_seed = ttk.Entry(form, width=28)
        self.entry_seed.insert(0, f"{float(self.account.get('initial_seed', 0)):,.0f}")
        self.entry_seed.grid(row=4, column=1, sticky='w', pady=6)

        # 5. 메모
        ttk.Label(form, text="계좌 설명 / 메모:", style='Card.TLabel', font=FONTS['body_bold']).grid(row=5, column=0, sticky='w', pady=6)
        self.entry_memo = ttk.Entry(form, width=28)
        self.entry_memo.insert(0, self.account.get('memo', ''))
        self.entry_memo.grid(row=5, column=1, sticky='w', pady=6)

        # 버튼 영역
        btn_box = ttk.Frame(self, style='Card.TFrame')
        btn_box.pack(fill='x', padx=20, pady=(16, 20))

        btn_cancel = ttk.Button(btn_box, text="취소", command=self.destroy)
        btn_cancel.pack(side='right', padx=(8, 0))

        btn_save = ttk.Button(btn_box, text="설정 저장 완료", style='Success.TButton', command=self._save_settings)
        btn_save.pack(side='right')

    def _save_settings(self):
        name = self.entry_name.get().strip()
        if not name:
            messagebox.showwarning("입력 오류", "계좌명을 입력해주세요.", parent=self)
            return

        reserve_str = self.combo_reserve.get().replace('%', '').strip()
        try:
            reserve_ratio = float(reserve_str) / 100.0
            if reserve_ratio < 0.0 or reserve_ratio > 1.0:
                raise ValueError()
        except ValueError:
            messagebox.showwarning("입력 오류", "위기준비금 비율은 0% ~ 100% 사이의 숫자로 입력해주세요.", parent=self)
            return

        seed_str = self.entry_seed.get().replace(',', '').strip()
        try:
            seed = float(seed_str)
            if seed <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showwarning("입력 오류", "초기 시드는 0보다 큰 숫자로 입력해주세요.", parent=self)
            return

        memo = self.entry_memo.get().strip()

        # 계좌 설정 업데이트
        self.mgr.update_account_settings(
            acc_id=self.account['id'],
            name=name,
            reserve_ratio=reserve_ratio,
            memo=memo,
            initial_seed=seed
        )

        messagebox.showinfo("설정 변경 완료", f"계좌 설정이 성공적으로 저장되었습니다.\n• 위기준비금 비율: {reserve_ratio*100:.1f}%\n• 시드 및 주문표가 즉시 재계산됩니다.", parent=self)
        self.on_success_callback(self.account['id'])
        self.destroy()


class CashAdjustmentDialog(tk.Toplevel):
    """
    자산 추가(입금) 및 세금 납부 등을 위한 자산 인출(출금) 다이얼로그
    """

    def __init__(self, parent, account: dict, on_success_callback):
        super().__init__(parent)
        self.title("💰 자산 입금 / 출금(세금 인출)")
        self.geometry("420x350")
        self.resizable(False, False)
        self.configure(bg=COLORS['bg_card'])
        self.transient(parent)
        self.grab_set()

        self.account = account
        self.on_success_callback = on_success_callback
        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text=f"자산 변동 등록 ({self.account['name']})", style='Title.TLabel', font=FONTS['subtitle']).pack(anchor='w', padx=20, pady=(16, 12))

        form = ttk.Frame(self, style='Card.TFrame')
        form.pack(fill='both', expand=True, padx=20)

        # 1. 구분
        ttk.Label(form, text="구분 (Type):", style='Card.TLabel', font=FONTS['body_bold']).grid(row=0, column=0, sticky='w', pady=8)
        self.combo_type = ttk.Combobox(form, values=['출금 (세금 납부/인출)', '입금 (투자 시드 추가)'], state='readonly', width=24)
        self.combo_type.set('출금 (세금 납부/인출)')
        self.combo_type.grid(row=0, column=1, sticky='w', pady=8)

        # 2. 금액 ($)
        ttk.Label(form, text="금액 ($):", style='Card.TLabel', font=FONTS['body_bold']).grid(row=1, column=0, sticky='w', pady=8)
        self.entry_amount = ttk.Entry(form, width=26)
        self.entry_amount.insert(0, "5000")
        self.entry_amount.grid(row=1, column=1, sticky='w', pady=8)

        # 3. 일자
        ttk.Label(form, text="반영 일자 (YYYY-MM-DD):", style='Card.TLabel', font=FONTS['body_bold']).grid(row=2, column=0, sticky='w', pady=8)
        self.entry_date = ttk.Entry(form, width=26)
        self.entry_date.insert(0, datetime.now().strftime('%Y-%m-%d'))
        self.entry_date.grid(row=2, column=1, sticky='w', pady=8)

        # 4. 사유 / 메모
        ttk.Label(form, text="사유 / 메모:", style='Card.TLabel', font=FONTS['body_bold']).grid(row=3, column=0, sticky='w', pady=8)
        self.entry_reason = ttk.Entry(form, width=26)
        self.entry_reason.insert(0, "해외주식 양도소득세 출금")
        self.entry_reason.grid(row=3, column=1, sticky='w', pady=8)

        # 버튼 박스
        btn_box = ttk.Frame(self, style='Card.TFrame')
        btn_box.pack(fill='x', padx=20, pady=(16, 20))

        btn_cancel = ttk.Button(btn_box, text="취소", command=self.destroy)
        btn_cancel.pack(side='right', padx=(8, 0))

        btn_save = ttk.Button(btn_box, text="등록 완료", style='Success.TButton', command=self._save_adjustment)
        btn_save.pack(side='right')

    def _save_adjustment(self):
        type_str = 'WITHDRAW' if '출금' in self.combo_type.get() else 'DEPOSIT'
        amt_str = self.entry_amount.get().replace(',', '').strip()
        date_str = self.entry_date.get().strip()
        reason = self.entry_reason.get().strip()

        try:
            amt = float(amt_str)
            if amt <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showwarning("입력 오류", "금액은 0보다 큰 숫자로 입력해주세요.", parent=self)
            return

        try:
            datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            messagebox.showwarning("입력 오류", "일자는 YYYY-MM-DD 형식으로 입력해주세요.", parent=self)
            return

        mgr = AccountManager()
        mgr.add_adjustment(self.account['id'], type_str, amt, date_str, reason)
        self.on_success_callback(self.account['id'])
        self.destroy()


class NettingDetailsDialog(tk.Toplevel):
    """
    퉁치기(자전거래 상계) 상세 분석 및 상계 전 원본 주문 내역 대화상자
    """

    def __init__(self, parent, details: dict):
        super().__init__(parent)
        self.title("⚡ 퉁치기 (자전거래 상계) 분석 상세 내역")
        self.geometry("880x620")
        self.minsize(760, 500)
        self.configure(bg=COLORS['bg_card'])
        self.transient(parent)
        self.grab_set()

        self.details = details
        self._build_ui()

    def _build_ui(self):
        net_info = self.details.get('netting_info', {})
        is_netted = net_info.get('is_netted', False)
        max_offset = net_info.get('max_offset_qty', 0)
        p_min = net_info.get('overlap_price_min')
        p_max = net_info.get('overlap_price_max')

        # 상단 요약 헤더
        header = ttk.Frame(self, style='Card.TFrame', padding=(20, 14))
        header.pack(fill='x')

        lbl_title = ttk.Label(header, text=f"⚡ 퉁치기(상계) 상세 분석: {self.details['account_name']}", style='Title.TLabel', font=FONTS['subtitle'])
        lbl_title.pack(anchor='w')

        summary_box = ttk.Frame(header, style='CardAlt.TFrame', padding=(12, 10))
        summary_box.pack(fill='x', pady=(10, 0))

        if is_netted:
            lbl_status = ttk.Label(summary_box, text=f"● 퉁치기 적용 완료: 최대 {max_offset:,}주 자전거래 상계 처리됨", style='KPIVal.TLabel', foreground=COLORS['accent_cyan'], font=FONTS['body_bold'])
            lbl_status.pack(anchor='w')

            desc_text = (
                f"• 중복 호가 체결 구간: ${p_min:.2f} ~ ${p_max:.2f}\n"
                f"• 원리: 당일 매도 조건(종가 ≥ 매도가)과 매수 조건(종가 ≤ 매수가)이 동시에 충족되는 구간에서는 "
                f"양방향 주문이 동시에 체결되어 의미 없는 자전거래와 수수료가 발생합니다.\n"
                f"  본 시스템은 겹치는 구간({max_offset:,}주)을 사전 상계(퉁치기)하여, "
                f"순매도 잔여 수량 및 순매수 수량만 실주문으로 분리 산출했습니다."
            )
            lbl_desc = ttk.Label(summary_box, text=desc_text, style='TLabel', foreground=COLORS['text_primary'], font=FONTS['caption'], wraplength=820)
            lbl_desc.pack(anchor='w', pady=(6, 0))
        else:
            lbl_status = ttk.Label(summary_box, text="● 퉁치기 대상 없음: 매수와 매도 호가 구간이 중복되지 않음", style='KPIVal.TLabel', foreground=COLORS['text_muted'], font=FONTS['body_bold'])
            lbl_status.pack(anchor='w')

            desc_text = "• 매수 주문의 최고가가 매도 주문의 최저가보다 낮아 양방향 동시 체결 가능성이 없으므로, 원본 주문이 그대로 유지됩니다."
            lbl_desc = ttk.Label(summary_box, text=desc_text, style='TLabel', foreground=COLORS['text_muted'], font=FONTS['caption'])
            lbl_desc.pack(anchor='w', pady=(4, 0))

        # 본문: 상계 전 원본 주문 2단 비교
        body = ttk.Frame(self, style='Card.TFrame', padding=(20, 10))
        body.pack(fill='both', expand=True)

        # 좌: 상계 전 원본 매도 주문
        left_frame = ttk.LabelFrame(body, text="🔴 상계 전 원본 매도 주문 (Raw Sells)", padding=8)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 6))

        sell_cols = ('구분', '주문유형', '주문단가', '수량', '체결조건')
        tree_raw_s = ttk.Treeview(left_frame, columns=sell_cols, show='headings', height=8)
        for c in sell_cols:
            tree_raw_s.heading(c, text=c)
            tree_raw_s.column(c, width=120 if c == '체결조건' else 75, anchor='center')
        tree_raw_s.pack(fill='both', expand=True)

        raw_sells = net_info.get('raw_sell_orders', [])
        if not raw_sells:
            tree_raw_s.insert('', 'end', values=('보유 없음', '-', '-', '-', '매도 주문 없음'))
        else:
            for s in raw_sells:
                tree_raw_s.insert('', 'end', values=(
                    s.get('stage', '매도'),
                    s.get('type', 'LOC 매도'),
                    f"${s['price']:.2f}",
                    f"{s['qty']:,}주",
                    s.get('raw', {}).get('condition', f"종가 ≥ ${s['price']:.2f}")
                ))

        # 우: 상계 전 원본 매수 주문
        right_frame = ttk.LabelFrame(body, text="🟢 상계 전 원본 매수 주문 (Raw Buys)", padding=8)
        right_frame.pack(side='right', fill='both', expand=True, padx=(6, 0))

        buy_cols = ('호가단계', '주문유형', '주문단가', '수량', '체결조건')
        tree_raw_b = ttk.Treeview(right_frame, columns=buy_cols, show='headings', height=8)
        for c in buy_cols:
            tree_raw_b.heading(c, text=c)
            tree_raw_b.column(c, width=120 if c == '체결조건' else 75, anchor='center')
        tree_raw_b.pack(fill='both', expand=True)

        raw_buys = net_info.get('raw_buy_orders', [])
        if not raw_buys:
            tree_raw_b.insert('', 'end', values=('매수 없음', '-', '-', '-', '매수 주문 없음'))
        else:
            for b in raw_buys:
                tree_raw_b.insert('', 'end', values=(
                    b.get('stage', '매수'),
                    b.get('type', 'LOC 매수'),
                    f"${b['price']:.2f}",
                    f"{b['qty']:,}주",
                    b.get('raw', {}).get('condition', f"종가 ≤ ${b['price']:.2f}")
                ))

        # 하단 닫기 버튼
        btn_bar = ttk.Frame(self, style='Card.TFrame', padding=(20, 12))
        btn_bar.pack(fill='x')
        ttk.Button(btn_bar, text="닫기", command=self.destroy).pack(side='right')


class AccountsTab(ttk.Frame):
    """
    첫 페이지: 활성화된 계좌 목록 관리 및 상세 대시보드
    """

    def __init__(self, parent, get_market_data_func):
        super().__init__(parent, style='TFrame')
        self.get_market_data_func = get_market_data_func
        self.mgr = AccountManager()
        self.selected_account_id = None
        self.current_details = None

        self._build_ui()

    def _build_ui(self):
        # 좌우 분할 패널 (좌: 계좌 목록 / 우: 계좌 상세 대시보드)
        paned = ttk.PanedWindow(self, orient='horizontal')
        paned.pack(fill='both', expand=True, padx=12, pady=12)

        # -------------------------------------------------------------
        # [Left] 계좌 목록 패널 (Master List)
        # -------------------------------------------------------------
        left_frame = ttk.Frame(paned, style='Card.TFrame', padding=12)
        paned.add(left_frame, weight=1)

        # 목록 헤더 (+ 버튼 포함)
        header_left = ttk.Frame(left_frame, style='Card.TFrame')
        header_left.pack(fill='x', pady=(0, 10))

        ttk.Label(header_left, text="💼 내 투자 계좌", style='CardTitle.TLabel').pack(side='left')

        btn_add = ttk.Button(header_left, text="➕ 새 계좌 추가", style='Success.TButton', command=self.open_add_account_dialog)
        btn_add.pack(side='right')

        # 계좌 트리뷰 목록
        acc_cols = ('계좌명', '종목', '전략')
        self.tree_acc = ttk.Treeview(left_frame, columns=acc_cols, show='headings', height=18)
        for c in acc_cols:
            self.tree_acc.heading(c, text=c)
            w = 110 if c == '계좌명' else (60 if c == '종목' else 90)
            self.tree_acc.column(c, width=w, anchor='center')

        scroll_acc = ttk.Scrollbar(left_frame, orient='vertical', command=self.tree_acc.yview)
        self.tree_acc.configure(yscrollcommand=scroll_acc.set)
        self.tree_acc.pack(fill='both', expand=True)
        self.tree_acc.bind('<<TreeviewSelect>>', self._on_account_selected)
        self.tree_acc.bind('<ButtonRelease-1>', self._on_tree_click)

        # 하단 조작 버튼
        action_box = ttk.Frame(left_frame, style='Card.TFrame')
        action_box.pack(fill='x', pady=(10, 0))

        btn_del = ttk.Button(action_box, text="🗑 계좌 삭제", style='TButton', command=self.delete_selected_account)
        btn_del.pack(side='left', fill='x', expand=True, padx=(0, 4))

        btn_reload = ttk.Button(action_box, text="🔄 새로고침", style='TButton', command=self.reload_accounts)
        btn_reload.pack(side='right', fill='x', expand=True, padx=(4, 0))

        # -------------------------------------------------------------
        # [Right] 선택된 계좌 상세 뷰 (Detail View)
        # -------------------------------------------------------------
        self.right_frame = ttk.Frame(paned, style='TFrame', padding=(8, 0))
        paned.add(self.right_frame, weight=3)

        # (A) 빈 상태 안내 프레임 (계좌 미선택 시)
        self.empty_frame = ttk.Frame(self.right_frame, style='Card.TFrame', padding=30)
        lbl_empty_icon = ttk.Label(self.empty_frame, text="🚀", font=('Segoe UI', 40), style='Card.TLabel')
        lbl_empty_icon.pack(pady=(40, 10))
        lbl_empty_title = ttk.Label(self.empty_frame, text="등록된 계좌가 없습니다.", style='CardTitle.TLabel', font=FONTS['title'])
        lbl_empty_title.pack(pady=(0, 8))
        lbl_empty_desc = ttk.Label(
            self.empty_frame,
            text="좌측 상단의 '+ 새 계좌 추가' 버튼을 눌러 계좌명, 시작일, 초기 시드를 설정하고 투자를 시작하세요!\n"
                 "등록 후에는 오늘 걸어야 할 LOC 주문표와 매매 기록, 세금 인출/추가 입금 관리를 한눈에 볼 수 있습니다.",
            style='CardMuted.TLabel', justify='center'
        )
        lbl_empty_desc.pack(pady=(0, 20))
        btn_empty_add = ttk.Button(self.empty_frame, text="➕ 첫 번째 계좌 등록하기", style='Success.TButton', command=self.open_add_account_dialog)
        btn_empty_add.pack()
        self.empty_frame.pack(fill='both', expand=True)

        # (B) 계좌 상세 컨테이너 (계좌 선택 시 표시)
        self.detail_container = ttk.Frame(self.right_frame, style='TFrame')

        # 1. 상단 계좌 요약 카드 (시작일, 초기시드, 현재가, 총자산, 수익률 등)
        self._build_account_header_card()

        # 2. 하부 세부 탭 컨테이너 (오늘 주문표 / 매매 기록 / 입출금 내역)
        self.detail_notebook = ttk.Notebook(self.detail_container)
        self.detail_notebook.pack(fill='both', expand=True, pady=(8, 0))

        self._build_subtab_today_orders()
        self._build_subtab_trade_logs()
        self._build_subtab_adjustments()

    def _build_account_header_card(self):
        header_card = ttk.Frame(self.detail_container, style='Card.TFrame', padding=14)
        header_card.pack(fill='x', pady=(0, 6))

        # 1행: 계좌명, 종목/전략 뱃지, 입출금 버튼
        row1 = ttk.Frame(header_card, style='Card.TFrame')
        row1.pack(fill='x', pady=(0, 10))

        self.lbl_acc_name = ttk.Label(row1, text="계좌명", style='Title.TLabel', font=FONTS['subtitle'])
        self.lbl_acc_name.pack(side='left')

        self.lbl_acc_badge = ttk.Label(row1, text="SOXL | 종종이 기본전략", style='CardMuted.TLabel', font=FONTS['caption'])
        self.lbl_acc_badge.pack(side='left', padx=(10, 0))

        # 입/출금 관리 및 계좌 설정 액션 버튼들
        btn_withdraw = ttk.Button(row1, text="➖ 자산 인출 (세금 등)", style='TButton', command=self.open_withdraw_dialog)
        btn_withdraw.pack(side='right', padx=(6, 0))

        btn_deposit = ttk.Button(row1, text="➕ 자산 추가 (입금)", style='Success.TButton', command=self.open_deposit_dialog)
        btn_deposit.pack(side='right', padx=(6, 0))

        btn_edit = ttk.Button(row1, text="⚙ 계좌 설정", style='TButton', command=self.open_edit_account_dialog)
        btn_edit.pack(side='right')

        # 2행: 핵심 5대 지표 카드 (언제 시작? 초기시드? 현재보유 및 매도대기수? 현재가격? 현재총자산/수익률?)
        kpi_grid = ttk.Frame(header_card, style='Card.TFrame')
        kpi_grid.pack(fill='x')

        self.card_start = self._create_mini_kpi(kpi_grid, "운용 시작일", "-", "경과일수: -")
        self.card_seed = self._create_mini_kpi(kpi_grid, "초기 투자 시드", "-", "순투자원금: -")
        self.card_hold = self._create_mini_kpi(kpi_grid, "보유량 / 매도 대기", "-", "매도 대기 수: -")
        self.card_price = self._create_mini_kpi(kpi_grid, "현재 종가 (기준일)", "-", "평균단가: -")
        self.card_asset = self._create_mini_kpi(kpi_grid, "현재 총 평가자산", "-", "수익률: -")

        self.card_start.pack(side='left', fill='both', expand=True, padx=(0, 4))
        self.card_seed.pack(side='left', fill='both', expand=True, padx=4)
        self.card_hold.pack(side='left', fill='both', expand=True, padx=4)
        self.card_price.pack(side='left', fill='both', expand=True, padx=4)
        self.card_asset.pack(side='left', fill='both', expand=True, padx=(4, 0))

    def _create_mini_kpi(self, parent, title, main_val, sub_val):
        f = ttk.Frame(parent, style='CardAlt.TFrame', padding=(10, 8))
        lbl_t = ttk.Label(f, text=title, style='KPILbl.TLabel')
        lbl_t.pack(anchor='w')
        lbl_m = ttk.Label(f, text=main_val, style='KPIVal.TLabel', font=('Segoe UI', 14, 'bold'))
        lbl_m.pack(anchor='w', pady=(2, 2))
        lbl_s = ttk.Label(f, text=sub_val, style='CardMuted.TLabel')
        lbl_s.pack(anchor='w')
        f.lbl_title = lbl_t
        f.lbl_main = lbl_m
        f.lbl_sub = lbl_s
        return f

    def _build_subtab_today_orders(self):
        tab = ttk.Frame(self.detail_notebook, style='TFrame', padding=10)
        self.detail_notebook.add(tab, text="  📋 오늘의 매수/매도 주문표  ")

        # 상단 도구모음 (운용 툴바)
        top_bar = ttk.Frame(tab, style='TFrame')
        top_bar.pack(fill='x', pady=(0, 8))

        left_box = ttk.Frame(top_bar, style='TFrame')
        left_box.pack(side='left')

        self.lbl_today_badge = ttk.Label(left_box, text="📅 운용 기준일: -", style='Title.TLabel', font=FONTS['body_bold'], foreground=COLORS['accent_cyan'])
        self.lbl_today_badge.pack(anchor='w')

        mode_box = ttk.Frame(left_box, style='TFrame')
        mode_box.pack(anchor='w', pady=(2, 0))
        self.lbl_today_mode = ttk.Label(mode_box, text="현재 모드: -", style='CardMuted.TLabel', font=FONTS['caption'])
        self.lbl_today_mode.pack(side='left')

        ttk.Label(mode_box, text=" | 수동 모드 설정: ", style='CardMuted.TLabel', font=FONTS['caption']).pack(side='left')
        self.combo_mode = ttk.Combobox(mode_box, values=['Normal', 'Safe', 'Riskoff'], state='readonly', width=8, font=FONTS['caption'])
        self.combo_mode.set('Normal')
        self.combo_mode.pack(side='left')
        self.combo_mode.bind('<<ComboboxSelected>>', self._on_mode_dropdown_changed)

        # 우측 액션 버튼들 (Next Day, 당일 종가/체결 입력, Undo, 복사)
        right_box = ttk.Frame(top_bar, style='TFrame')
        right_box.pack(side='right')

        btn_copy = ttk.Button(right_box, text="📋 MTS/HTS 주문 복사", style='TButton', command=self.copy_orders)
        btn_copy.pack(side='right', padx=(6, 0))

        btn_undo = ttk.Button(right_box, text="⏪ 마지막 거래일 삭제 (Undo)", style='TButton', command=self.on_delete_last_day)
        btn_undo.pack(side='right', padx=(6, 0))

        btn_fill = ttk.Button(right_box, text="🏁 당일 종가 & 체결 입력", style='Success.TButton', command=self.open_record_close_dialog)
        btn_fill.pack(side='right', padx=(6, 0))

        btn_next = ttk.Button(right_box, text="▶ Next Day (다음 거래일)", style='Primary.TButton', command=self.on_advance_next_day)
        btn_next.pack(side='right')

        # 퉁치기(상계) 상태 알림 배너
        self.netting_banner = ttk.Frame(tab, style='CardAlt.TFrame', padding=(10, 8))
        self.netting_banner.pack(fill='x', pady=(0, 8))

        self.lbl_netting_icon = ttk.Label(self.netting_banner, text="⚡ 퉁치기 안내:", style='KPIVal.TLabel', foreground=COLORS['accent_cyan'], font=FONTS['body_bold'])
        self.lbl_netting_icon.pack(side='left', padx=(0, 6))

        self.lbl_netting_text = ttk.Label(self.netting_banner, text="상계 정보 확인 중...", style='TLabel', foreground=COLORS['text_primary'], wraplength=760)
        self.lbl_netting_text.pack(side='left', fill='x', expand=True)

        self.btn_view_raw = ttk.Button(self.netting_banner, text="🔍 퉁치기 상세 내역", style='TButton', command=self.open_netting_details_dialog)
        self.btn_view_raw.pack(side='right')

        # 매도 주문표
        self.sell_frame = ttk.LabelFrame(tab, text="🔴 오늘의 순 매도 주문 (LOC) [퉁치기 반영]", padding=8)
        self.sell_frame.pack(fill='x', pady=(0, 8))

        sell_cols = ('구분', '주문유형', '주문단가', '주문수량', '누적수량', '예상금액', '체결조건', '비고')
        self.tree_sell = ttk.Treeview(self.sell_frame, columns=sell_cols, show='headings', height=4)
        for c in sell_cols:
            self.tree_sell.heading(c, text=c)
            w = 150 if c in ('구분', '체결조건', '비고') else 95
            self.tree_sell.column(c, width=w, anchor='center')
        self.tree_sell.pack(fill='x')

        # 매수 주문표
        self.buy_frame = ttk.LabelFrame(tab, text="🟢 오늘의 순 분할 매수 주문 (LOC) [퉁치기 반영]", padding=8)
        self.buy_frame.pack(fill='both', expand=True)

        buy_cols = ('호가단계', '주문유형', '주문단가', '주문수량', '누적수량', '예상금액', '체결조건', '비고')
        self.tree_buy = ttk.Treeview(self.buy_frame, columns=buy_cols, show='headings', height=6)
        for c in buy_cols:
            self.tree_buy.heading(c, text=c)
            w = 150 if c in ('호가단계', '체결조건', '비고') else 95
            self.tree_buy.column(c, width=w, anchor='center')

        s_buy = ttk.Scrollbar(self.buy_frame, orient='vertical', command=self.tree_buy.yview)
        self.tree_buy.configure(yscrollcommand=s_buy.set)
        self.tree_buy.pack(side='left', fill='both', expand=True)
        s_buy.pack(side='right', fill='y')

    def _build_subtab_trade_logs(self):
        tab = ttk.Frame(self.detail_notebook, style='TFrame', padding=10)
        self.detail_notebook.add(tab, text="  📜 계좌 매매 기록 내역  ")

        top_bar = ttk.Frame(tab, style='TFrame')
        top_bar.pack(fill='x', pady=(0, 6))

        self.lbl_log_summary = ttk.Label(top_bar, text="총 거래일수: -", style='TLabel', font=FONTS['body_bold'])
        self.lbl_log_summary.pack(side='left')

        btn_export = ttk.Button(top_bar, text="💾 CSV 내보내기", style='Success.TButton', command=self.export_trade_logs_csv)
        btn_export.pack(side='right', padx=(6, 0))

        btn_undo_log = ttk.Button(top_bar, text="⏪ 마지막 거래일 삭제 (Undo)", style='TButton', command=self.on_delete_last_day)
        btn_undo_log.pack(side='right')

        table_frame = ttk.Frame(tab, style='Card.TFrame', padding=6)
        table_frame.pack(fill='both', expand=True)

        log_cols = ('날짜', '종가', '모드', '슬롯상태', '매수수량', '매도일', '실현손익', '보유수량', '보유현금', '총평가자산')
        self.tree_log = ttk.Treeview(table_frame, columns=log_cols, show='headings')
        for c in log_cols:
            self.tree_log.heading(c, text=c)
            if c in ('슬롯상태', '총평가자산', '보유현금'):
                w = 160 if c == '슬롯상태' else 110
            elif c in ('날짜', '매도일'):
                w = 95
            elif c in ('매수수량', '실현손익'):
                w = 85
            else:
                w = 75
            self.tree_log.column(c, width=w, anchor='center')

        # 더블클릭 이벤트 연결 (특정 거래일 수정)
        self.tree_log.bind('<Double-Button-1>', self.on_tree_log_double_click)

        # Treeview 색상 태그 설정
        self.tree_log.tag_configure('tag_active', background='#163d27', foreground='#86efac')
        self.tree_log.tag_configure('tag_profit_pos', foreground='#f87171')
        self.tree_log.tag_configure('tag_profit_neg', foreground='#60a5fa')
        self.tree_log.tag_configure('tag_normal', foreground=COLORS['text_primary'])

        s_y = ttk.Scrollbar(table_frame, orient='vertical', command=self.tree_log.yview)
        self.tree_log.configure(yscrollcommand=s_y.set)
        self.tree_log.pack(side='left', fill='both', expand=True)
        s_y.pack(side='right', fill='y')

        ttk.Label(tab, text="💡 [안내] 특정 거래일 행을 더블클릭하면 종가/체결량을 직접 수정할 수 있습니다. 잘못 입력한 경우 [⏪ 마지막 거래일 삭제]로 안전하게 취소하세요.", 
                  foreground=COLORS['text_muted'], font=FONTS['caption']).pack(anchor='w', pady=(4, 0))

    def _build_subtab_adjustments(self):
        tab = ttk.Frame(self.detail_notebook, style='TFrame', padding=10)
        self.detail_notebook.add(tab, text="  💸 자산 입/출금 내역 (세금 등)  ")

        top_bar = ttk.Frame(tab, style='TFrame')
        top_bar.pack(fill='x', pady=(0, 6))

        self.lbl_adj_summary = ttk.Label(top_bar, text="총 추가입금: $0 | 총 세금/출금: $0", style='TLabel', font=FONTS['body_bold'])
        self.lbl_adj_summary.pack(side='left')

        table_frame = ttk.Frame(tab, style='Card.TFrame', padding=6)
        table_frame.pack(fill='both', expand=True)

        adj_cols = ('일자', '구분', '금액($)', '사유/메모')
        self.tree_adj = ttk.Treeview(table_frame, columns=adj_cols, show='headings')
        for c in adj_cols:
            self.tree_adj.heading(c, text=c)
            w = 220 if c == '사유/메모' else 110
            self.tree_adj.column(c, width=w, anchor='center')

        s_y = ttk.Scrollbar(table_frame, orient='vertical', command=self.tree_adj.yview)
        self.tree_adj.configure(yscrollcommand=s_y.set)
        self.tree_adj.pack(side='left', fill='both', expand=True)
        s_y.pack(side='right', fill='y')

    def reload_accounts(self, select_id: str = None):
        """
        계좌 목록을 파일에서 새로고침하여 트리뷰에 표시합니다.
        """
        accounts = self.mgr.load_accounts()
        self.tree_acc.delete(*self.tree_acc.get_children())

        if not accounts:
            self.empty_frame.pack(fill='both', expand=True)
            self.detail_container.pack_forget()
            self.selected_account_id = None
            self.current_details = None
            return

        self.empty_frame.pack_forget()
        self.detail_container.pack(fill='both', expand=True)

        target_item = None
        for a in accounts:
            item_id = self.tree_acc.insert('', 'end', iid=a['id'], values=(a['name'], a['ticker'], a['strategy']))
            if select_id and a['id'] == select_id:
                target_item = item_id

        # 선택 항목 지정 및 즉시 상세 로드
        chosen_id = target_item if target_item else (accounts[0]['id'] if accounts else None)
        if chosen_id:
            self.tree_acc.selection_set(chosen_id)
            self.tree_acc.focus(chosen_id)
            self.tree_acc.see(chosen_id)
            self.load_account_detail(chosen_id)

    def _on_tree_click(self, event=None):
        """
        트리뷰 항목을 직접 클릭했을 때, 이미 선택된 상태라도 강제로 계좌 상세를 다시 로드합니다.
        """
        if event:
            item = self.tree_acc.identify_row(event.y)
            if item:
                self.load_account_detail(item)

    def _on_account_selected(self, event=None):
        selected = self.tree_acc.selection()
        if not selected:
            return
        acc_id = selected[0]
        self.load_account_detail(acc_id)

    def load_account_detail(self, acc_id: str):
        accounts = self.mgr.load_accounts()
        acc = next((a for a in accounts if a['id'] == acc_id), None)
        if not acc:
            return

        self.selected_account_id = acc_id

        # 시세 데이터 조회 및 상세 연산
        df_market = self.get_market_data_func(acc['ticker'])
        details = self.mgr.compute_account_details(acc, df_market)
        self.current_details = details

        # 1. 상단 계좌 헤더 갱신
        reserve_pct = details.get('reserve_ratio', 0.05) * 100.0
        ak_amt = details.get('ak_val', 0.0)
        ar_amt = details.get('ar_val', details['initial_seed'])
        memo_str = f" (메모: {details['memo']})" if details.get('memo') else ""

        self.lbl_acc_name.config(text=details['account_name'])
        self.lbl_acc_badge.config(
            text=f"{details['ticker']} | {details['strategy_name']} | 🛡 위기준비금: {reserve_pct:.1f}% (${ak_amt:,.0f}) | 📅 {details.get('display_status', '')}{memo_str}"
        )

        # 2. 4대 KPI 카드 갱신
        start_dt = datetime.strptime(details['start_date'], '%Y-%m-%d')
        days_passed = (datetime.now() - start_dt).days

        self.card_start.lbl_main.config(text=details['start_date'], foreground=COLORS['text_white'])
        self.card_start.lbl_sub.config(text=f"운용 경과: {days_passed:,}일째")

        self.card_seed.lbl_main.config(text=f"${details['initial_seed']:,.0f}", foreground=COLORS['accent_cyan'])
        self.card_seed.lbl_sub.config(text=f"위기준비금: {reserve_pct:.1f}% (${ak_amt:,.0f}) | 운용(AR): ${ar_amt:,.0f}")

        self.card_hold.lbl_main.config(text=f"{details['current_hold']:,}주", foreground=COLORS['text_white'])
        pending_cnt = details.get('pending_sell_count', 0)
        self.card_hold.lbl_sub.config(text=f"매도 대기 수: {pending_cnt}개 슬롯", foreground=COLORS['accent_yellow'] if pending_cnt > 0 else COLORS['text_muted'])

        self.card_price.lbl_main.config(text=f"${details['current_price']:.2f}", foreground=COLORS['text_white'])
        self.card_price.lbl_sub.config(text=f"평균단가: ${details['avg_price']:.2f}")

        ret_color = COLORS['accent_green'] if details['total_return_pct'] >= 0 else COLORS['accent_red']
        self.card_asset.lbl_main.config(text=f"${details['current_asset']:,.0f}", foreground=COLORS['accent_blue'])
        self.card_asset.lbl_sub.config(text=f"수익률: {details['total_return_pct']:+.2f}% (${details['total_profit']:+,.0f})", foreground=ret_color)

        # 3. 오늘의 주문표 갱신
        self.lbl_today_badge.config(text=f"📅 운용 기준일: {details.get('display_status', '')}")
        daily_b = details.get('daily_budget', 0.0)
        self.lbl_today_mode.config(
            text=f"{details['mode']} (순운용 시드: ${ar_amt:,.0f} | 1일 예산: ${daily_b:,.0f} / 예수금: ${details['current_cash']:,.2f})"
        )
        if hasattr(self, 'combo_mode'):
            self.combo_mode.set(details.get('mode', 'Normal'))

        net_info = details.get('netting_info', {})
        if net_info.get('is_netted'):
            self.lbl_netting_icon.config(text="⚡ 퉁치기(상계) 적용:", foreground=COLORS['accent_cyan'])
            self.lbl_netting_text.config(text=net_info.get('summary_text', ''), foreground=COLORS['accent_yellow'])
            self.sell_frame.config(text="🔴 오늘의 순 매도 주문 (LOC) [퉁치기 반영]")
            self.buy_frame.config(text="🟢 오늘의 순 분할 매수 주문 (LOC) [퉁치기 반영]")
        else:
            self.lbl_netting_icon.config(text="✔ 퉁치기 대상 없음:", foreground=COLORS['text_muted'])
            self.lbl_netting_text.config(text=net_info.get('summary_text', '중복 호가 구간이 없어 원본 주문이 유지됩니다.'), foreground=COLORS['text_muted'])
            self.sell_frame.config(text="🔴 오늘의 매도 주문 (LOC)")
            self.buy_frame.config(text="🟢 오늘의 분할 매수 주문 (LOC)")

        self.tree_sell.delete(*self.tree_sell.get_children())
        if not details['sell_orders']:
            self.tree_sell.insert('', 'end', values=('보유 없음', '-', '-', '-', '-', '-', '매도할 보유 수량이 없습니다.', '-'))
        else:
            for s in details['sell_orders']:
                self.tree_sell.insert('', 'end', values=(
                    s.get('구분', '-'),
                    s.get('주문유형', '-'),
                    s.get('주문단가', '-'),
                    s.get('주문수량', '-'),
                    s.get('누적수량', s.get('주문수량', '-')),
                    s.get('예상금액', '-'),
                    s.get('체결조건', '-'),
                    s.get('비고', '-')
                ))

        self.tree_buy.delete(*self.tree_buy.get_children())
        if not details['buy_orders']:
            self.tree_buy.insert('', 'end', values=('-', '-', '-', '-', '-', '-', '오늘 실행할 매수 주문이 없습니다.', '-'))
        else:
            for b in details['buy_orders']:
                self.tree_buy.insert('', 'end', values=(
                    b.get('호가단계', '-'),
                    b.get('주문유형', '-'),
                    b.get('주문단가', '-'),
                    b.get('주문수량', '-'),
                    b.get('누적수량', '-'),
                    b.get('예상금액', '-'),
                    b.get('체결조건', '-'),
                    b.get('비고', '-')
                ))

        # 4. 매매 기록 갱신 (액티브 슬롯 전체 녹색, 실현손익 +빨간색, -파란색)
        self.tree_log.delete(*self.tree_log.get_children())
        df_res = details['df_res']
        if len(df_res) == 0:
            self.lbl_log_summary.config(text="총 0거래일 매매 기록 (신규 운용 계좌) | 🟢 액티브 매도 대기: 0개 슬롯")
        else:
            self.lbl_log_summary.config(text=f"총 {len(df_res)}거래일 매매 기록 ({details['start_date']} ~ {details['latest_date']}) | 🟢 액티브 매도 대기: {pending_cnt}개 슬롯")

        # 최근 기록부터 역순 표시
        for _, row in df_res.iloc[::-1].iterrows():
            d_str = row['Date'].strftime('%Y-%m-%d')
            c_str = f"${row['Close']:.2f}"
            m_str = str(row.get('Mode', ''))
            status_str = str(row.get('StatusText', '관망/대기'))
            b_qty = int(row.get('BuyQty', 0))
            b_str = f"{b_qty:,}주" if b_qty > 0 else "-"
            # 매도일자 판별
            w_raw = row.get('W')
            sold_flag = bool(row.get('Sold', False))
            if sold_flag and w_raw is not None and str(w_raw).strip() and str(w_raw) != 'None' and not pd.isna(w_raw):
                w_str = str(w_raw)[:10]
            elif b_qty > 0 and not sold_flag:
                w_str = "대기중"
            else:
                w_str = "-"

            p_val = float(row.get('Profit', 0.0))
            if p_val > 0.01:
                p_str = f"+${p_val:,.2f}"
            elif p_val < -0.01:
                p_str = f"-${abs(p_val):,.2f}"
            else:
                p_str = "-"
            h_str = f"{int(row['Hold']):,}주"
            cash_str = f"${row['Cash']:,.0f}"
            asset_str = f"${row['Asset']:,.0f}"
            tag_name = str(row.get('Tag', 'tag_normal'))

            self.tree_log.insert('', 'end', values=(d_str, c_str, m_str, status_str, b_str, w_str, p_str, h_str, cash_str, asset_str), tags=(tag_name,))

        # 5. 입출금 내역 갱신
        self.tree_adj.delete(*self.tree_adj.get_children())
        self.lbl_adj_summary.config(text=f"총 추가입금: ${details['total_deposited']:,.0f} | 총 세금/출금: ${details['total_withdrawn']:,.0f}")

        for adj in details['adjustments']:
            type_label = "출금 (세금 등)" if adj['type'] == 'WITHDRAW' else "추가 입금"
            self.tree_adj.insert('', 'end', values=(adj['date'], type_label, f"${adj['amount']:,.2f}", adj['reason']))

    def open_netting_details_dialog(self):
        if not self.current_details:
            messagebox.showinfo("알림", "먼저 계좌를 선택해주세요.")
            return
        NettingDetailsDialog(self, self.current_details)

    def open_add_account_dialog(self):
        AddAccountDialog(self, on_success_callback=lambda acc_id: self.reload_accounts(select_id=acc_id))

    def open_edit_account_dialog(self):
        if not self.selected_account_id:
            messagebox.showinfo("알림", "먼저 계좌를 선택해주세요.")
            return
        accounts = self.mgr.load_accounts()
        acc = next((a for a in accounts if a['id'] == self.selected_account_id), None)
        if acc:
            EditAccountDialog(self, acc, on_success_callback=lambda aid: self.reload_accounts(select_id=aid))

    def open_withdraw_dialog(self):
        if not self.selected_account_id:
            messagebox.showinfo("알림", "먼저 계좌를 선택해주세요.")
            return
        accounts = self.mgr.load_accounts()
        acc = next((a for a in accounts if a['id'] == self.selected_account_id), None)
        if acc:
            CashAdjustmentDialog(self, acc, on_success_callback=lambda aid: self.load_account_detail(aid))

    def open_deposit_dialog(self):
        if not self.selected_account_id:
            messagebox.showinfo("알림", "먼저 계좌를 선택해주세요.")
            return
        accounts = self.mgr.load_accounts()
        acc = next((a for a in accounts if a['id'] == self.selected_account_id), None)
        if acc:
            CashAdjustmentDialog(self, acc, on_success_callback=lambda aid: self.load_account_detail(aid))

    def delete_selected_account(self):
        if not self.selected_account_id:
            messagebox.showinfo("알림", "삭제할 계좌를 선택해주세요.")
            return
        if messagebox.askyesno("계좌 삭제 확인", "정말 이 계좌를 삭제하시겠습니까?\n삭제된 계좌 데이터는 복구할 수 없습니다."):
            self.mgr.delete_account(self.selected_account_id)
            self.reload_accounts()

    def copy_orders(self):
        if not self.current_details:
            messagebox.showinfo("알림", "복사할 주문 데이터가 없습니다.")
            return

        d = self.current_details
        net_info = d.get('netting_info', {})
        lines = [
            f"=== 📌 오늘의 LOC 주문표 [{d['account_name']} ({d['ticker']})] ===",
            f"• 전략: {d['strategy_name']} (시작일: {d['start_date']} / 현재가: ${d['current_price']:.2f})",
            f"• 순투자원금: ${d['net_invested']:,.2f} | 총 평가자산: ${d['current_asset']:,.2f}",
            f"• 보유 현금: ${d['current_cash']:,.2f} | 보유 수량: {d['current_hold']:,}주"
        ]
        if net_info.get('is_netted'):
            lines.append(f"⚡ [퉁치기(자전거래 상계) {net_info.get('max_offset_qty', 0):,}주 적용 완료 - 실주문용]")
            lines.append(f"• 중복 상계 구간: ${net_info.get('overlap_price_min', 0):.2f} ~ ${net_info.get('overlap_price_max', 0):.2f}")

        lines.append("")
        lines.append("[1. 매도 주문 (Sell)]")
        if not d['sell_orders']:
            lines.append("  (매도 주문 없음)")
        else:
            for s in d['sell_orders']:
                extra = f" | {s['비고']}" if s.get('비고') else ""
                lines.append(f"  • [{s['주문유형']}] {s['구분']} - 단가: {s['주문단가']} / 수량: {s['주문수량']} ({s['체결조건']}){extra}")

        lines.append("")
        lines.append("[2. 매수 주문 (Buy)]")
        if not d['buy_orders']:
            lines.append("  (매수 주문 없음)")
        else:
            for b in d['buy_orders']:
                extra = f" | {b['비고']}" if b.get('비고') else ""
                lines.append(f"  • [{b['주문유형']}] {b['호가단계']} - 단가: {b['주문단가']} / 수량: {b['주문수량']} ({b['체결조건']}){extra}")

        text = "\n".join(lines)
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("클립보드 복사 완료", f"[{d['account_name']}] 오늘의 주문표가 클립보드에 복사되었습니다!")

    def export_trade_logs_csv(self):
        if not self.selected_account_id or not self.current_details:
            messagebox.showinfo("알림", "내보낼 매매 기록이 없습니다.")
            return
        d = self.current_details
        default_filename = f"{d['account_name'].replace(' ', '_')}_매매기록.csv"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=default_filename,
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            title="계좌 매매 기록 CSV 저장"
        )
        if file_path:
            ok = self.mgr.export_trade_records_csv(self.selected_account_id, file_path)
            if ok:
                messagebox.showinfo(
                    "💾 CSV 내보내기 완료", 
                    f"매매 기록이 성공적으로 저장되었습니다:\n{file_path}\n\n"
                    f"💡 이 CSV 파일은 새 계좌를 추가할 때 [📂 기존 CSV 읽어오기]를 눌러\n"
                    f"언제든지 거래 내역을 그대로 이어서 운용하실 수 있습니다."
                )
            else:
                messagebox.showerror("저장 실패", "CSV 파일 저장 중 오류가 발생했습니다.")

    def on_advance_next_day(self):
        """
        Next Day(다음 거래일) 버튼 클릭 시: 미국 증시 개장일 캘린더를 기준으로 다음 거래일로 전진합니다.
        """
        if not self.selected_account_id:
            messagebox.showinfo("알림", "먼저 계좌를 선택해주세요.")
            return

        acc = self.mgr.advance_next_day(self.selected_account_id)
        if acc:
            self.load_account_detail(self.selected_account_id)
            next_d = acc.get('current_date')
            messagebox.showinfo(
                "▶ Next Day 이동 완료",
                f"[{acc.get('name')}] 운용 기준일이 업데이트되었습니다.\n\n"
                f"📅 새로운 기준일: {next_d} (미국 장전 - 주문 대기)\n"
                f"오늘 밤 체결을 위해 산출된 매수/매도 LOC 주문표를 확인하고 증권사 MTS/HTS에 입력하세요."
            )

    def open_record_close_dialog(self):
        """
        🏁 당일 종가 & 체결 입력 버튼 클릭 시:
        종가 입력 및 자동 LOC 체결 분석 팝업을 띄우고, 사용자가 실제 체결량을 수정/확정할 수 있게 합니다.
        """
        if not self.selected_account_id or not self.current_details:
            messagebox.showinfo("알림", "먼저 계좌를 선택해주세요.")
            return

        accounts = self.mgr.load_accounts()
        acc = next((a for a in accounts if a['id'] == self.selected_account_id), None)
        if not acc:
            return

        today_orders = {
            'sell_orders': self.current_details.get('sell_orders', []),
            'buy_orders': self.current_details.get('buy_orders', []),
            'last_price': self.current_details.get('current_price', 0.0),
            'mode': self.current_details.get('mode', 'Normal'),
            'netting_info': self.current_details.get('netting_info', {})
        }

        RecordCloseDialog(
            self,
            account=acc,
            today_orders=today_orders,
            on_success_callback=self._on_record_close_confirm
        )

    def _on_mode_dropdown_changed(self, event=None):
        """
        사용자가 툴바에서 시장 모드를 수동으로 변경했을 때 계좌 설정을 업데이트하고 주문표를 재계산합니다.
        """
        if not self.selected_account_id:
            return
        new_mode = self.combo_mode.get()
        accounts = self.mgr.load_accounts()
        for a in accounts:
            if a['id'] == self.selected_account_id:
                a['manual_mode'] = new_mode
                break
        self.mgr.save_accounts(accounts)
        self.load_account_detail(self.selected_account_id)

    def _on_record_close_confirm(self, close_p: float, buy_q: int, buy_p: float, sell_q: int, sell_p: float, memo: str):
        """
        체결 정산 다이얼로그에서 확인을 눌렀을 때 계좌 일지에 정산 기록을 반영합니다.
        """
        acc = self.mgr.record_daily_close(
            acc_id=self.selected_account_id,
            close_price=close_p,
            buy_qty=buy_q,
            buy_price=buy_p,
            sell_qty=sell_q,
            sell_price=sell_p,
            memo=memo
        )
        if acc:
            self.load_account_detail(self.selected_account_id)
            curr_d = acc.get('current_date')
            messagebox.showinfo(
                "✔ 체결 정산 완료",
                f"[{acc.get('name')}] {curr_d} 장 마감 정산이 완료되었습니다!\n\n"
                f"• 당일 종가: ${close_p:.2f}\n"
                f"• 매수 체결: {buy_q:,}주 (@${buy_p:.2f})\n"
                f"• 매도 체결: {sell_q:,}주 (@${sell_p:.2f})\n\n"
                f"매매 일지 및 계좌 잔고가 실시간으로 갱신되었습니다.\n다음 거래일로 진행하려면 [▶ Next Day]를 누르세요."
            )

    def on_delete_last_day(self):
        """
        ⏪ 마지막 거래일 삭제 (Undo) 버튼 클릭 시:
        가장 최근 기록을 삭제하고 이전 거래일의 상태(잔고, 미매도 슬롯)로 안전하게 되돌립니다.
        """
        if not self.selected_account_id:
            messagebox.showinfo("알림", "먼저 계좌를 선택해주세요.")
            return

        accounts = self.mgr.load_accounts()
        acc = next((a for a in accounts if a['id'] == self.selected_account_id), None)
        if not acc:
            return

        records = acc.get('trade_records', [])
        if not records:
            messagebox.showinfo("알림", "삭제할 거래일 기록이 없습니다.")
            return

        last_date = records[-1].get('Date', '')

        if messagebox.askyesno(
            "⏪ 마지막 거래일 삭제 확인 (Undo)",
            f"가장 최근 거래일 [{last_date}]의 기록을 삭제하시겠습니까?\n\n"
            f"이 작업은 [{last_date}]의 종가, 매수/매도 체결을 취소하고\n"
            f"계좌 잔고와 미매도 슬롯을 직전 거래일 상태로 완전히 복구합니다.\n\n"
            f"정말 삭제하고 직전 거래일로 되돌리시겠습니까?"
        ):
            ok = self.mgr.delete_last_day_record(self.selected_account_id)
            if ok:
                self.load_account_detail(self.selected_account_id)
                messagebox.showinfo("롤백 완료", f"[{last_date}] 거래 기록이 삭제되고 직전 거래일 상태로 복구되었습니다.")

    def on_tree_log_double_click(self, event):
        """
        매매 일지 테이블의 특정 행을 더블클릭했을 때 수정 다이얼로그를 호출합니다.
        """
        if not self.selected_account_id:
            return

        selected = self.tree_log.selection()
        if not selected:
            return

        item = self.tree_log.item(selected[0])
        values = item.get('values', [])
        if not values:
            return

        date_str = str(values[0])
        accounts = self.mgr.load_accounts()
        acc = next((a for a in accounts if a['id'] == self.selected_account_id), None)
        if not acc:
            return

        record_data = next((r for r in acc.get('trade_records', []) if r.get('Date') == date_str), None)
        if not record_data:
            return

        EditTradeLogDialog(
            self,
            date_str=date_str,
            record_data=record_data,
            on_save_callback=self._on_edit_log_confirm
        )

    def _on_edit_log_confirm(self, date_str: str, updated_fields: dict):
        """
        일지 수정 다이얼로그에서 수정을 확정했을 때 계좌 일지를 갱신하고 잔고를 재계산합니다.
        """
        ok = self.mgr.update_trade_record(self.selected_account_id, date_str, updated_fields)
        if ok:
            self.load_account_detail(self.selected_account_id)
            messagebox.showinfo("수정 완료", f"[{date_str}] 거래 기록이 성공적으로 수정되었으며 누적 잔고가 재계산되었습니다.")
