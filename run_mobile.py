"""
종종 투자 모바일 UI 실행 스크립트 (Python Runner)
터미널에서 'python run_mobile.py'로 직접 실행할 수 있습니다.
"""
import sys
import os
import subprocess

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

os.environ["PYTHONIOENCODING"] = "utf-8"

current_dir = os.path.dirname(os.path.abspath(__file__))
venv_python = os.path.join(current_dir, ".venv", "Scripts", "python.exe")
target_script = os.path.join(current_dir, "mobile_app.py")

python_exe = venv_python if os.path.exists(venv_python) else sys.executable

print("=" * 55)
print("종종이 & 무한매수 모바일 UI 실행 중... (412x860)")
print("=" * 55)
print(f"• Python   : {python_exe}")
print(f"• Script   : {target_script}")
print("-" * 55)

try:
    subprocess.run([python_exe, target_script], check=True)
except KeyboardInterrupt:
    print("\n프로그램이 종료되었습니다.")
except Exception as e:
    print(f"\n[실행 오류] {e}")
