"""
애플리케이션 버전 관리 및 구글 드라이브 기반 자동 업데이트 모듈
"""
import os
import sys
import re
import json
import subprocess
import email.utils
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple

APP_VERSION = "2.0.0"
APP_BUILD_NAME = "JongJong Trader v2.0.0 (ARM64 Release)"
# 현재 앱 빌드 기준 타임스탬프 (UTC) 및 한국시간 표시 문자열
APP_BUILD_TIMESTAMP = 1791078581  # Sun, 04 Oct 2026 01:49:41 GMT
APP_BUILD_DATE_STR = "2026-10-04 10:49"

if os.environ.get("FLET_APP_STORAGE_DATA"):
    BASE_DIR = os.environ.get("FLET_APP_STORAGE_DATA")
elif getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(BASE_DIR, "data")
UPDATE_CONFIG_FILE = os.path.join(DATA_DIR, "app_update_config.json")

DEFAULT_APK_DRIVE_URL = "https://drive.google.com/file/d/1Dc9OryPfGF8m19XB42JBejXkj8R7AZ_s/view?usp=sharing"
DEFAULT_DIRECT_DOWNLOAD_URL = "https://drive.usercontent.google.com/download?id=1Dc9OryPfGF8m19XB42JBejXkj8R7AZ_s&export=download&confirm=t"

DEFAULT_CONFIG: Dict[str, Any] = {
    "apk_drive_url": DEFAULT_APK_DRIVE_URL,
    "last_check_time": None,
    "last_check_status": "none",
    "auto_check_on_start": True
}


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def get_update_config() -> Dict[str, Any]:
    """업데이트 설정을 로드합니다."""
    _ensure_dir()
    if not os.path.exists(UPDATE_CONFIG_FILE):
        save_update_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    try:
        with open(UPDATE_CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                if k not in cfg:
                    cfg[k] = v
            if not cfg.get("apk_drive_url"):
                cfg["apk_drive_url"] = DEFAULT_APK_DRIVE_URL
            return cfg
    except Exception as e:
        print(f"[AppUpdate] 설정 로드 실패: {e}")
        return dict(DEFAULT_CONFIG)


def save_update_config(config: Dict[str, Any]):
    """업데이트 설정을 저장합니다."""
    _ensure_dir()
    try:
        with open(UPDATE_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[AppUpdate] 설정 저장 실패: {e}")


def extract_gdrive_file_id(url: str) -> Optional[str]:
    """구글 드라이브 공유 링크에서 파일 ID를 추출합니다."""
    if not url:
        return None
    url = url.strip()
    m = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
    if m:
        return m.group(1)
    m = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', url)
    if m:
        return m.group(1)
    return None


def parse_gdrive_download_url(url: str) -> str:
    """
    구글 드라이브 공유 링크를 바이러스 스캔 경고 없이 직접 다운로드 가능한 직링크로 변환합니다.
    """
    if not url:
        return DEFAULT_DIRECT_DOWNLOAD_URL
    file_id = extract_gdrive_file_id(url)
    if file_id:
        return f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"
    return url.strip() or DEFAULT_DIRECT_DOWNLOAD_URL


def parse_version_tuple(ver_str: str) -> Tuple[int, ...]:
    """'2.0.1' 등의 버전 문자열을 비교 가능한 튜플 (2, 0, 1)로 변환합니다."""
    if not ver_str:
        return (0, 0, 0)
    nums = [int(n) for n in re.findall(r'\d+', ver_str)]
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums[:3])


def check_remote_version_info(url: str, timeout: int = 5) -> Dict[str, Any]:
    """
    구글 드라이브 배포 링크의 최신 파일 정보를 확인하여
    현재 설치된 앱 버전과 비교합니다.
    """
    import urllib.request

    download_url = parse_gdrive_download_url(url)
    try:
        req = urllib.request.Request(
            download_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            method="HEAD"
        )
        with urllib.request.urlopen(req, timeout=timeout) as res:
            headers = dict(res.headers)
            last_mod_str = headers.get("Last-Modified", "")
            size_bytes = int(headers.get("Content-Length", 0))
            cd = headers.get("Content-Disposition", "")

            # 파일명 파싱
            fn_match = re.search(r'filename="?([^";]+)"?', cd)
            filename = fn_match.group(1) if fn_match else "JongJongTrader_ARM64.apk"
            size_mb = round(size_bytes / (1024 * 1024), 2) if size_bytes else 0.0

            # 최종 수정 일시 파싱 (KST 한국시간)
            kst_str = "알 수 없음"
            remote_ts = 0.0
            if last_mod_str:
                try:
                    dt = email.utils.parsedate_to_datetime(last_mod_str)
                    remote_ts = dt.timestamp()
                    kst_dt = dt.astimezone(timezone(timedelta(hours=9)))
                    kst_str = kst_dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    pass

            # 파일명에 명시된 버전 확인 (예: v2.0.1)
            remote_ver = None
            ver_candidates = re.findall(r'v?(\d+\.\d+(?:\.\d+)?)', filename)
            for cand in ver_candidates:
                if cand != "64":  # ARM64 배제
                    remote_ver = cand
                    break

            # 현재 버전과 비교
            is_newer = False
            current_ver_tuple = parse_version_tuple(APP_VERSION)
            if remote_ver:
                remote_ver_tuple = parse_version_tuple(remote_ver)
                if remote_ver_tuple > current_ver_tuple:
                    is_newer = True
                elif remote_ver_tuple < current_ver_tuple:
                    is_newer = False
                else:
                    # 버전 번호가 같을 경우 타임스탬프로 판정 (현재 빌드보다 2분 이상 최신 업로드일 때)
                    is_newer = remote_ts > (APP_BUILD_TIMESTAMP + 120)
            else:
                # 파일명이 동일한 경우 배포 타임스탬프 비교
                is_newer = remote_ts > (APP_BUILD_TIMESTAMP + 120)

            return {
                "status": "success",
                "is_newer": is_newer,
                "current_version": APP_VERSION,
                "remote_version": remote_ver or APP_VERSION,
                "remote_filename": filename,
                "remote_size_mb": size_mb,
                "remote_date_str": kst_str,
                "download_url": download_url,
                "remote_timestamp": remote_ts
            }
    except Exception as ex:
        return {
            "status": "error",
            "error": str(ex),
            "current_version": APP_VERSION,
            "download_url": download_url
        }


def trigger_apk_download(download_url: str):
    """
    안드로이드 OS 브라우저 또는 기본 웹브라우저로 APK 직링크 다운로드를 트리거합니다.
    """
    try:
        # 안드로이드 인텐트 호출
        subprocess.Popen(["am", "start", "-a", "android.intent.action.VIEW", "-d", download_url])
    except Exception:
        try:
            import webbrowser
            webbrowser.open(download_url)
        except Exception as e:
            print(f"[AppUpdate] 다운로드 실행 실패: {e}")
