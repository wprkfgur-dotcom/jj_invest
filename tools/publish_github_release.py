"""
GitHub Releases 배포 및 APK 업로드 자동화 스크립트
"""
import os
import sys
import json
import urllib.request
import urllib.error
import subprocess

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


REPO = "wprkfgur-dotcom/jj_invest"
DEFAULT_TAG = "v2.1.0"
DEFAULT_FILES = [
    r"C:\ai_development\dist\JongJongTrader_ARM64.apk",
    r"C:\ai_development\dist\JongJongTrader_Mobile.exe"
]


def get_github_token() -> str:
    """Git Credential Manager에서 GitHub 액세스 토큰을 획득합니다."""
    try:
        p = subprocess.Popen(['git', 'credential', 'fill'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        out, _ = p.communicate('protocol=https\nhost=github.com\n\n')
        creds = dict([l.split('=', 1) for l in out.strip().splitlines() if '=' in l])
        token = creds.get('password')
        if token and token.startswith(('gho_', 'ghp_', 'github_pat_')):
            return token
    except Exception as e:
        print(f"[Error] 토큰 획득 실패: {e}")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    raise RuntimeError("GitHub 인증 토큰을 찾을 수 없습니다.")


def publish_release(tag: str = DEFAULT_TAG, files: list = None, title: str = None, notes: str = None):
    token = get_github_token()
    headers = {
        "Authorization": f"token {token}",
        "User-Agent": "JongJongTrader-Release-Script",
        "Accept": "application/vnd.github.v3+json"
    }

    if files is None:
        files = DEFAULT_FILES

    if not title:
        title = f"JongJong Trader {tag} (ARM64 & Windows Release)"
    if not notes:
        notes = (
            f"## 🚀 JongJong Trader {tag} 정식 릴리즈\n\n"
            f"- **배포 바이너리**:\n"
            f"  - 📱 안드로이드 실기기: `JongJongTrader_ARM64.apk`\n"
            f"  - 💻 윈도우 모바일 뷰: `JongJongTrader_Mobile.exe`\n\n"
            f"- **주요 업데이트 내역**:\n"
            f"  - **라오어 밸류리밸런싱 (VR 5.0) 투자 전략 신규 탑재**\n"
            f"    - 2주(10거래일) 결산 주기 및 공식 ($V_2 = V_1 + Pool/G \\pm 적립금$) 자동 리밸런싱\n"
            f"    - $\\pm 15\\%$ 최소/최대 밴드 이탈 방지용 2주 기간예약 주문 사다리 자동 산출\n"
            f"    - 백테스트 4-way 멀티 전략 비교 (종종이, 무한매수, VR 5.0, Buy&Hold)\n"
            f"    - 신규 계좌 생성 시 'VR 5.0 (밸류리밸런싱)' 및 2주 진행도 표시 지원\n"
            f"  - **거래 슬롯별 상세 내역 (4대 섹션) 엑셀형 표 전면 개편**\n"
            f"    - 한 행 = 하나의 매수 슬롯(Lot) 라이프사이클 모델 (중복 매도량 제거)\n"
            f"    - 4대 섹션 콤마 구분 헤더: `[시장 정보] , [매수] , [매도] , [손익]`\n"
            f"    - 한국식 요일 포함 날짜 포맷팅 (`09.28.(월)`) 적용\n"
            f"    - 미매도 슬롯의 실현손익을 공란(`-`)으로 안전 격리하고 청산 시점 자동 추적 정산\n"
            f"    - 슬롯별 정보 직접 수정 모달 다이얼로그 4대 섹션 개편\n"
            f"  - **자동화 테스트 스위트 강화**: TC-1 ~ TC-8 (전체 8개 무결성 테스트 통과)\n"
        )

    # 1. 릴리즈 존재 확인 또는 생성
    release_data = None
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{REPO}/releases/tags/{tag}",
            headers=headers
        )
        with urllib.request.urlopen(req) as resp:
            release_data = json.loads(resp.read().decode())
            print(f"ℹ️ 기존 릴리즈 태그 {tag} 발견 (ID: {release_data['id']})")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"🆕 새로운 릴리즈 생성 중: {tag}...")
            payload = json.dumps({
                "tag_name": tag,
                "target_commitish": "main",
                "name": title,
                "body": notes,
                "draft": False,
                "prerelease": False
            }).encode('utf-8')
            create_req = urllib.request.Request(
                f"https://api.github.com/repos/{REPO}/releases",
                data=payload,
                headers={**headers, "Content-Type": "application/json"}
            )
            with urllib.request.urlopen(create_req) as resp:
                release_data = json.loads(resp.read().decode())
                print(f"✅ 릴리즈 생성 성공 (ID: {release_data['id']})")
        else:
            raise

    upload_url = release_data["upload_url"].split("{")[0]
    existing_assets = {a["name"]: a["id"] for a in release_data.get("assets", [])}

    # 2. 파일별 업로드
    results = []
    for fpath in files:
        if not os.path.exists(fpath):
            print(f"⚠️ 배포 파일을 찾을 수 없어 건너뜁니다: {fpath}")
            continue

        fname = os.path.basename(fpath)
        fsize = os.path.getsize(fpath)
        fsize_mb = round(fsize / (1024 * 1024), 2)
        print(f"\n📦 배포 대상: {fname} ({fsize_mb} MB)")

        # 기존 동일 이름 에셋 삭제
        if fname in existing_assets:
            asset_id = existing_assets[fname]
            print(f"🗑️ 기존 에셋 삭제 중: {fname} (ID: {asset_id})...")
            del_req = urllib.request.Request(
                f"https://api.github.com/repos/{REPO}/releases/assets/{asset_id}",
                headers=headers,
                method="DELETE"
            )
            with urllib.request.urlopen(del_req) as resp:
                pass
            print("✅ 기존 에셋 삭제 완료")

        content_type = "application/vnd.android.package-archive" if fname.endswith(".apk") else "application/vnd.microsoft.portable-executable"
        print(f"⬆️ 파일 업로드 시작... ({fname}, {fsize_mb} MB)")

        upload_target = f"{upload_url}?name={fname}"
        with open(fpath, "rb") as f:
            file_data = f.read()

        upload_req = urllib.request.Request(
            upload_target,
            data=file_data,
            headers={
                "Authorization": f"token {token}",
                "User-Agent": "JongJongTrader-Release-Script",
                "Content-Type": content_type,
                "Content-Length": str(len(file_data))
            }
        )
        with urllib.request.urlopen(upload_req) as resp:
            res = json.loads(resp.read().decode())
            print(f"🎉 {fname} 업로드 완료! 링크:\n  {res.get('browser_download_url')}")
            results.append(res)

    print(f"\n✨ 모든 파일 배포 완료! GitHub Releases URL:\n  https://github.com/{REPO}/releases/tag/{tag}")
    return results


if __name__ == "__main__":
    tag = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TAG
    publish_release(tag)

