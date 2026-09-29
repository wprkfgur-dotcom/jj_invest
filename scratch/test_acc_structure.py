import os
import json
import uuid
from datetime import datetime
import pandas as pd
import numpy as np

from strategies.jongjong import JongJongStrategy, safe_round4, round_down, round_up
from strategies.infinite_buying_v4 import InfiniteBuyingV4Strategy
from gui.order_netting import calculate_order_netting, generate_jongjong_orders
from core.market_calendar import get_next_trading_day, get_prev_trading_day, is_us_trading_day, parse_date
from core.data import fetch_market_data

# Test full AccountManager with operational methods
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
ACCOUNTS_FILE = os.path.join(DATA_DIR, "accounts.json")

with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
    accs = json.load(f)

acc = accs[0]
print("Loaded account:", acc['name'], "id:", acc['id'])
print("Adjustments count:", len(acc.get('adjustments', [])))
