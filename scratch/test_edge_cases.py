import sys, os
sys.path.insert(0, os.path.abspath('.'))
from scratch.test_netting_func import calculate_netted_orders

print("=== Case 1: No Hold (Only Buy Orders) ===")
c1_b = [{'price': 100.0, 'qty': 10, 'type': 'LOC 매수'}]
c1_s = []
res1 = calculate_netted_orders(c1_b, c1_s)
print("Net buy:", res1['net_buy_orders'])
print("Net sell:", res1['net_sell_orders'])
print("Max offset:", res1['max_offset_qty'])

print("\n=== Case 2: No Cash (Only Sell Orders) ===")
c2_b = []
c2_s = [{'price': 150.0, 'qty': 20, 'type': 'LOC 매도'}]
res2 = calculate_netted_orders(c2_b, c2_s)
print("Net buy:", res2['net_buy_orders'])
print("Net sell:", res2['net_sell_orders'])
print("Max offset:", res2['max_offset_qty'])

print("\n=== Case 3: No Overlap (Buy <= 140, Sell >= 155) ===")
c3_b = [{'price': 140.0, 'qty': 10, 'type': 'LOC 매수'}]
c3_s = [{'price': 155.0, 'qty': 10, 'type': 'LOC 매도'}]
res3 = calculate_netted_orders(c3_b, c3_s)
print("Net buy:", res3['net_buy_orders'])
print("Net sell:", res3['net_sell_orders'])
print("Max offset:", res3['max_offset_qty'])

print("\n=== Case 4: Multiple Unsold Lots (169 @ 155.78, 169 @ 156.29) vs User Buys ===")
c4_s = [
    {'price': 155.78, 'qty': 169, 'type': 'LOC 매도'},
    {'price': 156.29, 'qty': 169, 'type': 'LOC 매도'}
]
c4_b = [
    {'price': 170.83, 'qty': 39, 'type': 'LOC 매수'},
    {'price': 170.82, 'qty': 39, 'type': 'LOC 매수'},
    {'price': 155.92, 'qty': 39, 'type': 'LOC 매수'},
    {'price': 132.06, 'qty': 39, 'type': 'LOC 매수'},
]
res4 = calculate_netted_orders(c4_b, c4_s)
print("Max offset:", res4['max_offset_qty'])
print("Net sell:")
for o in res4['net_sell_orders']:
    print(" ", o)
print("Net buy:")
for o in res4['net_buy_orders']:
    print(" ", o)
