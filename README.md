# jj_invest ⚡ 종종이 & 무한매수 자동매매 시스템

미국 레버리지 ETF(SOXL, TQQQ 등)를 위한 **종종이(JJ) 3단계 LOC 매매 전략 & 라오어 무한매수법 v4.0** 통합 실매매 관리 및 백테스트 플랫폼입니다.

---

## ✨ 주요 기능

1. **💼 내 투자 계좌 관리 및 실시간 대시보드 (Live & Accounts)**
   - **다중 계좌 관리**: 여러 투자 계좌 생성, 설정(위기준비금 비율, 시드, 메모 등) 수정 및 삭제
   - **위기준비금(AK) 안전 시스템**: 급락장 대비 안전자산(기본 5%)을 차감 보관하고, 순운용 시드(AR) 기준으로 분할 매수 집행
   - **오늘의 LOC 순 주문표 (퉁치기 상계 반영)**: 당일 장전에 걸어야 할 1차~4차 LOC 분할 매수 및 익절/손절 매도 주문을 실시간 자동 계산
   - **일일 체결 정산 & 캘린더 연동**: 미국 정규장 일정에 맞춘 Next Day 진행 및 일일 종가/체결 수량 입력 정산
   - **자산 입출금 및 세금 인출 관리**: 투자금 추가 입금 및 세금 납부를 위한 출금 이력 관리
   - **매매 일지 CSV 내보내기/불러오기**: 과거 엑셀/CSV 매매 일지를 그대로 이어받아 운용 가능

2. **📊 백테스트 시뮬레이터 (Backtest Simulator)**
   - 기간별, 종목별(SOXL, TQQQ 등), 초기 시드별 전략 성과 정밀 분석
   - 총수익률, 연평균 성장률(CAGR), 최대 낙폭(MDD), 샤프 지수, 칼마 비율 및 자산 성장 곡선 차트 제공

---

## 📁 프로젝트 구조

```text
jj_invest/
├── core/                       # 공통 코어 모듈
│   ├── data.py                 # 야후 파이낸스 시세 다운로드 및 메모리 캐시
│   ├── market_calendar.py      # 미국 증시 개장일 캘린더 연동
│   ├── metrics.py              # CAGR, MDD, 샤프/칼마비율 성과 분석
│   └── visualizer.py           # 자산 곡선 및 낙폭 비교 차트 시각화
├── strategies/                 # 투자 전략 모듈
│   ├── base.py                 # BaseStrategy 추상 기본 클래스
│   ├── jongjong.py             # 종종이(JJ) 3단계 모드 & LOC 4분할 매매 전략
│   ├── infinite_buying_v4.py   # 라오어 무한매수법 v4.0 전략
│   └── buy_and_hold.py         # 단순 보유(Buy & Hold) 벤치마크 전략
├── gui/                        # GUI 대시보드 (Tkinter)
│   ├── tabs/
│   │   ├── accounts_tab.py     # 계좌 관리 & 실매매 대시보드 탭
│   │   └── backtest_tab.py     # 백테스트 시뮬레이터 탭
│   ├── dialogs/
│   │   └── trade_entry_dialog.py # 체결 정산 & 일지 수정 다이얼로그
│   ├── account_manager.py      # 계좌 데이터 영속성 관리
│   ├── order_netting.py        # 퉁치기(상계) 주문 계산 엔진
│   ├── main_window.py          # 메인 윈도우 프레임워크
│   └── theme.py                # 다크 모드 테마 및 스타일링
├── data/                       # 데이터 저장소 (accounts.json 등)
│   └── accounts.example.json   # 계좌 템플릿 예시 파일
├── main.py                     # GUI 애플리케이션 진입점
├── backtest.py                 # 백테스트 CLI 실행기
├── optimize.py                 # 종종이 파라미터 최적화 엔진
├── requirements.txt            # 의존성 라이브러리 목록
└── README.md                   # 프로젝트 문서
```

---

## 🚀 빠른 시작

### 1. 환경 구성 및 패키지 설치
```powershell
pip install -r requirements.txt
```

### 2. GUI 자동매매 대시보드 실행
```powershell
python main.py
```

### 3. CLI 백테스트 실행
```powershell
python backtest.py
```
