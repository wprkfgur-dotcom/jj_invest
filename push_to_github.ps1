# GitHub 저장소(jj_invest) 푸시 스크립트
$ErrorActionPreference = "Stop"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  🚀 GitHub 저장소 푸시 시작 (jj_invest)" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

$gitCmd = Join-Path $env:LOCALAPPDATA "Programs\Git\cmd"
$gitBin = Join-Path $env:LOCALAPPDATA "Programs\Git\ucrt64\bin"
$env:Path = "$gitCmd;$gitBin;" + $env:Path

Write-Host "[1/2] 로컬 브랜치 상태 확인 중..." -ForegroundColor Yellow
git status --short
Write-Host ""

Write-Host "[2/2] GitHub로 푸시를 진행합니다 (origin/main)..." -ForegroundColor Yellow
Write-Host "      (브라우저 로그인 팝업 창이 열리면 [Sign in with your browser]를 눌러 승인해주세요)" -ForegroundColor DarkGray
Write-Host "--------------------------------------------------------" -ForegroundColor DarkGray

git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================================" -ForegroundColor Green
    Write-Host "  ✔ 축하합니다! GitHub 푸시가 성공적으로 완료되었습니다!" -ForegroundColor Green
    Write-Host "  저장소: https://github.com/wprkfgur-dotcom/jj_invest" -ForegroundColor Green
    Write-Host "========================================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "========================================================" -ForegroundColor Red
    Write-Host "  ❌ 푸시가 완료되지 않았습니다." -ForegroundColor Red
    Write-Host "  개인 액세스 토큰(PAT)을 사용하는 경우 아래 명령어로 직접 푸시할 수 있습니다:" -ForegroundColor Yellow
    Write-Host "  git remote set-url origin https://<YOUR_TOKEN>@github.com/wprkfgur-dotcom/jj_invest.git"
    Write-Host "  git push -u origin main"
    Write-Host "========================================================" -ForegroundColor Red
}
