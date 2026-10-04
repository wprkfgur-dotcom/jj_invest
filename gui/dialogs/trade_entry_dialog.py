"""
당일 종가 및 체결 정산 입력 다이얼로그 (Record Close & Fill Dialog)
및 매매 기록 수정 다이얼로그 (Edit Trade Log Dialog)
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable

from gui.theme import COLORS, FONTS


class RecordCloseDialog(tk.Toplevel):
    """
    미국 주식 시장 마감 후 당일 종가를 입력하고,
    LOC 주문 체결 여부를 자동 분석한 뒤 사용자가 실제 체결 수량을 직접 수정/확정하는 다이얼로그
    """

    def __init__(self, parent, account: dict, today_orders: dict, on_success_callback: Callable):
        super().__init__(parent)
        self.account = account
        self.today_orders = today_orders
        self.on_success_callback = on_success_callback

        current_date = account.get('current_date', '오늘')
        self.title(f"🏁 [{account.get('name', '계좌')}] {current_date} 종가 & LOC 체결 정산")
        self.geometry("560x650")
        self.resizable(False, False)
        self.configure(bg=COLORS['bg_card'])
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        curr_d = self.account.get('current_date', '-')
        ticker = self.account.get('ticker', 'SOXL')
        last_price = float(self.today_orders.get('last_price', 0.0))
        if last_price <= 0:
            last_price = float(self.account.get('current_price', 0.0))
        if last_price <= 0:
            recs = self.account.get('trade_records', [])
            if recs:
                last_price = float(recs[-1].get('Close', 0.0))
        mode = self.today_orders.get('mode', self.account.get('mode', 'Normal'))

        # 1. 헤더 타이틀
        top_frame = ttk.Frame(self, style='Card.TFrame', padding=(20, 14, 20, 8))
        top_frame.pack(fill='x')

        ttk.Label(top_frame, text=f"🏁 {curr_d} 장 마감 체결 정산", style='Title.TLabel', font=FONTS['subtitle']).pack(anchor='w')
        ttk.Label(top_frame, text=f"종목: {ticker} | 직전 종가: ${last_price:.2f} | 현재 모드: {mode} | 전략: {self.account.get('strategy', '')}", 
                  style='CardMuted.TLabel', font=FONTS['caption']).pack(anchor='w', pady=(2, 0))

        # 2. 메인 입력 폼
        form = ttk.Frame(self, style='CardAlt.TFrame', padding=16)
        form.pack(fill='both', expand=True, padx=20, pady=8)

        # (1) 당일 미국장 종가 입력
        row0 = ttk.Frame(form, style='CardAlt.TFrame')
        row0.pack(fill='x', pady=(0, 10))

        ttk.Label(row0, text="당일 미국장 종가 ($):", style='KPIVal.TLabel', font=FONTS['body_bold']).pack(side='left')
        self.close_var = tk.StringVar(value=f"{last_price:.2f}" if last_price > 0 else "")
        self.entry_close = ttk.Entry(row0, textvariable=self.close_var, font=('Segoe UI', 13, 'bold'), width=14)
        self.entry_close.pack(side='left', padx=(10, 8))
        self.close_var.trace_add('write', lambda *args: self._on_close_price_changed())
        self.entry_close.bind('<Return>', lambda e: self._on_close_price_changed())

        btn_calc = ttk.Button(row0, text="⚡ 체결 자동 계산", style='Primary.TButton', command=self._on_close_price_changed)
        btn_calc.pack(side='left')

        # (2) LOC 주문 체결 자동 분석 결과 요약창
        preview_box = ttk.LabelFrame(form, text="  📊 LOC 주문 자동 체결 분석  ", padding=10)
        preview_box.pack(fill='x', pady=6)

        self.lbl_analysis_sell = ttk.Label(preview_box, text="• 매도 체결: 분석 대기 중...", font=FONTS['caption'], foreground=COLORS['accent_yellow'])
        self.lbl_analysis_sell.pack(anchor='w', pady=2)

        self.lbl_analysis_buy = ttk.Label(preview_box, text="• 매수 체결: 분석 대기 중...", font=FONTS['caption'], foreground=COLORS['accent_green'])
        self.lbl_analysis_buy.pack(anchor='w', pady=2)

        # (3) 실제 체결 수량 및 단가 입력 (사용자 직접 수정 가능)
        edit_box = ttk.LabelFrame(form, text="  ✍ 실제 증권사 체결 내역 확인 및 수정  ", padding=12)
        edit_box.pack(fill='x', pady=8)

        # 매수 체결
        r_buy = ttk.Frame(edit_box)
        r_buy.pack(fill='x', pady=4)
        ttk.Label(r_buy, text="실제 매수 체결 수량:", width=18, font=FONTS['body_bold']).pack(side='left')
        self.entry_buy_qty = ttk.Entry(r_buy, width=12, font=FONTS['body'])
        self.entry_buy_qty.insert(0, "0")
        self.entry_buy_qty.pack(side='left', padx=(4, 16))

        ttk.Label(r_buy, text="매수 체결 단가 ($):", width=16).pack(side='left')
        self.entry_buy_price = ttk.Entry(r_buy, width=12, font=FONTS['body'])
        self.entry_buy_price.insert(0, f"{last_price:.2f}")
        self.entry_buy_price.pack(side='left', padx=4)

        # 매도 체결 (자동 체결 / 수정 불가)
        r_sell = ttk.Frame(edit_box)
        r_sell.pack(fill='x', pady=4)
        ttk.Label(r_sell, text="실제 매도 체결 수량 (자동):", width=22, font=FONTS['body_bold']).pack(side='left')
        self.entry_sell_qty = ttk.Entry(r_sell, width=12, font=FONTS['body'], state='readonly')
        self.entry_sell_qty.pack(side='left', padx=(4, 16))

        ttk.Label(r_sell, text="매도 체결 단가 ($):", width=16).pack(side='left')
        self.entry_sell_price = ttk.Entry(r_sell, width=12, font=FONTS['body'], state='readonly')
        self.entry_sell_price.pack(side='left', padx=4)

        # 비고 / 메모
        r_memo = ttk.Frame(edit_box)
        r_memo.pack(fill='x', pady=(6, 2))
        ttk.Label(r_memo, text="거래 메모 / 비고:", width=18).pack(side='left')
        self.entry_memo = ttk.Entry(r_memo, width=42, font=FONTS['body'])
        self.entry_memo.pack(side='left', padx=4)

        # 안내 문구
        ttk.Label(form, text="💡 LOC 주문은 종가가 주문가 이하일 때 매수, 주문가 이상일 때 매도 체결됩니다.\n실제 증권사 체결량과 차이가 있을 경우 위 수량을 직접 수정하세요.", 
                  foreground=COLORS['text_muted'], font=FONTS['caption']).pack(anchor='w', pady=(6, 0))

        # 3. 버튼 박스
        btn_box = ttk.Frame(self, style='Card.TFrame', padding=(20, 8, 20, 16))
        btn_box.pack(fill='x', side='bottom')

        btn_cancel = ttk.Button(btn_box, text="취소", command=self.destroy)
        btn_cancel.pack(side='right', padx=(8, 0))

        btn_confirm = ttk.Button(btn_box, text="✔ 체결 확정 및 일지 저장", style='Success.TButton', command=self._confirm)
        btn_confirm.pack(side='right')

        # 최초 실행 시 자동 체결 분석 1회 가동
        self.after(50, self._on_close_price_changed)

    def _on_close_price_changed(self):
        val_str = self.close_var.get().replace('$', '').replace(',', '').strip() if hasattr(self, 'close_var') else self.entry_close.get().replace('$', '').replace(',', '').strip()
        try:
            close_p = float(val_str)
        except ValueError:
            self.lbl_analysis_sell.config(text="• 매도 체결: 종가를 입력하세요...", foreground=COLORS['text_muted'])
            self.lbl_analysis_buy.config(text="• 매수 체결: 종가를 입력하세요...", foreground=COLORS['text_muted'])
            return

        if close_p <= 0:
            self.lbl_analysis_sell.config(text="• 매도 체결: 0보다 큰 종가를 입력하세요...", foreground=COLORS['text_muted'])
            self.lbl_analysis_buy.config(text="• 매수 체결: 0보다 큰 종가를 입력하세요...", foreground=COLORS['text_muted'])
            return

        try:
            sell_orders = self.today_orders.get('sell_orders', [])
            buy_orders = self.today_orders.get('buy_orders', [])

            # 1. 미매도 슬롯들의 개별 목표가(U) 도달 여부 정밀 분석
            records = self.account.get('trade_records', [])
            unsold_lots = [r for r in records if r.get('R', 0) > 0 and not r.get('Sold', False)]

            target_reached_lots = []
            for lot in unsold_lots:
                u_p = float(lot.get('U', 0.0)) if lot.get('U') is not None else 0.0
                if u_p <= 0:
                    bp = float(lot.get('BuyPrice', lot.get('Close', close_p)))
                    u_p = round(bp * 1.0275, 2)
                h_days = len(records) - 1 - int(lot.get('t', 0))
                is_moc = (h_days >= 10)
                is_reached = (close_p >= u_p - 1e-4)
                if is_moc or is_reached:
                    target_reached_lots.append((lot, is_moc, u_p))

            auto_sell_qty = 0
            filled_sells = []
            # 목표가 도달 및 만기 슬롯들을 매도 체결 목록에 추가
            for lot, is_moc, u_p in target_reached_lots:
                q = int(lot['R'])
                auto_sell_qty += q
                if is_moc:
                    filled_sells.append(f"{lot.get('Date', '')} 만기로트({q}주@MOC)")
                else:
                    filled_sells.append(f"{lot.get('Date', '')} 로트({q}주@목표${u_p:.2f})")

            # 2. 매수 체결 분석
            auto_buy_qty = 0
            filled_buys = []
            for b in buy_orders:
                p = float(b.get('price', 0.0))
                q = int(b.get('qty', 0))
                if p > 0 and q > 0:
                    # 종가 <= 주문가 이면 LOC 매수 체결
                    if close_p <= p + 1e-4:
                        auto_buy_qty += q
                        filled_buys.append(f"{b.get('호가단계', '매수')}({q}주@${p:.2f})")

            # 퉁치기 모드에서 퉁치기 슬롯(최저 목표가 슬롯)이 익절 체결된 경우:
            # 퉁치기 상계 원리에 따라 당일 1회분 매수도 함께 체결됨
            netting_info = self.today_orders.get('netting_info', {})
            reached_lots_raw = [t[0] for t in target_reached_lots]
            if netting_info.get('is_netted') and auto_buy_qty == 0 and unsold_lots:
                min_u_lot = min(unsold_lots, key=lambda x: float(x.get('U', 999999.0)))
                if min_u_lot in reached_lots_raw:
                    tung_q = int(min_u_lot['R'])
                    auto_buy_qty = tung_q
                    filled_buys.append(f"퉁치기 상계 순매수({tung_q}주@${close_p:.2f})")

            # 분석 텍스트 갱신
            if filled_sells:
                self.lbl_analysis_sell.config(
                    text=f"• 매도 체결: 총 {auto_sell_qty:,}주 체결 [ {', '.join(filled_sells)} ]",
                    foreground=COLORS['accent_red']
                )
            else:
                self.lbl_analysis_sell.config(
                    text="• 매도 체결: 체결 조건 미달 (0주 매도)",
                    foreground=COLORS['text_muted']
                )

            if filled_buys:
                self.lbl_analysis_buy.config(
                    text=f"• 매수 체결: 총 {auto_buy_qty:,}주 체결 [ {', '.join(filled_buys)} ]",
                    foreground=COLORS['accent_green']
                )
            else:
                self.lbl_analysis_buy.config(
                    text="• 매수 체결: 체결 조건 미달 (0주 매수)",
                    foreground=COLORS['text_muted']
                )

            # 입력 필드 기본값 갱신
            self.entry_buy_qty.delete(0, 'end')
            self.entry_buy_qty.insert(0, str(auto_buy_qty))

            self.entry_buy_price.delete(0, 'end')
            self.entry_buy_price.insert(0, f"{close_p:.2f}")

            self.entry_sell_qty.config(state='normal')
            self.entry_sell_qty.delete(0, 'end')
            self.entry_sell_qty.insert(0, str(auto_sell_qty))
            self.entry_sell_qty.config(state='readonly')

            self.entry_sell_price.config(state='normal')
            self.entry_sell_price.delete(0, 'end')
            self.entry_sell_price.insert(0, f"{close_p:.2f}")
            self.entry_sell_price.config(state='readonly')
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.lbl_analysis_buy.config(
                text=f"• 분석 안내: 체결 분석 중 오류 ({e})",
                foreground=COLORS['accent_yellow']
            )

    def _confirm(self):
        try:
            close_p = float(self.entry_close.get().replace('$', '').replace(',', '').strip())
            buy_q = int(self.entry_buy_qty.get().replace(',', '').strip())
            buy_p = float(self.entry_buy_price.get().replace('$', '').replace(',', '').strip())
            sell_q = int(self.entry_sell_qty.get().replace(',', '').strip())
            sell_p = float(self.entry_sell_price.get().replace('$', '').replace(',', '').strip())
            memo = self.entry_memo.get().strip()
        except ValueError:
            messagebox.showwarning("입력 오류", "숫자 형식이 올바르지 않습니다. 다시 확인해주세요.", parent=self)
            return

        if close_p <= 0:
            messagebox.showwarning("입력 오류", "종가는 0보다 커야 합니다.", parent=self)
            return

        if buy_q < 0 or sell_q < 0:
            messagebox.showwarning("입력 오류", "수량은 0 이상이어야 합니다.", parent=self)
            return

        # 콜백 호출
        self.on_success_callback(close_p, buy_q, buy_p, sell_q, sell_p, memo)
        self.destroy()


class EditTradeLogDialog(tk.Toplevel):
    """
    기존 매매 기록의 특정 거래일 행을 더블클릭하여 내용을 수정하는 다이얼로그
    """

    def __init__(self, parent, date_str: str, record_data: dict, on_save_callback: Callable):
        super().__init__(parent)
        self.date_str = date_str
        self.record_data = record_data
        self.on_save_callback = on_save_callback

        self.title(f"✏ [{date_str}] 매매 기록 수정")
        self.geometry("460x480")
        self.resizable(False, False)
        self.configure(bg=COLORS['bg_card'])
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        top_frame = ttk.Frame(self, style='Card.TFrame', padding=(20, 14, 20, 8))
        top_frame.pack(fill='x')

        ttk.Label(top_frame, text=f"✏ {self.date_str} 매매 기록 수정", style='Title.TLabel', font=FONTS['subtitle']).pack(anchor='w')
        ttk.Label(top_frame, text="수정된 내용은 계좌 잔고 및 이후 누적 지표에 즉시 반영됩니다.", 
                  style='CardMuted.TLabel', font=FONTS['caption']).pack(anchor='w', pady=(2, 0))

        form = ttk.Frame(self, style='CardAlt.TFrame', padding=16)
        form.pack(fill='both', expand=True, padx=20, pady=8)

        # 1. 종가
        r1 = ttk.Frame(form)
        r1.pack(fill='x', pady=6)
        ttk.Label(r1, text="당일 종가 ($):", width=18, font=FONTS['body_bold']).pack(side='left')
        self.entry_close = ttk.Entry(r1, width=16, font=FONTS['body'])
        self.entry_close.insert(0, f"{float(self.record_data.get('Close', 0.0)):.2f}")
        self.entry_close.pack(side='left')

        # 2. 매수 수량
        r2 = ttk.Frame(form)
        r2.pack(fill='x', pady=6)
        ttk.Label(r2, text="매수 수량 (주):", width=18, font=FONTS['body_bold']).pack(side='left')
        self.entry_buy_qty = ttk.Entry(r2, width=16, font=FONTS['body'])
        self.entry_buy_qty.insert(0, str(int(self.record_data.get('BuyQty', self.record_data.get('R', 0)))))
        self.entry_buy_qty.pack(side='left')

        # 3. 매수 단가
        r3 = ttk.Frame(form)
        r3.pack(fill='x', pady=6)
        ttk.Label(r3, text="매수 단가 ($):", width=18).pack(side='left')
        self.entry_buy_price = ttk.Entry(r3, width=16, font=FONTS['body'])
        b_p = self.record_data.get('BuyPrice', self.record_data.get('Close', 0.0))
        self.entry_buy_price.insert(0, f"{float(b_p):.2f}")
        self.entry_buy_price.pack(side='left')

        # 4. 실현 손익
        r4 = ttk.Frame(form)
        r4.pack(fill='x', pady=6)
        ttk.Label(r4, text="실현 손익 ($):", width=18, font=FONTS['body_bold']).pack(side='left')
        self.entry_profit = ttk.Entry(r4, width=16, font=FONTS['body'])
        self.entry_profit.insert(0, f"{float(self.record_data.get('Profit', 0.0)):.2f}")
        self.entry_profit.pack(side='left')

        # 5. 메모
        r5 = ttk.Frame(form)
        r5.pack(fill='x', pady=6)
        ttk.Label(r5, text="비고 / 메모:", width=18).pack(side='left')
        self.entry_memo = ttk.Entry(r5, width=24, font=FONTS['body'])
        self.entry_memo.insert(0, str(self.record_data.get('Memo', '')))
        self.entry_memo.pack(side='left')

        # 버튼
        btn_box = ttk.Frame(self, style='Card.TFrame', padding=(20, 8, 20, 16))
        btn_box.pack(fill='x', side='bottom')

        btn_cancel = ttk.Button(btn_box, text="취소", command=self.destroy)
        btn_cancel.pack(side='right', padx=(8, 0))

        btn_save = ttk.Button(btn_box, text="수정 완료 및 재계산", style='Success.TButton', command=self._save)
        btn_save.pack(side='right')

    def _save(self):
        try:
            close_p = float(self.entry_close.get().replace('$', '').replace(',', '').strip())
            buy_q = int(self.entry_buy_qty.get().replace(',', '').strip())
            buy_p = float(self.entry_buy_price.get().replace('$', '').replace(',', '').strip())
            profit = float(self.entry_profit.get().replace('$', '').replace(',', '').strip())
            memo = self.entry_memo.get().strip()
        except ValueError:
            messagebox.showwarning("입력 오류", "숫자 형식이 올바르지 않습니다.", parent=self)
            return

        updated = {
            'Close': close_p,
            'BuyQty': buy_q,
            'R': buy_q,
            'BuyPrice': buy_p,
            'Profit': profit,
            'Memo': memo
        }
        self.on_save_callback(self.date_str, updated)
        self.destroy()
