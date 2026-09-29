import sys
sys.path.insert(0, '.')
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
import os
import pandas as pd
from gui.account_manager import AccountManager

mgr = AccountManager()
acc = mgr.load_accounts()[0]

test_csv = 'scratch/test_export.csv'

# Test export
details = mgr.compute_account_details(acc)
df = details['df_res'].copy()
df['AccountName'] = acc['name']
df['Ticker'] = acc['ticker']
df['Strategy'] = acc['strategy']
df['InitialSeed'] = acc['initial_seed']
df.to_csv(test_csv, index=False, encoding='utf-8-sig')
print('Exported CSV shape:', df.shape)

# Test parse
df_in = pd.read_csv(test_csv, encoding='utf-8-sig')
print('Read back CSV rows:', len(df_in))
print('AccountName:', df_in['AccountName'].iloc[0])
print('Ticker:', df_in['Ticker'].iloc[0])
print('Strategy:', df_in['Strategy'].iloc[0])
print('InitialSeed:', df_in['InitialSeed'].iloc[0])
print('First Date:', df_in['Date'].iloc[0])
print('Last Date:', df_in['Date'].iloc[-1])
print('Last Hold:', df_in['Hold'].iloc[-1])
print('Last Cash:', df_in['Cash'].iloc[-1])
