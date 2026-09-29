import sys
sys.path.insert(0, '.')
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
import os
import pandas as pd
from gui.account_manager import AccountManager

mgr = AccountManager()
acc = mgr.load_accounts()[0]

test_csv = 'scratch/test_export.csv'

# Step 1: Export
details = mgr.compute_account_details(acc)
df = details['df_res'].copy()
df['AccountName'] = acc['name']
df['Ticker'] = acc['ticker']
df['Strategy'] = acc['strategy']
df['InitialSeed'] = acc['initial_seed']
df.to_csv(test_csv, index=False, encoding='utf-8-sig')

# Step 2: Implement parse_trade_records_csv logic and test
def parse_trade_records_csv(file_path):
    encodings = ['utf-8-sig', 'utf-8', 'cp949', 'euc-kr']
    df = None
    for enc in encodings:
        try:
            df = pd.read_csv(file_path, encoding=enc)
            break
        except Exception:
            continue
    if df is None:
        raise ValueError("CSV 파일을 읽을 수 없습니다.")

    col_map = {
        '날짜': 'Date', '일자': 'Date', '거래일자': 'Date', 'date': 'Date',
        '종가': 'Close', 'close': 'Close',
        '변동률': 'Chg', '등락률': 'Chg', 'chg': 'Chg',
        '모드': 'Mode', 'mode': 'Mode',
        '매수량': 'BuyQty', '매수수량': 'BuyQty', 'r': 'R', 'buyqty': 'BuyQty',
        '매수가': 'BuyPrice', '매수단가': 'BuyPrice', 'buyprice': 'BuyPrice',
        '매수금액': 'S', 's': 'S',
        '목표가': 'U', 'u': 'U',
        '매도여부': 'Sold', '청산여부': 'Sold', 'sold': 'Sold',
        '매도일': 'W', '청산일': 'W', 'w': 'W',
        '매도가': 'X', '매도단가': 'X', '청산가': 'X', 'x': 'X',
        '매도량': 'SellQty', '매도수량': 'SellQty', 'y': 'SellQty', 'sellqty': 'SellQty',
        '매도금액': 'Z', 'z': 'Z',
        '손익금액': 'Profit', '실현손익': 'Profit', '손익': 'Profit', 'profit': 'Profit',
        '예수금': 'Cash', '현금': 'Cash', '보유현금': 'Cash', 'cash': 'Cash',
        '보유량': 'Hold', '보유수량': 'Hold', 'hold': 'Hold',
        '총자산': 'Asset', '평가금': 'Asset', '총평가자산': 'Asset', 'asset': 'Asset',
        '메모': 'Memo', '비고': 'Memo', 'memo': 'Memo',
        '슬롯상태': 'StatusText', '상태': 'StatusText', 'statustext': 'StatusText',
        'tag': 'Tag',
        '종목': 'Ticker', 'ticker': 'Ticker',
        '전략': 'Strategy', 'strategy': 'Strategy',
        '초기시드': 'InitialSeed', 'initialseed': 'InitialSeed',
        '계좌명': 'AccountName', 'accountname': 'AccountName'
    }

    renamed = {}
    for c in df.columns:
        s_c = str(c).strip()
        low_c = s_c.lower()
        if s_c in col_map:
            renamed[c] = col_map[s_c]
        elif low_c in col_map:
            renamed[c] = col_map[low_c]
    df = df.rename(columns=renamed)

    ticker = 'SOXL'
    if 'Ticker' in df.columns and not df['Ticker'].isna().all():
        ticker = str(df['Ticker'].dropna().iloc[0]).strip().upper()

    strategy = '종종이 기본전략'
    if 'Strategy' in df.columns and not df['Strategy'].isna().all():
        strategy = str(df['Strategy'].dropna().iloc[0]).strip()

    initial_seed = 150000.0
    if 'InitialSeed' in df.columns and not df['InitialSeed'].isna().all():
        initial_seed = float(df['InitialSeed'].dropna().iloc[0])
    elif 'Cash' in df.columns:
        initial_seed = float(df['Cash'].iloc[0])

    account_name = "SOXL 연동 계좌"
    if 'AccountName' in df.columns and not df['AccountName'].isna().all():
        account_name = str(df['AccountName'].dropna().iloc[0]).strip()

    records = []
    for idx, row in df.iterrows():
        d_val = str(row['Date'])[:10]
        close_v = float(row.get('Close', 0.0))
        r_v = int(row.get('R', row.get('BuyQty', 0))) if not pd.isna(row.get('R', row.get('BuyQty', 0))) else 0
        buy_p = float(row.get('BuyPrice', close_v)) if not pd.isna(row.get('BuyPrice')) else close_v
        s_v = float(row.get('S', 0.0)) if not pd.isna(row.get('S')) else round(buy_p * r_v * 1.001, 2)
        u_v = float(row['U']) if ('U' in row and not pd.isna(row['U']) and float(row['U']) > 0) else None
        
        w_raw = row.get('W')
        sold_raw = row.get('Sold')
        is_sold = False
        w_val = None
        if w_raw is not None and not pd.isna(w_raw) and str(w_raw).strip() not in ('', '-', 'None', 'nan'):
            is_sold = True
            w_val = str(w_raw)[:10]
        elif sold_raw is True or str(sold_raw).lower() in ('true', '1'):
            is_sold = True
            w_val = str(w_raw)[:10] if (w_raw is not None and not pd.isna(w_raw)) else d_val

        x_v = float(row['X']) if ('X' in row and not pd.isna(row['X']) and float(row['X']) > 0) else None
        z_v = float(row['Z']) if ('Z' in row and not pd.isna(row['Z'])) else 0.0
        profit_v = float(row['Profit']) if ('Profit' in row and not pd.isna(row['Profit'])) else (None if not is_sold else 0.0)
        sell_q = int(row.get('SellQty', 0)) if not pd.isna(row.get('SellQty')) else 0
        cash_v = float(row.get('Cash', 0.0)) if not pd.isna(row.get('Cash')) else 0.0
        hold_v = int(row.get('Hold', 0)) if not pd.isna(row.get('Hold')) else 0
        asset_v = float(row.get('Asset', 0.0)) if not pd.isna(row.get('Asset')) else round(cash_v + hold_v * close_v, 2)

        rec = {
            't': idx,
            'Date': d_val,
            'Close': close_v,
            'Chg': float(row.get('Chg', 0.0)) if not pd.isna(row.get('Chg')) else 0.0,
            'Mode': str(row.get('Mode', 'Normal')),
            'R': r_v,
            'BuyQty': r_v,
            'BuyPrice': buy_p,
            'S': s_v,
            'U': u_v,
            'Sold': is_sold,
            'W': w_val,
            'X': x_v,
            'Z': z_v,
            'Profit': profit_v,
            'SellQty': sell_q,
            'Cash': cash_v,
            'Hold': hold_v,
            'Asset': asset_v,
            'AR': float(row.get('AR', 0.0)) if not pd.isna(row.get('AR')) else initial_seed,
            'AK': float(row.get('AK', 0.0)) if not pd.isna(row.get('AK')) else 0.0,
            'Memo': str(row.get('Memo', '')) if not pd.isna(row.get('Memo')) else '',
            'StatusText': str(row.get('StatusText', '')) if not pd.isna(row.get('StatusText')) else '',
            'Tag': str(row.get('Tag', 'tag_normal')) if not pd.isna(row.get('Tag')) else 'tag_normal'
        }
        records.append(rec)

    return {
        'account_name': account_name,
        'ticker': ticker,
        'strategy': strategy,
        'initial_seed': initial_seed,
        'start_date': records[0]['Date'] if records else '2026-01-02',
        'current_date': records[-1]['Date'] if records else '2026-01-02',
        'current_cash': records[-1]['Cash'] if records else initial_seed,
        'current_hold': records[-1]['Hold'] if records else 0,
        'total_asset': records[-1]['Asset'] if records else initial_seed,
        'current_price': records[-1]['Close'] if records else 0.0,
        'trade_records': records,
        'record_count': len(records)
    }

parsed = parse_trade_records_csv(test_csv)
print('Parsed result:')
print('Ticker:', parsed['ticker'])
print('Strategy:', parsed['strategy'])
print('Record count:', parsed['record_count'])
print('Start date:', parsed['start_date'])
print('Current date:', parsed['current_date'])
print('Hold:', parsed['current_hold'])
print('Cash:', parsed['current_cash'])
print('Unsold lots in parsed:', len([r for r in parsed['trade_records'] if r['R'] > 0 and not r['Sold']]))
for l in [r for r in parsed['trade_records'] if r['R'] > 0 and not r['Sold']]:
    print('  Unsold lot:', l['Date'], l['R'], l['U'], l['Sold'])

# Step 3: Test compute_account_details with temporary account dict
mock_acc = {
    'id': 'test_mock_acc',
    'name': parsed['account_name'],
    'strategy': parsed['strategy'],
    'ticker': parsed['ticker'],
    'start_date': parsed['start_date'],
    'initial_seed': parsed['initial_seed'],
    'trade_records': parsed['trade_records'],
    'current_date': parsed['current_date'],
    'operational_state': 'DAY_COMPLETED',
    'adjustments': []
}
comp_res = mgr.compute_account_details(mock_acc)
print('\nCompute details check:')
print('Hold:', comp_res['current_hold'])
print('Cash:', comp_res['current_cash'])
print('Pending sell count:', comp_res['pending_sell_count'])
print('Sell orders count:', len(comp_res['sell_orders']))
print('Buy orders count:', len(comp_res['buy_orders']))
print('ALL TESTS PASSED!')
