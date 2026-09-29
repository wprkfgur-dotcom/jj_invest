import sys, json

sys.stdout.reconfigure(encoding='utf-8')
with open('data/accounts.json', 'r', encoding='utf-8') as f:
    accounts = json.load(f)

records = accounts[0]['trade_records']
for i, r in enumerate(records):
    d_i = str(r['Date'])[:10]
    active_lots = [
        lot for lot in records[:i+1] 
        if lot.get('R', 0) > 0 and (
            not lot.get('Sold', False) or 
            (lot.get('W') is not None and str(lot.get('W'))[:10] > d_i)
        )
    ]
    true_hold = sum(int(lot.get('R', 0)) for lot in active_lots)
    r['Hold'] = true_hold
    r['Asset'] = round(float(r['Cash']) + float(r['Close']) * true_hold, 2)

print('Last 10 records with corrected Hold & Asset:')
for r in records[-10:]:
    print(f"Date: {r['Date']}, Close: {r['Close']}, Hold: {r['Hold']}, Cash: {r['Cash']}, Asset: {r['Asset']}, Sold: {r.get('Sold')}, U: {r.get('U')}")
