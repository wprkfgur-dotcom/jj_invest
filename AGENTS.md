# JongJong Trader - Agent Guidelines & Policies

이 문서는 본 프로젝트(`jj_invest`)의 개발 및 릴리스 기본 지침입니다.

## 📌 핵심 원칙 요약

1. **배포 타깃 단일화 (Mobile First)**
   - 본 프로젝트의 최종 배포 대상은 **오직 2가지**입니다:
     1) **안드로이드 앱**: `dist\JongJongTrader_ARM64.apk`
     2) **윈도우 모바일 뷰 실행파일**: `dist\JongJongTrader_Mobile.exe`
   - *구 PC 데스크톱 버전(`JongJongTrader.exe`)은 폐기되었으며 더 이상 빌드하거나 관리하지 않습니다.*

2. **개발 (Windows First)**
   - 모든 기능 개발과 버그 수정은 **Windows 환경의 모바일 뷰를 기본으로** 진행합니다.
   - 로컬 테스트: `run_mobile.bat` (스마트폰 412x860 비율 윈도우 프리뷰 모드).

3. **검증 (Android Verification)**
   - 윈도우에서의 수정/개선이 완전히 끝난 후, 안드로이드 전용 릴리스 APK를 빌드하여 검증합니다.
   - 빌드: `powershell -ExecutionPolicy Bypass -File .\build_arm64_release_apk.ps1`
   - 검증: 안드로이드 실기기(`adb install -r dist\JongJongTrader_ARM64.apk`)에서 실행, UI/터치, 업데이트 동작 확인.

4. **릴리스 (Release & Git Push)**
   - **버전 증가**: `core/app_update.py` (`APP_VERSION`, `APP_BUILD_NAME`) 및 `pubspec.yaml`
   - **릴리스 노트**: `CHANGELOG.md` 작성 및 GitHub Release 본문 반영
   - **Git 반영**: 작업된 모든 소스를 `origin/main`에 commit & push
   - **APK 배포**: GitHub Releases에 최신 태그(`vX.X.X`)로 `dist\JongJongTrader_ARM64.apk` 업로드 (`python tools\publish_github_release.py`)
   - **윈도우 실행파일 빌드**: `python build_mobile_exe.py` 실행하여 `dist\JongJongTrader_Mobile.exe` 생성.

5. **디렉토리 청결 (Clean Workspace)**
   - `.apk`, `.exe` 등 컴파일 바이너리는 프로젝트 루트에 두지 않고 반드시 `dist/`에만 유지합니다.

상세 정책 내용은 [DEVELOPMENT_POLICY.md](file:///c:/ai_development/DEVELOPMENT_POLICY.md) 및 [.agents/rules/dev-and-release-policy.md](file:///c:/ai_development/.agents/rules/dev-and-release-policy.md)를 참조하십시오.
