"""MA 交叉策略（S1）

规则：短期 MA=5 上穿长期 MA=20 买入；下穿卖出。
generate_signals(df) 返回对齐 df 的 1/0 序列，禁止 look-ahead（使用 shift 比较）。
"""
import pandas as pd


SHORT = 5
LONG = 20


def generate_signals(df: pd.DataFrame) -> pd.Series:
    df2 = df.copy()
    df2["ma_short"] = df2["close"].rolling(SHORT).mean()
    df2["ma_long"] = df2["close"].rolling(LONG).mean()
    # signal when short crosses above long, using previous bar to avoid look-ahead
    cond_buy = (df2["ma_short"].shift(1) <= df2["ma_long"].shift(1)) & (df2["ma_short"] > df2["ma_long"])
    cond_sell = (df2["ma_short"].shift(1) >= df2["ma_long"].shift(1)) & (df2["ma_short"] < df2["ma_long"])
    sig = pd.Series(0, index=df2.index)
    position = 0
    for i in range(len(df2)):
        if cond_buy.iloc[i] and position == 0:
            position = 1
        elif cond_sell.iloc[i] and position == 1:
            position = 0
        sig.iloc[i] = position
    # return series aligned with datetime column
    return pd.Series(sig.values, index=df2["datetime"]) 


def backtest(df, signals, out_dir, **kwargs):
    import importlib
    try:
        run_backtest = importlib.import_module("S1.backtest").run_backtest
    except Exception:
        run_backtest = importlib.import_module("backtest").run_backtest
    return run_backtest(df, signals, out_dir, **kwargs)
