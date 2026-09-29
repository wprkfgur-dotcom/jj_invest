"""
Python 업무 자동화 & 스크립트 개발 스타터 템플릿
"""
import sys
import os

# 윈도우 콘솔 UTF-8 인코딩 대응
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import pandas as pd
import requests


def check_environment():
    print("=" * 55)
    print("[OK] Python 개발 환경이 성공적으로 설정되었습니다!")
    print("=" * 55)
    print(f"• Python 버전 : {sys.version.split()[0]}")
    print(f"• 가상환경 경로: {sys.prefix}")
    print(f"• 실행 파일   : {sys.executable}")
    print(f"• 작업 디렉터리: {os.getcwd()}")
    print("-" * 55)


def demo_automation():
    print("[샘플 1] Pandas 데이터프레임 생성 및 처리:")
    data = {
        "작업명": ["데이터 수집", "엑셀 정리", "보고서 생성", "이메일 발송"],
        "소요시간(분)": [15, 30, 20, 5],
        "상태": ["완료", "완료", "진행중", "대기"],
    }
    df = pd.DataFrame(data)
    print(df.to_string(index=False))
    print("-" * 55)

    print("[샘플 2] requests 라이브러리 정상 동작 확인:")
    try:
        res = requests.get("https://httpbin.org/get", timeout=5)
        if res.status_code == 200:
            print("  -> 외부 API HTTP 요청 성공 (Status: 200 OK)")
    except Exception as e:
        print(f"  -> HTTP 요청 테스트 건너뜀: {e}")
    print("=" * 55)


if __name__ == "__main__":
    check_environment()
    demo_automation()
