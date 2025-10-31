import os
import pandas as pd

from S2.strategies.ma_crossover import backtest as ma_backtest
from S2.strategies.rsi import backtest as rsi_backtest
from S2.strategies.macd import backtest as macd_backtest


def load_data():
    path = os.path.join("data", "raw", "btc_daily.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Data file not found: {path}. Please run S1 data downloader first.")
    df = pd.read_csv(path, parse_dates=["datetime"]) 
    return df


def run_all():
    df = load_data()
    results = {}
    results["ma"] = ma_backtest(df, out_dir="results/s2/ma_crossover_sl_tp")
    results["rsi"] = rsi_backtest(df, out_dir="results/s2/rsi_sl_tp")
    results["macd"] = macd_backtest(df, out_dir="results/s2/macd_sl_tp")
    for k, v in results.items():
        metrics = v.get("metrics", {})
        print(f"{k} -> {metrics}")


if __name__ == "__main__":
    run_all()
