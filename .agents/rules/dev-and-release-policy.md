# 개발 및 릴리스 정책 (Development & Release Policy)

이 규칙은 `c:\ai_development` 프로젝트(종종이 & 무한매수 트레이더)의 개발, 검증, 릴리스 표준 프로세스를 정의합니다.
AI 어시스턴트는 모든 작업 시 이 원칙을 최우선으로 준수해야 합니다.

---

## 1. 배포 타깃 정책 (Target Platforms)
- 본 프로젝트의 공식 배포 타깃은 **오직 2가지**입니다:
  1. **안드로이드 릴리스 APK**: `dist\JongJongTrader_ARM64.apk`
  2. **윈도우 모바일 뷰 EXE**: `dist\JongJongTrader_Mobile.exe`
- **구 PC 데스크톱 버전(`JongJongTrader.exe`)은 폐기**되었으며, 더 이상 빌드하지 않고 관련 소스 코드(`run_gui.*`, `gui/tabs/*`, `gui/dialogs/*` 등)도 관리하지 않습니다.

---

## 2. 개발 및 검증 원칙 (Windows First -> Android Verification)

1. **개발은 윈도우(Windows) 모바일 뷰 환경을 기본으로 진행한다.**
   - 코드 작성, 기능 추가, UI 수정, 버그 패치 등 모든 작업은 로컬 Windows 환경에서 먼저 실행하고 디버깅합니다.
   - 실행 스크립트:
     - 모바일 UI 로컬 프리뷰: `run_mobile.bat` 또는 `python mobile_app.py`
   - 스마트폰 화면비(412x860) 프리뷰 창과 콘솔 로그 확인을 통해 로직 및 UI의 완전성을 1차 확보합니다.

2. **수정이 완료된 후 안드로이드(Android) 버전으로 빌드하여 검증한다.**
   - 윈도우에서의 동작이 정상임을 확인한 후, 모바일 소스를 동기화하고 APK를 빌드합니다.
   - 빌드 스크립트:
     ```powershell
     powershell -ExecutionPolicy Bypass -File .\build_arm64_release_apk.ps1
     ```
   - 산출물: `dist\JongJongTrader_ARM64.apk`에 생성 (루트 디렉토리에는 바이너리를 생성하지 않음).
   - 실제 연결된 안드로이드 기기(`adb install -r dist\JongJongTrader_ARM64.apk`)에서 터치 동작, 레이아웃 반응형 크기, 네트워크 호출 및 다운로드 팝업 등을 최종 검증합니다.

---

## 3. 릴리스 정책 (Release & Distribution Policy)

버전 릴리스(배포) 요청이 있을 때는 다음 절차를 단계별로 누락 없이 수행합니다.

### Step 1. 버전 번호 증가 (Version Bump - SemVer 규칙 준수)
- **버전 표기 체계 (`MAJOR.MINOR.PATCH`)**:
  - `MAJOR` (맨 앞 자리): 대규모 변경사항, 아키텍처 개편, 호환되지 않는 큰 변경 (예: `2.x.x` -> `3.0.0`)
  - `MINOR` (가운데 자리): 신규 전략/기능 추가 등 새로운 기능성 탑재 (예: `2.1.0` -> `2.2.0`)
  - `PATCH` (마지막 자리): 단순 버그 픽스 및 사소한 오류 수정 (예: `2.1.0` -> `2.1.1`)
1. `core/app_update.py`:
   - `APP_VERSION`: 지정된 규칙에 맞춰 버전 업 (예: 버그 수정 시 `2.1.1`, 기능 추가 시 `2.2.0`, 대규모 변경 시 `3.0.0`)
   - `APP_BUILD_NAME`: 예: `"JongJong Trader v2.1.1 (ARM64 & Windows Release)"`
2. `flet_apk_project/build/flutter/pubspec.yaml`:
   - `version: X.X.X+N` (버전 및 빌드 번호 일치)

### Step 2. 릴리스 노트 업데이트 (Release Notes)
1. `CHANGELOG.md` 파일에 신규 버전 섹션 추가:
   - 날짜, 버전 태그 (`vX.X.X`)
   - 추가된 기능 (New Features)
   - 버그 수정 (Bug Fixes)
   - 개선 및 최적화 (Improvements)
2. 작성된 내용은 GitHub Release 본문에도 그대로 반영.

### Step 3. Git 커밋 및 푸시 (Git Commit & Push)
- 모든 소스 코드 변경점 및 문서 업데이트를 Git에 커밋하고 원격 저장소(`origin/main`)에 푸시합니다.
  ```powershell
  git add .
  git commit -m "릴리즈: vX.X.X - <간략한 요약>"
  git push origin main
  ```

### Step 4. 안드로이드 APK 및 윈도우 모바일 EXE 동시 빌드 & 배포
1. 릴리스용 최신 안드로이드 APK 빌드:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\build_arm64_release_apk.ps1
   ```
2. 윈도우용 모바일 실행파일 빌드:
   ```powershell
   python build_mobile_exe.py
   ```
   *(산출물: `dist\JongJongTrader_Mobile.exe`)*
3. GitHub Releases 배포 스크립트 실행 (APK & EXE 동시 업로드):
   - 태그 생성 및 빌드된 `dist\JongJongTrader_ARM64.apk`와 `dist\JongJongTrader_Mobile.exe`를 함께 첨부하여 GitHub Release 생성:
     ```powershell
     python tools\publish_github_release.py --tag vX.X.X
     ```
   - 앱 내부의 원클릭 자동 업데이트(GitHub Releases API 연동)가 즉시 새 버전을 감지할 수 있도록 보장합니다.

---

## 4. 디렉토리 청결 유지 정책 (Clean Workspace)
- 컴파일된 `.apk`, `.exe` 등 대용량 실행 파일은 **절대로 프로젝트 루트 디렉토리에 두지 않습니다.**
- 모든 빌드 산출물은 반드시 `dist/` 폴더에만 위치해야 하며, Git 트래킹 대상에서 제외(`.gitignore`)됩니다.
- 임시 테스트 파일, 스크래치 스크립트는 작업 완료 후 즉시 삭제합니다.
