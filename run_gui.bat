@echo off
cd /d "%~dp0."
title Trading System GUI

echo =====================================================================
echo [RUN] Starting Trading System GUI...
echo =====================================================================

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run_gui.py
) else (
    python run_gui.py
)

pause
