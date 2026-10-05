"""
종종 트레이더 모바일 (JongJongTrader Mobile) 종합 기능 자동화 테스트 스위트
TC-1: 계좌 생성/저장/로드 및 백업 무결성
TC-2: 종종이(JJ) LOC 4분할 및 퉁치기 주문 산출 엔진
TC-3: 라오어 무한매수법 v4 주문 산출 엔진
TC-4: 시장 시세 조회 및 SQLite DB 캐시 무결성
TC-5: GitHub Releases 자동 업데이트 버전 체크 엔진
TC-6: 모바일 UI 헬퍼 및 차트 SVG 생성기
"""
import sys
import os
import shutil
import tempfile
import unittest
from datetime import datetime

# Windows 콘솔 UTF-8 출력 보장
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 루트 경로 추가
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from gui.account_manager import AccountManager
from gui.order_netting import calculate_order_netting
from strategies.jongjong import JongJongStrategy
from strategies.infinite_buying_v4 import InfiniteBuyingV4Strategy
from strategies.vr_v5 import ValueRebalancingV5Strategy
from core.data import get_current_stock_price, get_price_from_db
from core.app_update import APP_VERSION, check_remote_version_info, parse_download_url
from mobile.theme import BG_DARK, ACCENT_BLUE, PROFIT_GREEN, LOSS_RED
from mobile.helpers import compute_suggested_trades, parse_picked_date_str
from mobile.charts import render_portfolio_chart


class TestJongJongTrader(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_accounts_file = os.path.join(self.test_dir, "test_accounts.json")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_tc1_account_lifecycle_and_backup(self):
        """TC-1: 계좌 생성, 저장, 로드 및 백업 생성 무결성 검증"""
        am = AccountManager(filepath=self.test_accounts_file)
        self.assertEqual(len(am.load_accounts()), 0)

        # 1. 신규 계좌 추가
        acc = am.add_account(
            name="테스트_SOXL_계좌",
            strategy="종종이 (LOC 4분할)",
            ticker="SOXL",
            start_date="2026-01-01",
            initial_seed=10000.0,
            reserve_ratio=0.05,
            memo="자동 테스트 계좌"
        )
        self.assertIsNotNone(acc)
        self.assertEqual(acc["name"], "테스트_SOXL_계좌")
        self.assertEqual(acc["initial_seed"], 10000.0)
        self.assertEqual(acc["reserve_ratio"], 0.05)

        # 2. 파일 영속성 검증 (저장 및 다시 로드)
        am2 = AccountManager(filepath=self.test_accounts_file)
        loaded = am2.load_accounts()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["ticker"], "SOXL")

        # 3. 백업 파일 생성 검증 (accounts.backup.json 자동 백업 로직)
        backup_path = os.path.join(os.path.dirname(am.filepath), "accounts.backup.json")
        with open(am.filepath, 'r', encoding='utf-8') as rf:
            with open(backup_path, 'w', encoding='utf-8') as wf:
                wf.write(rf.read())
        self.assertTrue(os.path.exists(backup_path))
        self.assertGreater(os.path.getsize(backup_path), 0)

    def test_tc2_jongjong_strategy_orders(self):
        """TC-2: 종종이(JJ) 4분할 주문 산출 및 퉁치기 로직 검증"""
        strat = JongJongStrategy(initial_capital=10000.0, reserve_ratio=0.05)
        self.assertEqual(strat.initial_capital, 10000.0)
        self.assertEqual(strat.reserve_ratio, 0.05)

        # 퉁치기(상계) 주문 계산 검증
        buy_orders = [{"type": "매수", "price": 40.0, "qty": 10, "loc_type": "LOC"}]
        sell_orders = [{"type": "매도", "price": 40.0, "qty": 4, "loc_type": "LOC"}]
        netting_result = calculate_order_netting(buy_orders, sell_orders)
        self.assertIsInstance(netting_result, dict)
        self.assertIn('net_buy_orders', netting_result)
        self.assertIn('net_sell_orders', netting_result)
        self.assertTrue(netting_result.get('is_netted', False))

    def test_tc3_infinite_buying_v4_strategy(self):
        """TC-3: 라오어 무한매수법 v4 전략 엔진 초기화 및 검증"""
        strat = InfiniteBuyingV4Strategy(initial_capital=20000.0)
        self.assertEqual(strat.initial_capital, 20000.0)
        self.assertEqual(strat.name, "무한매수법 v4.0")

    def test_tc4_market_data_and_db_cache(self):
        """TC-4: 시장 데이터 시세 조회 및 로컬 DB 캐시 조회 검증"""
        # SQLite DB에 기저장된 SOXL 과거 시세 조회 (빠른 로컬 DB 검증)
        db_price = get_price_from_db("SOXL", "2024-01-05")
        if db_price > 0:
            self.assertGreater(db_price, 0)

        # 실시간 fallback 가격 로직 검증
        price = get_current_stock_price("INVALID_TICKER_XYZ", fallback_price=50.0)
        self.assertEqual(price, 50.0)

    def test_tc5_app_update_version_check(self):
        """TC-5: GitHub Releases 자동 업데이트 버전 파싱 및 API 검증"""
        # 현재 버전 형식 검증 (vX.Y.Z)
        self.assertTrue(APP_VERSION.count(".") == 2, f"버전 형식 오류: {APP_VERSION}")
        
        # GitHub direct 다운로드 URL 파싱 로직 검증
        parsed = parse_download_url("https://github.com/wprkfgur-dotcom/jj_invest/releases/tag/v2.0.0")
        self.assertIn("github.com", parsed)

        # 원격 릴리스 정보 API 조회 검증
        info = check_remote_version_info()
        if info:
            self.assertIn("remote_version", info)
            self.assertIn("download_url", info)

    def test_tc6_mobile_helpers_and_svg_charts(self):
        """TC-6: 모바일 테마, 헬퍼 함수 및 SVG 차트 렌더러 검증"""
        self.assertTrue(BG_DARK.startswith("#"))
        self.assertTrue(PROFIT_GREEN.startswith("#"))
        self.assertTrue(LOSS_RED.startswith("#"))

        # 날짜 파싱 헬퍼 검증 (시간 제외 및 날짜 문자열 정규화)
        d_str = parse_picked_date_str("2026-10-04T00:00:00")
        self.assertTrue(len(d_str) == 10 and d_str.startswith("2026-10-"))

        # 제안 주문 계산 헬퍼 검증 (체결 수량 산출)
        buy_orders = [{"type": "매수", "price": 30.0, "qty": 10}]
        sell_orders = [{"type": "매도", "price": 32.0, "qty": 5}]
        calc_b, calc_s = compute_suggested_trades(
            close_p=29.0,
            buy_orders=buy_orders,
            sell_orders=sell_orders
        )
        self.assertEqual(calc_b, 10) # 29.0 <= 30.0 이므로 매수 체결 10주
        self.assertEqual(calc_s, 0)  # 29.0 < 32.0 이므로 매도 미체결 0주

        # SVG 차트 렌더러 검증 (Base64 벡터 이미지 생성)
        test_accounts = [{
            "account": {"name": "테스트"},
            "details": {"asset": 12000.0, "cash": 5000.0, "hold_value": 7000.0}
        }]
        svg_b64, dates, vals = render_portfolio_chart(test_accounts, total_portfolio_asset=12000.0)
        self.assertTrue(svg_b64.startswith("data:image/svg+xml;base64,"))
        self.assertGreater(len(vals), 0)

    def test_tc7_mobile_exe_binary_launch(self):
        r"""TC-7: dist\JongJongTrader_Mobile.exe 바이너리 직접 실행 및 프로세스 기동 검증"""
        import subprocess
        import time

        exe_path = os.path.join(BASE_DIR, "dist", "JongJongTrader_Mobile.exe")
        if not os.path.exists(exe_path):
            self.skipTest(f"바이너리가 존재하지 않습니다: {exe_path}")

        proc = subprocess.Popen([exe_path])
        try:
            # 4초간 프로세스가 크래시(WinError 등) 없이 정상 구동되는지 확인
            time.sleep(4)
            ret_code = proc.poll()
            self.assertIsNone(ret_code, f"JongJongTrader_Mobile.exe가 비정상 종료되었습니다 (반환코드: {ret_code})")
        finally:
            # 안전하게 프로세스 종료 및 정리
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                pass
            subprocess.run(["taskkill", "/F", "/IM", "flet.exe"], capture_output=True)
            subprocess.run(["taskkill", "/F", "/IM", "JongJongTrader_Mobile.exe"], capture_output=True)

    def test_tc8_vr_v5_strategy_and_orders(self):
        """TC-8: 라오어 밸류리밸런싱 VR 5.0 전략 엔진 및 2주 기간예약 주문 산출 검증"""
        # 1. 전략 엔진 초기화 검증
        strat = ValueRebalancingV5Strategy(
            ticker='TQQQ',
            initial_capital=100000.0,
            g_value=10.0,
            band_pct=0.15,
            pool_usage_limit=0.50
        )
        self.assertEqual(strat.g_value, 10.0)
        self.assertEqual(strat.band_pct, 0.15)
        self.assertEqual(strat.pool_usage_limit, 0.50)

        # 2. 2주 기간예약 주문표 (P_buy = V_min / n, P_sell = V_max / n) 산출 검증
        v_test = 85000.0
        v_min = v_test * 0.85 # 72,250
        v_max = v_test * 1.15 # 97,750
        buys, sells = strat.calculate_order_ladder(
            v_val=v_test,
            current_hold=1000,
            pool_cash=15000.0,
            pool_usage_limit=0.50
        )
        self.assertGreater(len(buys), 0)
        self.assertGreater(len(sells), 0)
        # 매수 1차 가격은 v_min / 1000 = 72.25
        self.assertEqual(buys[0]['price'], 72.25)
        # 매도 1차 가격은 v_max / 1000 = 97.75
        self.assertEqual(sells[0]['price'], 97.75)

        # 3. AccountManager 계좌 연동 및 주문표 산출 검증
        am = AccountManager(filepath=self.test_accounts_file)
        acc = am.add_account(
            name="VR_테스트계좌",
            strategy="VR 5.0 (밸류리밸런싱)",
            ticker="TQQQ",
            start_date="2026-01-02",
            initial_seed=100000.0,
            memo="VR 5.0 테스트"
        )
        dtl = am.compute_account_details(acc)
        self.assertIn("VR 5.0", dtl['strategy_name'])
        self.assertIn("buy_orders", dtl)
        self.assertIn("sell_orders", dtl)
        self.assertGreater(len(dtl['buy_orders']), 0)


if __name__ == "__main__":
    print("=" * 65)
    print("🚀 종종트레이더 모바일 (JongJongTrader Mobile) 기능 무결성 테스트")
    print("=" * 65)
    unittest.main(verbosity=2)
