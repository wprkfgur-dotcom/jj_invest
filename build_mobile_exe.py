"""
mobile_app.py -> JongJongTrader_Mobile.exe 빌드 스크립트
flet pack (PyInstaller 기반) 사용
"""
import os
import sys
import subprocess
import shutil

# UTF-8 출력 설정
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

os.environ["PYTHONIOENCODING"] = "utf-8"

print("=" * 55)
print("  JongJong Trader Mobile -> EXE 빌드 시작")
print("=" * 55)

current_dir = os.path.dirname(os.path.abspath(__file__))
flet_exe = os.path.join(current_dir, ".venv", "Scripts", "flet.exe")
target_script = os.path.join(current_dir, "mobile_app.py")

if not os.path.exists(flet_exe):
    print(f"[오류] flet.exe 를 찾을 수 없습니다: {flet_exe}")
    sys.exit(1)

if not os.path.exists(target_script):
    print(f"[오류] mobile_app.py 를 찾을 수 없습니다: {target_script}")
    sys.exit(1)

print(f"  flet    : {flet_exe}")
print(f"  소스    : {target_script}")
print(f"  출력    : dist/JongJongTrader_Mobile.exe")
print("-" * 55)

# flet pack 명령 실행
cmd = [
    flet_exe,
    "pack",
    "--name", "JongJongTrader_Mobile",
    "--product-name", "JongJong Trader",
    "--product-version", "2.0.0",
    "--file-version", "2.0.0.0",
    target_script,
    "--",
    "--noconsole",
    "--clean",
    "--hidden-import=flet",
    "--hidden-import=flet_core",
    "--hidden-import=pandas",
    "--hidden-import=numpy",
    "--hidden-import=yfinance",
    "--hidden-import=requests",
    "--hidden-import=urllib3",
    "--hidden-import=certifi",
    "--hidden-import=charset_normalizer",
]

print("실행 중... (수 분 소요될 수 있습니다)")
env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"

res = subprocess.run(cmd, env=env, cwd=current_dir)

if res.returncode == 0:
    print("\n" + "=" * 55)
    print("  빌드 성공!")
    print("=" * 55)
    exe_path = os.path.join(current_dir, "dist", "JongJongTrader_Mobile.exe")
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"  EXE 경로 : {exe_path}")
        print(f"  크기     : {size_mb:.1f} MB")
        root_exe = os.path.join(current_dir, "JongJongTrader_Mobile.exe")
        shutil.copy2(exe_path, root_exe)
        print(f"  루트 복사 : {root_exe}")
    else:
        print("  [경고] dist 폴더에서 EXE를 찾지 못했습니다.")
else:
    print(f"\n[빌드 실패] 종료 코드: {res.returncode}")
    sys.exit(res.returncode)
