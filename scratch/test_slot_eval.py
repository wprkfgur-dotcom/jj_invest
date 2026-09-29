import sys
sys.stdout.reconfigure(encoding='utf-8')

lots = [
    {'date': '2026-09-22', 'price': 151.95, 'U': 156.13, 'R': 159},
    {'date': '2026-09-23', 'price': 146.25, 'U': 150.28, 'R': 159},
    {'date': '2026-09-24', 'price': 146.33, 'U': 150.36, 'R': 159}
]

close_p = 151.45

lots_to_sell = [l for l in lots if close_p >= l['U']]
lots_to_hold = [l for l in lots if close_p < l['U']]

print('Close:', close_p)
print('\nLots that should be SOLD (익절):')
for l in lots_to_sell:
    profit = (close_p - l['price']) * l['R']
    ret = (close_p / l['price'] - 1) * 100
    print(f"  {l['date']} 로트: {l['R']}주, 매수가 ${l['price']}, 목표가 ${l['U']} -> 익절 (+${profit:.2f}, {ret:+.2f}%)")

print('\nLots that should be HELD (미매도 대기):')
for l in lots_to_hold:
    print(f"  {l['date']} 로트: {l['R']}주, 매수가 ${l['price']}, 목표가 ${l['U']} (목표가 미달)")
