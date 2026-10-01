"""
Google Drive 클라우드 실시간 동기화 설정 대화상자 (데스크톱 Tkinter GUI)
Google Apps Script Web App 연동을 통해 멀티 디바이스(폰, 태블릿, PC) 간 계좌를 실시간 동기화합니다.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading

from gui.theme import COLORS, FONTS
from core.cloud_sync import (
    get_sync_config, save_sync_config, is_sync_enabled,
    test_connection, upload_accounts_to_drive, download_accounts_from_drive,
    sync_local_with_drive, get_gas_script_code
)


class CloudSyncDialog(tk.Toplevel):
    def __init__(self, parent, account_manager, on_sync_done_callback=None):
        super().__init__(parent)
        self.title("☁️ Google Drive 클라우드 실시간 동기화")
        self.geometry("560x520")
        self.resizable(False, False)
        self.configure(bg=COLORS['bg_card'])
        self.transient(parent)
        self.grab_set()

        self.am = account_manager
        self.on_sync_done_callback = on_sync_done_callback
        self.cfg = get_sync_config()

        self._build_ui()

    def _build_ui(self):
        container = ttk.Frame(self, style='Card.TFrame', padding=20)
        container.pack(fill='both', expand=True)

        # 1. 헤더
        lbl_title = ttk.Label(container, text="☁️ Google Drive 실시간 계좌 동기화", style='Title.TLabel', font=FONTS['subtitle'])
        lbl_title.pack(anchor='w', pady=(0, 4))

        lbl_desc = ttk.Label(
            container,
            text="스마트폰, 태블릿, PC 등 여러 기기에서 동일한 구글 드라이브 폴더('JongJongTrader')를\n"
                 "통해 계좌 데이터를 실시간으로 자동 동기화합니다.",
            style='CardMuted.TLabel', font=FONTS['caption']
        )
        lbl_desc.pack(anchor='w', pady=(0, 14))

        # 2. 동기화 ON / OFF 스위치 (체크박스)
        self.var_sync_on = tk.BooleanVar(value=self.cfg.get("sync_enabled", False))
        chk_frame = ttk.Frame(container, style='CardAlt.TFrame', padding=10)
        chk_frame.pack(fill='x', pady=(0, 12))

        chk_sync = ttk.Checkbutton(
            chk_frame,
            text="Google Drive 실시간 동기화 활성화 (Sync ON)",
            variable=self.var_sync_on,
            command=self._on_toggle_sync
        )
        chk_sync.pack(side='left')

        # 3. URL 입력 폼
        url_frame = ttk.LabelFrame(container, text=" 🔗 Google Apps Script 웹 앱 URL ", padding=10)
        url_frame.pack(fill='x', pady=(0, 12))

        self.entry_url = ttk.Entry(url_frame, width=50)
        self.entry_url.insert(0, self.cfg.get("web_app_url", ""))
        self.entry_url.pack(side='left', fill='x', expand=True, padx=(0, 8))

        btn_save_url = ttk.Button(url_frame, text="URL 저장", style='TButton', command=self._on_save_url)
        btn_save_url.pack(side='left', padx=(0, 4))

        btn_test = ttk.Button(url_frame, text="연결 테스트", style='Primary.TButton', command=self._on_test_conn)
        btn_test.pack(side='left')

        # 4. 상태 표시 영역
        self.lbl_status = ttk.Label(
            container,
            text=self._get_status_text(),
            style='Card.TLabel',
            font=FONTS['caption']
        )
        self.lbl_status.pack(anchor='w', pady=(0, 14))

        # 5. 동기화 실행 버튼 그룹
        btn_box = ttk.Frame(container, style='Card.TFrame')
        btn_box.pack(fill='x', pady=(0, 14))

        btn_sync_now = ttk.Button(btn_box, text="🔄 지금 즉시 동기화", style='Success.TButton', command=self._on_sync_now)
        btn_sync_now.pack(side='left', fill='x', expand=True, padx=(0, 4))

        btn_upload = ttk.Button(btn_box, text="⬆ 드라이브로 올리기 (백업)", style='TButton', command=self._on_force_upload)
        btn_upload.pack(side='left', fill='x', expand=True, padx=(0, 4))

        btn_download = ttk.Button(btn_box, text="⬇ 드라이브에서 받기 (복원)", style='TButton', command=self._on_force_download)
        btn_download.pack(side='left', fill='x', expand=True)

        # 6. 스크립트 복사 및 안내 버튼
        guide_frame = ttk.Frame(container, style='CardAlt.TFrame', padding=10)
        guide_frame.pack(fill='x', pady=(0, 10))

        ttk.Label(
            guide_frame,
            text="💡 처음 사용하시나요? 1분 만에 구글 드라이브에 스크립트를 배포하여 바로 시작할 수 있습니다.",
            style='CardMuted.TLabel', font=FONTS['caption']
        ).pack(anchor='w', pady=(0, 6))

        btn_copy_gas = ttk.Button(
            guide_frame,
            text="📋 Google Apps Script 코드 전체 복사",
            style='Primary.TButton',
            command=self._on_copy_gas_code
        )
        btn_copy_gas.pack(anchor='w')

        # 7. 닫기 버튼
        btn_close = ttk.Button(container, text="닫기", style='TButton', command=self.destroy)
        btn_close.pack(anchor='e', pady=(10, 0))

    def _get_status_text(self) -> str:
        cfg = get_sync_config()
        en = cfg.get("sync_enabled", False)
        u = cfg.get("web_app_url", "")
        t = cfg.get("last_sync_time") or "기록 없음"
        m = cfg.get("last_sync_message") or ""
        st = "작동 중 (Sync ON)" if (en and u) else "비활성화 (Sync OFF)"
        return f"• 상태: {st}\n• 최근 동기화: {t} ({m})\n• 드라이브 폴더: Google Drive / JongJongTrader / accounts.json"

    def _refresh_status(self):
        self.lbl_status.config(text=self._get_status_text())

    def _on_toggle_sync(self):
        val = self.var_sync_on.get()
        u = self.entry_url.get().strip()
        if val and (not u or not u.startswith("http")):
            self.var_sync_on.set(False)
            messagebox.showwarning("입력 필요", "Google Apps Script 웹 앱 URL을 먼저 입력해주세요.", parent=self)
            return

        cfg = get_sync_config()
        cfg["sync_enabled"] = val
        cfg["web_app_url"] = u
        save_sync_config(cfg)
        self._refresh_status()

        if val:
            messagebox.showinfo("동기화 가동", "Google Drive 실시간 동기화가 활성화되었습니다!", parent=self)
            self._on_sync_now()
        else:
            messagebox.showinfo("동기화 중지", "Google Drive 동기화가 비활성화되었습니다. (로컬 단독 저장)", parent=self)

    def _on_save_url(self):
        u = self.entry_url.get().strip()
        if not u or not u.startswith("http"):
            messagebox.showwarning("URL 오류", "올바른 URL(https://...)을 입력하세요.", parent=self)
            return
        cfg = get_sync_config()
        cfg["web_app_url"] = u
        save_sync_config(cfg)
        self._refresh_status()
        messagebox.showinfo("저장 완료", "Google Apps Script 웹 앱 URL이 저장되었습니다.", parent=self)

    def _on_test_conn(self):
        u = self.entry_url.get().strip()
        if not u or not u.startswith("http"):
            messagebox.showwarning("URL 오류", "URL을 먼저 입력하세요.", parent=self)
            return
        ok, msg = test_connection(u)
        if ok:
            messagebox.showinfo("연결 성공", msg, parent=self)
        else:
            messagebox.showerror("연결 실패", msg, parent=self)

    def _on_sync_now(self):
        if not is_sync_enabled():
            messagebox.showwarning("동기화 꺼짐", "먼저 'Google Drive 실시간 동기화 활성화'를 체크해주세요.", parent=self)
            return
        ok, msg = sync_local_with_drive(self.am)
        self._refresh_status()
        if ok:
            messagebox.showinfo("동기화 완료", msg, parent=self)
            if self.on_sync_done_callback:
                self.on_sync_done_callback()
        else:
            messagebox.showerror("동기화 오류", msg, parent=self)

    def _on_force_upload(self):
        u = self.entry_url.get().strip()
        if not u or not u.startswith("http"):
            messagebox.showwarning("URL 오류", "웹 앱 URL을 먼저 입력하세요.", parent=self)
            return
        accs = self.am.load_accounts()
        ok, msg = upload_accounts_to_drive(accs, u)
        self._refresh_status()
        if ok:
            messagebox.showinfo("업로드 완료", f"구글 드라이브로 계좌 백업 완료 ({len(accs)}개 계좌)", parent=self)
        else:
            messagebox.showerror("업로드 실패", msg, parent=self)

    def _on_force_download(self):
        u = self.entry_url.get().strip()
        if not u or not u.startswith("http"):
            messagebox.showwarning("URL 오류", "웹 앱 URL을 먼저 입력하세요.", parent=self)
            return
        ok, drive_accs, msg = download_accounts_from_drive(u)
        self._refresh_status()
        if ok and drive_accs is not None:
            self.am.save_accounts(drive_accs, skip_cloud_sync=True)
            messagebox.showinfo("다운로드 완료", f"구글 드라이브에서 {len(drive_accs)}개 계좌를 복원했습니다!", parent=self)
            if self.on_sync_done_callback:
                self.on_sync_done_callback()
        else:
            messagebox.showerror("다운로드 실패", msg, parent=self)

    def _on_copy_gas_code(self):
        code = get_gas_script_code()
        self.clipboard_clear()
        self.clipboard_append(code)
        messagebox.showinfo(
            "클립보드 복사 완료",
            "Google Apps Script 코드가 클립보드에 복사되었습니다!\n\n"
            "[1분 연동 방법]\n"
            "1. drive.google.com 접속\n"
            "2. '+ 새로 만들기' -> '더보기' -> 'Google Apps Script' 생성\n"
            "3. 복사한 코드를 모두 붙여넣기\n"
            "4. 우측 상단 [배포] -> [새 배포] -> [웹 앱] 선택\n"
            "   (액세스 권한: '모든 사용자(Anyone)' 선택 필수!)\n"
            "5. 발급된 URL을 앱에 붙여넣고 동기화 ON!",
            parent=self
        )
