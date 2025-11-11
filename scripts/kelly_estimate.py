#!/usr/bin/env python3
"""scripts/kelly_estimate.py

Estimate rolling Kelly fraction (discrete from trades or continuous from returns)
and save CSV + plot to results/s3/<strategy>_kelly/.

Usage examples:
  python3 scripts/kelly_estimate.py --strategy ma_crossover --window 100 --kelly_frac 0.25

This script is defensive: it first tries to use `results/s1/<strategy>/trades.csv` (per-trade returns,
discrete Kelly). If not available or not parseable, it falls back to `results/s1/<strategy>/equity.csv`
and computes continuous (returns-based) Kelly.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def read_trades_returns(trades_path: Path) -> pd.Series | None:
    if not trades_path.exists():
        return None
    df = pd.read_csv(trades_path)
    # Try common column names for per-trade returns
    candidates = [
        "return", "pct_return", "pct_ret", "r", "roi", "pnl", "pnl_pct",
        "net_return", "net_pct_return",
    ]
    for c in candidates:
        if c in df.columns:
            s = pd.to_numeric(df[c], errors="coerce").dropna()
            # if values look like percent (e.g., 1.5 for 1.5%) try to detect; but we won't convert automatically
            if len(s) > 0:
                return s.reset_index(drop=True)
    # Try computing from entry/exit prices
    if {"entry_price", "exit_price"}.issubset(set(df.columns)):
        ep = pd.to_numeric(df["entry_price"], errors="coerce")
        xp = pd.to_numeric(df["exit_price"], errors="coerce")
        valid = ep.notna() & xp.notna() & (ep != 0)
        if valid.sum() > 0:
            r = (xp[valid] - ep[valid]) / ep[valid]
            return r.reset_index(drop=True)
    # Try computing from cash in/out
    if {"cash_in", "cash_out"}.issubset(set(df.columns)):
        ci = pd.to_numeric(df["cash_in"], errors="coerce")
        co = pd.to_numeric(df["cash_out"], errors="coerce")
        valid = ci.notna() & co.notna() & (ci != 0)
        if valid.sum() > 0:
            r = (co[valid] - ci[valid]) / ci[valid]
            return r.reset_index(drop=True)
    return None


def read_equity_returns(equity_path: Path) -> pd.Series:
    df = pd.read_csv(equity_path, parse_dates=["datetime"]).sort_values("datetime")
    if "equity" in df.columns:
        eq = pd.to_numeric(df["equity"], errors="coerce")
    elif "net_value" in df.columns:
        eq = pd.to_numeric(df["net_value"], errors="coerce")
    elif "close" in df.columns:
        eq = pd.to_numeric(df["close"], errors="coerce")
    else:
        # assume second column is equity
        eq = pd.to_numeric(df.iloc[:, 1], errors="coerce")
    eq = eq.dropna()
    r = eq.pct_change().dropna()
    r.index = pd.to_datetime(df.loc[r.index, "datetime"]).values if "datetime" in df.columns else r.index
    return r


def rolling_discrete_kelly(trade_returns: pd.Series, window: int) -> pd.Series:
    # trade_returns: sequence of per-trade return ratios (e.g., 0.02 = +2%)
    # Compute rolling p, g, l and then f* = p - (1-p)/b where b = g/l
    r = trade_returns.reset_index(drop=True)

    def calc(sub: pd.Series):
        if len(sub) < 5:
            return np.nan
        wins = sub[sub > 0]
        losses = sub[sub <= 0]
        p = len(wins) / len(sub)
        if len(wins) == 0 or len(losses) == 0:
            return np.nan
        g = wins.mean()
        l = (-losses).mean()
        if l <= 0 or g <= 0:
            return np.nan
        b = g / l if l != 0 else np.inf
        f = p - (1 - p) / b
        return f

    out = r.rolling(window=window, min_periods=5).apply(lambda x: calc(pd.Series(x)), raw=False)
    out.index = r.index
    return out


def rolling_continuous_kelly(returns: pd.Series, window: int) -> pd.Series:
    # returns: pandas Series indexed by datetime (pct returns)
    mu = returns.rolling(window=window, min_periods=10).mean()
    var = returns.rolling(window=window, min_periods=10).var(ddof=0)
    f = mu / var.replace(0, np.nan)
    return f


def smooth_series(s: pd.Series, alpha: float) -> pd.Series:
    if alpha is None or alpha <= 0:
        return s
    return s.ewm(alpha=alpha, adjust=False).mean()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--window", type=int, default=100, help="rolling window (trades or days)")
    parser.add_argument("--kelly_frac", type=float, default=0.25, help="fractional Kelly to apply")
    parser.add_argument("--smoothing_alpha", type=float, default=0.0, help="EWMA alpha for smoothing final f")
    parser.add_argument("--out_dir", type=str, default=None)
    parser.add_argument("--method", type=str, choices=["auto", "discrete", "continuous"], default="auto")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    results_s1 = repo_root / "results" / "s1" / args.strategy
    trades_path = results_s1 / "trades.csv"
    equity_path = results_s1 / "equity.csv"

    out_base = Path(args.out_dir) if args.out_dir else (repo_root / "results" / "s3" / f"{args.strategy}_kelly")
    out_base.mkdir(parents=True, exist_ok=True)

    use_discrete = False
    trade_returns = None
    if args.method in ("auto", "discrete"):
        trade_returns = read_trades_returns(trades_path)
        if trade_returns is not None:
            use_discrete = True

    returns = None
    if not use_discrete:
        if not equity_path.exists():
            print(f"Error: no trades.csv usable and no equity.csv found for strategy {args.strategy}", file=sys.stderr)
            sys.exit(2)
        returns = read_equity_returns(equity_path)

    if use_discrete:
        print(f"Using discrete/trade-based Kelly for strategy {args.strategy}")
        r = trade_returns
        f_raw = rolling_discrete_kelly(r, window=args.window)
        # Align to index as integer trade index; create a Datetime-like index if trades contain times
        idx = pd.RangeIndex(start=0, stop=len(r), step=1)
        f_raw.index = idx
        # apply fraction and smoothing
        f_adj = args.kelly_frac * f_raw
        f_s = smooth_series(f_adj, args.smoothing_alpha)
        out_df = pd.DataFrame({"trade_index": idx, "f_raw": f_raw, "f_adj": f_adj, "f_smooth": f_s})
        out_csv = out_base / "kelly_trades_rolling.csv"
        out_df.to_csv(out_csv, index=False)
        print(f"Wrote kelly CSV: {out_csv}")

        # plot
        plt.figure(figsize=(10, 4))
        plt.plot(out_df["trade_index"], out_df["f_raw"], label="f_raw")
        plt.plot(out_df["trade_index"], out_df["f_adj"], label=f"f_adj (frac={args.kelly_frac})")
        if args.smoothing_alpha and args.smoothing_alpha > 0:
            plt.plot(out_df["trade_index"], out_df["f_smooth"], label=f"f_smooth alpha={args.smoothing_alpha}")
        plt.xlabel("trade_index")
        plt.ylabel("Kelly fraction")
        plt.title(f"Rolling discrete Kelly - {args.strategy}")
        plt.legend()
        png = out_base / "kelly_trades_rolling.png"
        plt.tight_layout()
        plt.savefig(png)
        print(f"Wrote kelly plot: {png}")

    else:
        print(f"Using continuous/returns-based Kelly for strategy {args.strategy}")
        r = returns.dropna()
        f_raw = rolling_continuous_kelly(r, window=args.window)
        # align index (datetime)
        f_adj = args.kelly_frac * f_raw
        f_s = smooth_series(f_adj, args.smoothing_alpha)
        out_df = pd.DataFrame({"datetime": f_raw.index, "f_raw": f_raw.values, "f_adj": f_adj.values, "f_smooth": f_s.values})
        out_csv = out_base / "kelly_returns_rolling.csv"
        out_df.to_csv(out_csv, index=False)
        print(f"Wrote kelly CSV: {out_csv}")

        # plot
        plt.figure(figsize=(10, 4))
        plt.plot(out_df["datetime"], out_df["f_raw"], label="f_raw")
        plt.plot(out_df["datetime"], out_df["f_adj"], label=f"f_adj (frac={args.kelly_frac})")
        if args.smoothing_alpha and args.smoothing_alpha > 0:
            plt.plot(out_df["datetime"], out_df["f_smooth"], label=f"f_smooth alpha={args.smoothing_alpha}")
        plt.xlabel("datetime")
        plt.ylabel("Kelly fraction")
        plt.title(f"Rolling continuous Kelly - {args.strategy}")
        plt.legend()
        png = out_base / "kelly_returns_rolling.png"
        plt.tight_layout()
        plt.savefig(png)
        print(f"Wrote kelly plot: {png}")


if __name__ == "__main__":
    main()
