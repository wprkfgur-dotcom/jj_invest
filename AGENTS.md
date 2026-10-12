# JongJong Trader - Agent Guidelines & Policies

이 문서는 본 프로젝트(`jj_invest`)의 개발 및 릴리스 기본 지침입니다.

## 📌 핵심 원칙 요약

1. **배포 타깃 단일화 (Mobile First)**
   - 본 프로젝트의 최종 배포 대상은 **오직 2가지**입니다:
     1) **안드로이드 앱**: `dist\JongJongTrader_ARM64.apk`
     2) **윈도우 모바일 뷰 실행파일**: `dist\JongJongTrader_Mobile.exe`
   - *구 PC 데스크톱 버전(`JongJongTrader.exe`)은 폐기되었으며 더 이상 빌드하거나 관리하지 않습니다.*

2. **개발 및 윈도우 선검증 (Windows First Verification)**
   - 모든 기능 개발과 버그 수정은 **Windows 환경의 모바일 뷰를 기본으로** 진행합니다.
   - 로컬 테스트: `run_mobile.bat` (스마트폰 412x860 비율 윈도우 프리뷰 모드).
   - 기능 수정 완료 후 **AI의 자율 작업 범위**:
     - 테스트 검증: `python tools\run_app_tests.py`
     - **오직 윈도우 실행파일만 빌드**: `python build_mobile_exe.py` 실행하여 `dist\JongJongTrader_Mobile.exe` 생성
     - *주의: 사용자가 컨펌하기 전에는 APK 빌드 및 버전 번호 변경을 하지 않습니다.*

3. **단계별 릴리스 프로세스 (사용자 윈도우 확인 및 컨펌 후 배포)**
   - ⚠️ **핵심 원칙**: 
     - **1단계**: 기능 개발 및 버그 수정 완료 후 단위 테스트 통과 및 **윈도우 실행파일(`dist\JongJongTrader_Mobile.exe`)만 빌드**하여 사용자에게 확인 요청.
     - **2단계**: **사용자가 윈도우 실행파일로 직접 동작을 확인하고 최종 컨펌(승인)**.
     - **3단계 (컨펌 후)**: 
       - 버전 번호 증가 (`core/app_update.py`의 `APP_VERSION`, `APP_BUILD_NAME` 및 `pubspec.yaml`)
       - 안드로이드 APK 빌드 (`powershell -ExecutionPolicy Bypass -File .\build_arm64_release_apk.ps1`)
       - `CHANGELOG.md` 릴리스 노트 작성
       - Git 반영 (`origin/main` commit & push)
       - GitHub Releases 동시 배포 (`python tools\publish_github_release.py`)

4. **디렉토리 청결 (Clean Workspace)**
   - `.apk`, `.exe` 등 컴파일 바이너리는 프로젝트 루트에 두지 않고 반드시 `dist/`에만 유지합니다.

상세 정책 내용은 [DEVELOPMENT_POLICY.md](file:///c:/ai_development/DEVELOPMENT_POLICY.md) 및 [.agents/rules/dev-and-release-policy.md](file:///c:/ai_development/.agents/rules/dev-and-release-policy.md)를 참조하십시오.
