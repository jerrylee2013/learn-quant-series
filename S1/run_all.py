"""运行 S1 系列：下载/更新数据，按指定时间区间对三种策略回测并保存结果。

用法示例：
python S1/run_all.py --start 2020-01-01 --end 2023-01-01
"""
import os
import importlib
import argparse

try:
    from S1.data import download_and_cache
except Exception:
    # when running the script from S1/ directory directly, try local import
    from data import download_and_cache


STRATEGIES = [
    ("ma_crossover", "S1.strategies.ma_crossover"),
    ("rsi", "S1.strategies.rsi"),
    ("macd", "S1.strategies.macd"),
]


def run(start: str = None, end: str = None, update: bool = True, out_root: str = "results/s1"):
    # ensure data available
    os.makedirs(out_root, exist_ok=True)
    print("Downloading/updating data...")
    df = download_and_cache(start=None, end=None, save_path="data/raw/btc_daily.csv", update=update)
    if df.empty:
        raise RuntimeError("no data downloaded")

    # filter by requested backtest window for signals/backtest
    for name, module_path in STRATEGIES:
        print(f"Running strategy: {name}")
        try:
            mod = importlib.import_module(module_path)
        except ModuleNotFoundError:
            # when executing script directly from S1/ folder, try local module path
            local_path = module_path.replace("S1.", "")
            mod = importlib.import_module(local_path)
        signals = mod.generate_signals(df)
        out_dir = os.path.join(out_root, name)
        # run backtest with requested start/end
        mod.backtest(df, signals, out_dir=out_dir, start=start, end=end)
        print(f"Saved results for {name} to {out_dir}")


def cli():
    p = argparse.ArgumentParser()
    p.add_argument("--start", default=None)
    p.add_argument("--end", default=None)
    p.add_argument("--no-update", action="store_true")
    p.add_argument("--only", nargs="*", help="限定要跑的策略名称，例如 ma_crossover rsi")
    args = p.parse_args()
    run(start=args.start, end=args.end, update=not args.no_update)


if __name__ == "__main__":
    cli()
