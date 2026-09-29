"""
GitHub 저장소(jj_invest)로 코드 푸시를 수행하는 스크립트
"""
import os
import sys
import subprocess

def main():
    print("=" * 60)
    print("  🚀 GitHub 저장소 푸시 시작 (jj_invest)")
    print("=" * 60)
    print()

    # Git 실행 경로 설정
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    git_cmd_dir = os.path.join(local_app_data, "Programs", "Git", "cmd")
    git_bin_dir = os.path.join(local_app_data, "Programs", "Git", "ucrt64", "bin")
    
    os.environ["PATH"] = f"{git_cmd_dir};{git_bin_dir};" + os.environ.get("PATH", "")

    # git.exe 경로 탐색
    git_exe = os.path.join(git_cmd_dir, "git.exe")
    if not os.path.exists(git_exe):
        git_exe = "git"

    print("[1/2] 로컬 브랜치 및 커밋 상태 확인 중...")
    try:
        subprocess.run([git_exe, "status", "--short"], check=True)
    except Exception as e:
        print(f"Git 실행 오류: {e}")
        return

    print()
    print("[2/2] GitHub 원격 저장소(origin/main)로 푸시를 진행합니다...")
    print("      (브라우저 창이 열리면 [Sign in with your browser] 버튼을 눌러 승인해주세요)")
    print("-" * 60)

    # capture_output을 쓰지 않고 콘솔과 브라우저에 직접 상호작용하도록 실행
    ret = subprocess.run([git_exe, "push", "-u", "origin", "main"])

    print("-" * 60)
    if ret.returncode == 0:
        print()
        print("  ✔ 축하합니다! GitHub 푸시가 성공적으로 완료되었습니다!")
        print("  저장소 확인: https://github.com/wprkfgur-dotcom/jj_invest")
        print("=" * 60)
    else:
        print()
        print("  ❌ 푸시가 완료되지 않았습니다.")
        print("  인증 토큰(PAT)을 사용하여 푸시하려면 아래 명령어를 입력해주세요:")
        print("  git remote set-url origin https://<YOUR_TOKEN>@github.com/wprkfgur-dotcom/jj_invest.git")
        print("  git push -u origin main")
        print("=" * 60)

if __name__ == "__main__":
    main()
