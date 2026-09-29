@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
title 종종 투자 모바일 앱 (JongJong Mobile)

echo ========================================================
echo  종종이 & 무한매수 안드로이드 모바일 UI 실행기 (Windows)
echo ========================================================
echo.
echo 스마트폰 화면 비율(412x860)로 모바일 UI 및 전 기능을 점검합니다.
echo.

if exist ".\.venv\Scripts\python.exe" (
    ".\.venv\Scripts\python.exe" mobile_app.py
) else (
    python mobile_app.py
)

if errorlevel 1 (
    echo.
    echo [오류] 프로그램 실행 중 문제가 발생했습니다.
    pause
)
