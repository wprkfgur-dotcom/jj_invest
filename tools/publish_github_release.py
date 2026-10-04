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
DEFAULT_TAG = "v2.0.0"
DEFAULT_APK_PATH = r"C:\ai_development\JongJongTrader_ARM64.apk"


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


def publish_release(tag: str = DEFAULT_TAG, apk_path: str = DEFAULT_APK_PATH, title: str = None, notes: str = None):
    token = get_github_token()
    headers = {
        "Authorization": f"token {token}",
        "User-Agent": "JongJongTrader-Release-Script",
        "Accept": "application/vnd.github.v3+json"
    }

    if not title:
        title = f"JongJong Trader {tag}"
    if not notes:
        notes = (
            f"## 🚀 JongJong Trader {tag} 정식 릴리즈\n\n"
            f"- **빌드 종류**: Android ARM64 Release APK\n"
            f"- **주요 업데이트 내역**:\n"
            f"  - 구글 드라이브 클라우드 동기화 시스템 (계좌 실시간 연동)\n"
            f"  - 신규 계좌 1회차 첫 거래 매수가격 산출 로직 개선\n"
            f"  - 정산 마감 확정(저장)과 다음 거래일 진행 분리\n"
            f"  - GitHub Releases 기반 원클릭 자동 업데이트 시스템\n"
        )

    if not os.path.exists(apk_path):
        raise FileNotFoundError(f"APK 파일을 찾을 수 없습니다: {apk_path}")

    file_size = os.path.getsize(apk_path)
    file_name = os.path.basename(apk_path)
    print(f"📦 배포 대상: {file_name} ({round(file_size / (1024*1024), 2)} MB)")

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

    release_id = release_data["id"]
    upload_url = release_data["upload_url"].split("{")[0]

    # 2. 기존 동일 이름 에셋이 있으면 삭제
    for asset in release_data.get("assets", []):
        if asset["name"] == file_name:
            print(f"🗑️ 기존 에셋 삭제 중: {asset['name']} (ID: {asset['id']})...")
            del_req = urllib.request.Request(
                f"https://api.github.com/repos/{REPO}/releases/assets/{asset['id']}",
                headers=headers,
                method="DELETE"
            )
            with urllib.request.urlopen(del_req) as resp:
                pass
            print("✅ 기존 에셋 삭제 완료")

    # 3. APK 에셋 업로드
    print(f"⬆️ APK 파일 업로드 시작... ({file_name}, 약 {round(file_size/(1024*1024), 2)} MB)")
    upload_target = f"{upload_url}?name={file_name}"
    with open(apk_path, "rb") as f:
        apk_data = f.read()

    upload_req = urllib.request.Request(
        upload_target,
        data=apk_data,
        headers={
            "Authorization": f"token {token}",
            "User-Agent": "JongJongTrader-Release-Script",
            "Content-Type": "application/vnd.android.package-archive",
            "Content-Length": str(len(apk_data))
        }
    )
    with urllib.request.urlopen(upload_req) as resp:
        result = json.loads(resp.read().decode())
        print(f"🎉 배포 완료! 다운로드 링크:\n{result.get('browser_download_url')}")
        return result


if __name__ == "__main__":
    tag = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TAG
    publish_release(tag)
