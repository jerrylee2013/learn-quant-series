"""MACD 策略（S1）

规则：MACD(12,26,9) 线上穿信号线买入，线下穿卖出。
"""
import pandas as pd


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def generate_signals(df: pd.DataFrame) -> pd.Series:
    s = df["close"]
    ema12 = _ema(s, 12)
    ema26 = _ema(s, 26)
    macd = ema12 - ema26
    signal = _ema(macd, 9)
    cond_buy = (macd.shift(1) <= signal.shift(1)) & (macd > signal)
    cond_sell = (macd.shift(1) >= signal.shift(1)) & (macd < signal)
    sig = pd.Series(0, index=df.index)
    position = 0
    for i in range(len(df)):
        if cond_buy.iloc[i] and position == 0:
            position = 1
        elif cond_sell.iloc[i] and position == 1:
            position = 0
        sig.iloc[i] = position
    return pd.Series(sig.values, index=df["datetime"]) 


def backtest(df, signals, out_dir, **kwargs):
    import importlib
    try:
        run_backtest = importlib.import_module("S1.backtest").run_backtest
    except Exception:
        run_backtest = importlib.import_module("backtest").run_backtest
    return run_backtest(df, signals, out_dir, **kwargs)
