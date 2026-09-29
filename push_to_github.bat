@echo off
python push_to_github.py
if %ERRORLEVEL% neq 0 (
    .\.venv\Scripts\python.exe push_to_github.py
)
pause
