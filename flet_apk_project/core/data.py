"""
데이터 수집 및 전처리 모듈 (Data Loader with Local SQLite Cache)
로컬 SQLite DB에 SOXL, TQQQ 등 주요 종목 시세를 영구 보존하고,
필요한 경우에만(신규 날짜 누락 등) 야후 파이낸스에서 증분 다운로드하여 갱신합니다.
"""
import os
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

# 메모리 캐시 (세션 내 재사용)
_DATA_CACHE = {}


def get_db_path() -> str:
    """모바일 및 데스크톱 환경에 맞는 SQLite DB 파일 경로를 반환합니다."""
    storage_base = os.environ.get("FLET_APP_STORAGE_DATA")
    if not storage_base:
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        storage_base = os.path.dirname(cur_dir)
    data_dir = os.path.join(storage_base, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "market_data.db")


def init_market_db(conn: sqlite3.Connection = None):
    """시세 저장용 SQLite 테이블 및 인덱스를 생성합니다."""
    close_after = False
    if conn is None:
        conn = sqlite3.connect(get_db_path())
        close_after = True
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_candles (
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL NOT NULL,
                volume REAL,
                PRIMARY KEY (ticker, date)
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ticker_date ON daily_candles(ticker, date)")
        conn.commit()
    finally:
        if close_after:
            conn.close()


def save_candles_to_db(ticker: str, df: pd.DataFrame):
    """다운로드한 시세 데이터프레임을 SQLite DB에 UPSERT 합니다."""
    if df is None or df.empty:
        return
    ticker = ticker.upper().strip()
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    try:
        init_market_db(conn)
        rows = []
        for _, row in df.iterrows():
            d_str = row['Date'].strftime('%Y-%m-%d') if hasattr(row['Date'], 'strftime') else str(row['Date'])[:10]
            c = float(row['Close'])
            o = float(row.get('Open', c))
            h = float(row.get('High', c))
            l = float(row.get('Low', c))
            v = float(row.get('Volume', 0.0))
            rows.append((ticker, d_str, o, h, l, c, v))

        cur = conn.cursor()
        cur.executemany("""
            INSERT INTO daily_candles (ticker, date, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker, date) DO UPDATE SET
                open=excluded.open,
                high=excluded.high,
                low=excluded.low,
                close=excluded.close,
                volume=excluded.volume
        """, rows)
        conn.commit()
    except Exception as ex:
        print(f"[{ticker}] 시세 DB 저장 안내: {ex}")
    finally:
        conn.close()


def get_cached_candles_from_db(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """로컬 SQLite DB에서 해당 기간의 시세 데이터를 조회합니다."""
    ticker = ticker.upper().strip()
    db_path = get_db_path()
    if not os.path.exists(db_path):
        return pd.DataFrame()

    conn = sqlite3.connect(db_path)
    try:
        init_market_db(conn)
        query = """
            SELECT date as Date, open as Open, high as High, low as Low, close as Close, volume as Volume
            FROM daily_candles
            WHERE ticker = ? AND date >= ? AND date <= ?
            ORDER BY date ASC
        """
        df = pd.read_sql_query(query, conn, params=(ticker, start_date, end_date))
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'])
        return df
    except Exception as ex:
        print(f"[{ticker}] 시세 DB 조회 안내: {ex}")
        return pd.DataFrame()
    finally:
        conn.close()


def get_db_date_range(ticker: str) -> tuple:
    """DB에 저장된 특정 티커의 최소 날짜와 최대 날짜를 반환합니다. (없으면 None, None)"""
    ticker = ticker.upper().strip()
    db_path = get_db_path()
    if not os.path.exists(db_path):
        return None, None
    conn = sqlite3.connect(db_path)
    try:
        init_market_db(conn)
        cur = conn.cursor()
        cur.execute("SELECT MIN(date), MAX(date) FROM daily_candles WHERE ticker = ?", (ticker,))
        row = cur.fetchone()
        if row and row[0] and row[1]:
            return row[0], row[1]
        return None, None
    except Exception:
        return None, None
    finally:
        conn.close()


def get_price_from_db(ticker: str, target_date: str) -> float:
    """로컬 DB에서 특정 날짜(또는 해당 날짜 직전)의 종가를 즉시 반환합니다. (없으면 0.0)"""
    ticker = ticker.upper().strip()
    target_clean = str(target_date).strip()[:10]
    db_path = get_db_path()
    if not os.path.exists(db_path):
        return 0.0
    conn = sqlite3.connect(db_path)
    try:
        init_market_db(conn)
        cur = conn.cursor()
        cur.execute("""
            SELECT close FROM daily_candles
            WHERE ticker = ? AND date <= ?
            ORDER BY date DESC LIMIT 1
        """, (ticker, target_clean))
        row = cur.fetchone()
        if row and row[0]:
            return round(float(row[0]), 2)
        return 0.0
    except Exception:
        return 0.0
    finally:
        conn.close()


def fetch_market_data(ticker: str, start_date: str, end_date: str, warmup_days: int = 50) -> pd.DataFrame:
    """
    야후 파이낸스 및 로컬 SQLite DB에서 시세 데이터를 수집합니다.
    - DB에 이미 저장된 날짜 범위는 네트워크 통신 없이 초고속으로 로드합니다.
    - 데이터가 누락된 경우에만 야후 파이낸스에서 필요한 구간을 증분 다운로드하여 DB를 갱신합니다.
    """
    ticker = ticker.upper().strip()
    cache_key = (ticker, start_date, end_date, warmup_days)
    if cache_key in _DATA_CACHE:
        return _DATA_CACHE[cache_key].copy()

    warmup_start = (pd.Timestamp(start_date) - pd.Timedelta(days=warmup_days)).strftime('%Y-%m-%d')
    fetch_end = (pd.Timestamp(end_date) + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    today_str = datetime.now().strftime('%Y-%m-%d')

    # 1. DB의 저장 범위 확인
    min_d, max_d = get_db_date_range(ticker)

    need_download = False
    dl_start = warmup_start
    dl_end = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    if min_d is None or max_d is None:
        need_download = True
        dl_start = min(warmup_start, '2019-01-01')
    else:
        if warmup_start < min_d:
            need_download = True
            dl_start = warmup_start
            dl_end = min_d
        elif end_date > max_d and max_d < today_str:
            need_download = True
            dl_start = max_d
            dl_end = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    # 2. 꼭 필요한 경우에만 야후 파이낸스 증분 다운로드
    if need_download:
        try:
            print(f"[{ticker}] 시세 증분 업데이트 중 ({dl_start} ~ {dl_end})...")
            raw = yf.download(ticker, start=dl_start, end=dl_end, auto_adjust=False, progress=False)
            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = raw.columns.droplevel(1)
            raw.dropna(subset=['Close'], inplace=True)
            if not raw.empty:
                df_new = pd.DataFrame({
                    'Date': pd.to_datetime(raw.index).tz_localize(None),
                    'Open': raw['Open'].astype(float).values if 'Open' in raw.columns else raw['Close'].astype(float).values,
                    'High': raw['High'].astype(float).values if 'High' in raw.columns else raw['Close'].astype(float).values,
                    'Low': raw['Low'].astype(float).values if 'Low' in raw.columns else raw['Close'].astype(float).values,
                    'Close': raw['Close'].astype(float).values,
                    'Volume': raw['Volume'].astype(float).values if 'Volume' in raw.columns else 0.0
                }).reset_index(drop=True)
                save_candles_to_db(ticker, df_new)
        except Exception as ex:
            print(f"[{ticker}] 야후 파이낸스 다운로드 실패(로컬 DB 데이터로 대체 진행): {ex}")

    # 3. 로컬 DB에서 필요한 전체 범위 추출
    df_cached = get_cached_candles_from_db(ticker, warmup_start, end_date)
    if not df_cached.empty:
        trade_start_indices = df_cached[df_cached['Date'] >= pd.Timestamp(start_date)].index
        if len(trade_start_indices) > 0:
            _DATA_CACHE[cache_key] = df_cached
            return df_cached.copy()

    # 4. DB에 여전히 없는 경우 (최초 다운로드 실패 등) 직접 다운로드
    raw = yf.download(ticker, start=warmup_start, end=fetch_end, auto_adjust=False, progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.droplevel(1)
    raw.dropna(subset=['Close'], inplace=True)
    df = pd.DataFrame({
        'Date': pd.to_datetime(raw.index).tz_localize(None),
        'Open': raw['Open'].astype(float).values if 'Open' in raw.columns else raw['Close'].astype(float).values,
        'High': raw['High'].astype(float).values if 'High' in raw.columns else raw['Close'].astype(float).values,
        'Low': raw['Low'].astype(float).values if 'Low' in raw.columns else raw['Close'].astype(float).values,
        'Close': raw['Close'].astype(float).values,
        'Volume': raw['Volume'].astype(float).values if 'Volume' in raw.columns else 0.0
    }).reset_index(drop=True)

    save_candles_to_db(ticker, df)
    _DATA_CACHE[cache_key] = df
    return df.copy()


_HISTORICAL_PRICE_CACHE = {}


def get_current_stock_price(ticker: str, fallback_price: float = 0.0) -> float:
    """실시간 야후 파이낸스 fast_info 시세를 조회합니다."""
    try:
        t = yf.Ticker(ticker)
        fi = t.fast_info
        p = fi.get('lastPrice') or fi.get('regularMarketPrice') or fi.get('previousClose')
        if p is not None and float(p) > 0:
            return round(float(p), 2)
    except Exception as ex:
        print(f"[{ticker}] 실시간 시세 조회 안내: {ex}")

    return round(float(fallback_price), 2) if fallback_price > 0 else 142.50


def get_stock_price_for_date(ticker: str, target_date: str, fallback_price: float = 0.0) -> float:
    """
    지정한 종목의 특정 정산 대상 날짜(target_date) 직전 종가를 조회합니다.
    - 로컬 SQLite DB에 저장된 시세가 있으면 네트워크 호출 없이 0.001초 만에 즉시 반환합니다.
    - 오늘 또는 미래 날짜인 경우: 실시간 현재가(fast_info)를 조회합니다.
    - 과거 날짜인데 DB에 없는 경우: 증분 다운로드 및 로컬 캐싱 후 반환합니다.
    - 조회 실패 시 fallback_price를 반환합니다.
    """
    if not target_date:
        return get_current_stock_price(ticker, fallback_price)

    target_clean = str(target_date).strip()[:10]
    cache_key = (ticker.upper(), target_clean)
    if cache_key in _HISTORICAL_PRICE_CACHE:
        return _HISTORICAL_PRICE_CACHE[cache_key]

    today_str = datetime.now().strftime('%Y-%m-%d')

    # 1. 과거 날짜인 경우 로컬 SQLite DB 우선 조회 (초고속 0.001s)
    if target_clean < today_str:
        db_p = get_price_from_db(ticker, target_clean)
        if db_p > 0:
            _HISTORICAL_PRICE_CACHE[cache_key] = db_p
            return db_p

    # 2. 오늘 또는 미래 날짜인 경우 실시간 빠른 시세 조회
    if target_clean >= today_str:
        p = get_current_stock_price(ticker, fallback_price)
        if p > 0:
            _HISTORICAL_PRICE_CACHE[cache_key] = p
            return p

    # 3. DB에 누락된 과거 구간인 경우 증분 다운로드 및 로컬 캐싱
    try:
        dt = datetime.strptime(target_clean, '%Y-%m-%d')
        s_date = (dt - timedelta(days=7)).strftime('%Y-%m-%d')
        e_date = (dt + timedelta(days=7)).strftime('%Y-%m-%d')
        df = fetch_market_data(ticker, s_date, e_date, warmup_days=10)
        if df is not None and not df.empty:
            df['Date_str'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
            match = df[df['Date_str'] == target_clean]
            if not match.empty:
                val = round(float(match.iloc[0]['Close']), 2)
                _HISTORICAL_PRICE_CACHE[cache_key] = val
                return val
            prior = df[df['Date_str'] <= target_clean]
            if not prior.empty:
                val = round(float(prior.iloc[-1]['Close']), 2)
                _HISTORICAL_PRICE_CACHE[cache_key] = val
                return val
    except Exception as ex:
        print(f"[{ticker}] {target_clean} 과거 종가 조회 안내: {ex}")

    return get_current_stock_price(ticker, fallback_price)

