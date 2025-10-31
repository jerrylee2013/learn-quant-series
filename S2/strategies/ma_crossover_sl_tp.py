import os
import pandas as pd

from S2.backtest import run_backtest_sl_tp

try:
    from S1.strategies.ma_crossover import generate_signals as base_generate_signals
except Exception:
    # fallback if package import context differs
    from ..S1.strategies.ma_crossover import generate_signals as base_generate_signals


def generate_signals(df: pd.DataFrame) -> pd.Series:
    # reuse S1 signal generator (it already avoids look-ahead)
    return base_generate_signals(df)


def backtest(df: pd.DataFrame, out_dir: str, sl_pct: float = 0.05, tp_pct: float = 0.2, **kwargs):
    os.makedirs(out_dir, exist_ok=True)
    signals = generate_signals(df)
    # align signals index to df datetimes (preserve tz if present)
    signals = signals.reindex(pd.DatetimeIndex(df["datetime"]))
    signals = signals.fillna(0).astype(int)
    return run_backtest_sl_tp(df, signals, out_dir, sl_pct=sl_pct, tp_pct=tp_pct, skip_reindex=True, **kwargs)


if __name__ == "__main__":
    # quick local runner
    df = pd.read_csv("data/raw/btc_daily.csv", parse_dates=["datetime"]) 
    out = backtest(df, out_dir="results/s2/ma_crossover_sl_tp", sl_pct=0.05, tp_pct=0.2)
    print(out["metrics"])
