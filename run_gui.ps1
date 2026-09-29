# =====================================================================
# 종종이 및 무한매수 자동매매 시스템 GUI 실행 스크립트 (PowerShell 전용)
# =====================================================================
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$PSScriptRoot = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition
Set-Location -Path $PSScriptRoot

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "🚀 [실행] 종종이 및 무한매수 자동매매 시스템 대시보드를 시작합니다..." -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Cyan

if (Test-Path ".\.venv\Scripts\python.exe") {
    & ".\.venv\Scripts\python.exe" "run_gui.py"
} else {
    python "run_gui.py"
}
