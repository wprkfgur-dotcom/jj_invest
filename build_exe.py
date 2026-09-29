import os
import sys
import subprocess
import shutil

print("=== Starting PyInstaller Build ===")

# Build command
cmd = [
    os.path.join(".venv", "Scripts", "pyinstaller.exe"),
    "--noconsole",
    "--onefile",
    "--name=JongJongTrader",
    "--clean",
    "--hidden-import=matplotlib",
    "--hidden-import=matplotlib.backends.backend_tkagg",
    "--hidden-import=pandas",
    "--hidden-import=numpy",
    "--hidden-import=openpyxl",
    "--hidden-import=yfinance",
    "--hidden-import=peewee",
    "--hidden-import=gui",
    "--hidden-import=gui.theme",
    "--hidden-import=gui.account_manager",
    "--hidden-import=gui.order_netting",
    "--hidden-import=gui.main_window",
    "--hidden-import=gui.dialogs.trade_entry_dialog",
    "--hidden-import=gui.tabs.accounts_tab",
    "--hidden-import=gui.tabs.today_order_tab",
    "--hidden-import=gui.tabs.backtest_tab",
    "--hidden-import=gui.tabs.trade_log_tab",
    "--hidden-import=strategies.jongjong",
    "--hidden-import=strategies.infinite_buying_v4",
    "--hidden-import=core.market_calendar",
    "--hidden-import=core.metrics",
    "--collect-data=matplotlib",
    "run_gui.py"
]

print("Running command:", " ".join(cmd))
res = subprocess.run(cmd)

if res.returncode == 0:
    print("\n=== Build SUCCESSFUL! ===")
    exe_path = os.path.join("dist", "JongJongTrader.exe")
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"Executable created: {exe_path} ({size_mb:.1f} MB)")
        
        # Also copy dist/JongJongTrader.exe to project root for easy access if desired
        target_root_exe = "JongJongTrader.exe"
        shutil.copy2(exe_path, target_root_exe)
        print(f"Copied executable to project root: {os.path.abspath(target_root_exe)}")
else:
    print(f"\n=== Build FAILED with code {res.returncode} ===")
    sys.exit(res.returncode)
