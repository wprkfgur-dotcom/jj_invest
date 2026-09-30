"""
데이터 수집 및 전처리 모듈 (Data Loader)
야후 파이낸스 시세를 수집하고 캐싱하여 여러 전략에서 동일 데이터를 재사용합니다.
"""
import pandas as pd
import yfinance as yf

# 메모리 캐시 (동일 실행 세션 내 중복 다운로드 방지)
_DATA_CACHE = {}


def fetch_market_data(ticker: str, start_date: str, end_date: str, warmup_days: int = 50) -> pd.DataFrame:
    """
    야후 파이낸스에서 지정한 종목의 시세 데이터를 다운로드하고 전처리합니다.

    Args:
        ticker: 종목 티커 (예: 'SOXL', 'TQQQ')
        start_date: 매매 시작일 (YYYY-MM-DD)
        end_date: 매매 종료일 (YYYY-MM-DD)
        warmup_days: 이평선 및 지표 산출을 위한 사전 워밍업 기간(일)

    Returns:
        pd.DataFrame: ['Date', 'Close'] 컬럼을 포함하는 시세 데이터프레임
    """
    cache_key = (ticker, start_date, end_date, warmup_days)
    if cache_key in _DATA_CACHE:
        return _DATA_CACHE[cache_key].copy()

    warmup_start = (pd.Timestamp(start_date) - pd.Timedelta(days=warmup_days)).strftime('%Y-%m-%d')
    fetch_end = (pd.Timestamp(end_date) + pd.Timedelta(days=1)).strftime('%Y-%m-%d')

    print(f"[{ticker}] 야후 파이낸스 시세 다운로드 중 ({warmup_start} ~ {end_date})...")
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

    trade_start_indices = df[df['Date'] >= pd.Timestamp(start_date)].index
    if len(trade_start_indices) == 0:
        raise ValueError(f"지정한 기간({start_date} ~ {end_date})에 '{ticker}' 거래 데이터가 없습니다.")

    _DATA_CACHE[cache_key] = df
    return df.copy()
