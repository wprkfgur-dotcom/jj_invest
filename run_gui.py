"""
=====================================================================
종종이 & 무한매수 주식 매매 자동화 시스템 GUI 실행기 (Runner)
=====================================================================
실행 방법:
  python run_gui.py
또는
  run_gui.bat 더블 클릭
"""
import sys
import os
import tkinter as tk

# 윈도우 콘솔 UTF-8 인코딩 대응
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 현재 디렉터리를 모듈 탐색 경로에 추가
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from gui.main_window import TradingAppWindow


def main():
    try:
        root = tk.Tk()
        app = TradingAppWindow(root)
        root.mainloop()
    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        try:
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("실행 오류", f"프로그램 실행 중 예기치 않은 오류가 발생했습니다:\n\n{err_msg}")
        except Exception:
            pass
        try:
            exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else CURRENT_DIR
            with open(os.path.join(exe_dir, "error.log"), "w", encoding="utf-8") as f:
                f.write(err_msg)
        except Exception:
            pass


if __name__ == "__main__":
    main()
