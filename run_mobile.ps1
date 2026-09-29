# UTF-8 출력 인코딩 설정
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " 종종이 & 무한매수 안드로이드 모바일 UI 실행기 (Windows)" -ForegroundColor Yellow
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "스마트폰 화면 비율(412x860)로 모바일 UI 및 전 기능을 점검합니다.`n" -ForegroundColor Gray

$pythonPath = ".\.venv\Scripts\python.exe"
if (Test-Path $pythonPath) {
    & $pythonPath mobile_app.py
} else {
    python mobile_app.py
}
