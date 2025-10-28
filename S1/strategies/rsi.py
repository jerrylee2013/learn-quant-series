"""RSI 策略（S1）

规则：14 日 RSI，RSI<30 买入，RSI>70 卖出。建议叠加 MA 过滤，但这里实现基础版本。
"""
import pandas as pd

PERIOD = 14
RSI_LOW = 30
RSI_HIGH = 70


def _rsi(series: pd.Series, period: int = PERIOD) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ma_up = up.rolling(period).mean()
    ma_down = down.rolling(period).mean()
    rs = ma_up / ma_down
    rsi = 100 - 100 / (1 + rs)
    return rsi


def generate_signals(df: pd.DataFrame) -> pd.Series:
    df2 = df.copy()
    df2["rsi"] = _rsi(df2["close"], PERIOD)
    sig = pd.Series(0, index=df2.index)
    position = 0
    for i in range(len(df2)):
        r = df2["rsi"].iloc[i]
        if pd.isna(r):
            sig.iloc[i] = position
            continue
        if r < RSI_LOW and position == 0:
            position = 1
        elif r > RSI_HIGH and position == 1:
            position = 0
        sig.iloc[i] = position
    return pd.Series(sig.values, index=df2["datetime"]) 


def backtest(df, signals, out_dir, **kwargs):
    import importlib
    try:
        run_backtest = importlib.import_module("S1.backtest").run_backtest
    except Exception:
        run_backtest = importlib.import_module("backtest").run_backtest
    return run_backtest(df, signals, out_dir, **kwargs)
