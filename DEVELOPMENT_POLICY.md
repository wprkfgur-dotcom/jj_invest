# 종종이 & 무한매수 트레이더 - 개발 및 릴리스 정책 가이드

본 문서는 프로젝트의 일관된 개발 주기, 품질 검증, 버전 관리 및 GitHub Release 배포 규칙을 정리한 가이드입니다.

---

## 1. 개발 프로세스 (Development Workflow)

### 1.1 기본 개발 환경: Windows First
- 모든 기능 추가, UI 수정, 버그 패치는 **Windows 로컬 환경**을 기준으로 먼저 개발하고 테스트합니다.
- 빠른 디버깅과 즉각적인 피드백을 위해 아래 스크립트를 활용합니다:
  - **윈도우 데스크톱 GUI**: `run_gui.bat` (또는 `python run_gui.py`)
  - **모바일 화면 로컬 프리뷰**: `run_mobile.bat` (또는 `python mobile_app.py`)
- Python 콘솔 로그, 데이터 정산 로직, 구글 드라이브 동기화 등을 윈도우 환경에서 1차적으로 완벽하게 검증합니다.

### 1.2 안드로이드 빌드 및 검증 (Android Verification)
- 윈도우 환경에서의 수정 작업이 완전히 완료되면, 안드로이드 전용 ARM64 릴리스 APK를 빌드합니다.
- **빌드 명령어**:
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\build_arm64_release_apk.ps1
  ```
- **빌드 산출물 위치**: `dist\JongJongTrader_ARM64.apk`
- **실기기 설치 및 검증**:
  ```powershell
  adb install -r dist\JongJongTrader_ARM64.apk
  ```
- 모바일 화면 비율, 터치 이벤트, 알림/팝업, 파일 다운로드 등 모바일 고유 동작을 최종 확인합니다.

---

## 2. 릴리스 정책 (Release Workflow)

릴리스 시에는 **Git 소스 반영 + 앱 버전 업 + 릴리스 노트 업데이트 + GitHub Release APK 업로드**가 한 세트로 진행됩니다.

```
[개발 및 윈도우 테스트] ──> [안드로이드 빌드 & 기기 검증]
                                      │
                                      ▼
[버전 업 (core/app_update.py)] ──> [CHANGELOG.md 작성]
                                      │
                                      ▼
[Git Commit & Push (origin/main)] ──> [GitHub Releases 배포 (APK 첨부)]
```

### 단계별 절차:

#### 1) 버전 번호 증가 (Version Bump)
- [core/app_update.py](file:///c:/ai_development/core/app_update.py):
  - `APP_VERSION`: 새 버전 지정 (예: `2.0.0` -> `2.0.1` 또는 `2.1.0`)
  - `APP_BUILD_NAME`: 예: `"JongJong Trader v2.0.1 (ARM64 Release)"`
- [flet_apk_project/build/flutter/pubspec.yaml](file:///c:/ai_development/flet_apk_project/build/flutter/pubspec.yaml):
  - `version: 2.0.1+2` (버전 및 빌드 번호 일치)

#### 2) 릴리스 노트 작성 (Release Notes)
- [CHANGELOG.md](file:///c:/ai_development/CHANGELOG.md) 파일에 신규 버전에 대한 상세 변경 내역을 작성합니다.
  - 신규 기능 (Added)
  - 개선 사항 (Changed / Improved)
  - 버그 수정 (Fixed)

#### 3) Git 커밋 및 푸시
- 변경된 모든 소스 코드와 문서를 Git에 커밋하고 원격 저장소에 푸시합니다:
  ```powershell
  git add .
  git commit -m "릴리즈: vX.X.X - <요약 설명>"
  git push origin main
  ```

#### 4) 최신 APK 빌드 및 GitHub Releases 배포
- 최신 소스가 반영된 릴리스 APK를 빌드합니다:
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\build_arm64_release_apk.ps1
  ```
- 빌드된 APK를 GitHub Releases에 업로드하여 정식 배포합니다:
  ```powershell
  python tools\publish_github_release.py --tag vX.X.X
  ```
  *(해당 스크립트는 Git 자격 증명을 통해 GitHub Releases 태그 생성 및 `dist\JongJongTrader_ARM64.apk` 바이너리를 자동 업로드합니다.)*
- 배포가 완료되면 앱 실행 시 설정 화면의 **[업데이트 확인 / 다운로드]** 기능이 GitHub Releases API를 통해 최신 버전을 감지하고 원클릭 다운로드를 제공합니다.

---

## 3. 작업 환경 청결 원칙 (Workspace Cleanliness)

- **루트 디렉토리 바이너리 금지**:
  - `JongJongTrader*.apk`, `JongJongTrader*.exe` 등 컴파일된 실행 파일은 루트 디렉토리에 생성/방치하지 않고 오직 [dist/](file:///c:/ai_development/dist/) 폴더에서만 관리합니다.
- **임시 파일 정리**:
  - 디버깅용 임시 파일이나 스크래치 스크립트는 완료 후 정리합니다.
