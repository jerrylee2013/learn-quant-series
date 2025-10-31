import pandas as pd

df = pd.read_csv('data/raw/btc_daily.csv', parse_dates=['datetime'])
from S1.strategies.ma_crossover import generate_signals

sig = generate_signals(df)
sig2 = sig.reindex(pd.DatetimeIndex(df['datetime'])).fillna(0).astype(int)

df2 = df.sort_values('datetime').reset_index(drop=True)
df2['datetime'] = pd.to_datetime(df2['datetime'])
df2.set_index(pd.DatetimeIndex(df2['datetime'].values), inplace=True)

print('len df', len(df2), 'len sig2', len(sig2))

count = 0
for i, idx in enumerate(df2.index):
    prev_sig = sig2.iloc[i - 1] if i > 0 else 0
    cur_sig = sig2.iloc[i]
    if prev_sig == 0 and cur_sig == 1:
        print('entry at', idx, 'i=', i)
        count += 1
    if i > 200:
        break

print('found entries in first 200 rows:', count)

# replicate run_backtest_sl_tp to see trades
cash = 10000.0
qty = 0.0
in_position = False
trades = []
for i, idx in enumerate(df2.index):
    price_open = df2.at[idx, 'open']
    price_high = df2.at[idx, 'high']
    price_low = df2.at[idx, 'low']
    price_close = df2.at[idx, 'close']

    prev_sig = sig2.iloc[i - 1] if i > 0 else 0
    cur_sig = sig2.iloc[i]

    if (not in_position) and (prev_sig == 0 and cur_sig == 1):
        entry_price = price_open
        qty = cash / entry_price if entry_price > 0 else 0.0
        cash = 0.0
        in_position = True
        trades.append({'datetime': idx.isoformat(), 'side': 'buy', 'price': float(entry_price), 'qty': float(qty), 'cash': float(cash)})

    if in_position:
        sl_price = entry_price * (1 - 0.05)
        tp_price = entry_price * (1 + 0.2)
        hit_sl = price_low <= sl_price
        hit_tp = price_high >= tp_price
        if hit_sl and hit_tp:
            exit_price = sl_price
            cash = qty * exit_price * (1 - 0.001)
            trades.append({'datetime': idx.isoformat(), 'side': 'sell', 'price': float(exit_price), 'qty': float(qty), 'cash': float(cash), 'reason': 'sl'})
            qty = 0.0
            in_position = False
        elif hit_sl:
            exit_price = sl_price
            cash = qty * exit_price * (1 - 0.001)
            trades.append({'datetime': idx.isoformat(), 'side': 'sell', 'price': float(exit_price), 'qty': float(qty), 'cash': float(cash), 'reason': 'sl'})
            qty = 0.0
            in_position = False
        elif hit_tp:
            exit_price = tp_price
            cash = qty * exit_price * (1 - 0.001)
            trades.append({'datetime': idx.isoformat(), 'side': 'sell', 'price': float(exit_price), 'qty': float(qty), 'cash': float(cash), 'reason': 'tp'})
            qty = 0.0
            in_position = False

print('simulated trades count', len(trades))
if trades:
    print('first trades', trades[:4])

