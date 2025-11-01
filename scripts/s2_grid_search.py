#!/usr/bin/env python3
"""Grid-search SL/TP for S2 strategies and compute Pareto front.

Produces:
- results/s2/experiments_grid.csv
- results/s2/pareto_front.png

Usage: python3 scripts/s2_grid_search.py
"""
import os
import csv
import datetime
import subprocess
from typing import List, Dict

import pandas as pd
import matplotlib.pyplot as plt

# strategies to test (module path under S2.strategies)
STRATEGIES = [
    "ma_crossover",
    "rsi",
    "macd",
]

ROOT = os.path.dirname(os.path.dirname(__file__))
RESULTS_S2 = os.path.join(ROOT, "results", "s2")
OUT_CSV = os.path.join(RESULTS_S2, "experiments_grid.csv")
OUT_PARETO = os.path.join(RESULTS_S2, "pareto_front.png")
os.makedirs(RESULTS_S2, exist_ok=True)

# make sure repository root is on sys.path so imports like S2.strategies.* work
import sys
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# grid
SL_GRID = [0.03, 0.05, 0.08]
TP_GRID = [0.10, 0.20, 0.30]

DATA_PATH = os.path.join(ROOT, "data", "raw", "btc_daily.csv")


def _get_git_short():
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT)
        return out.decode().strip()
    except Exception:
        return ""


def run():
    # load market data once
    df = pd.read_csv(DATA_PATH, parse_dates=["datetime"]) 

    rows: List[Dict] = []
    tag = _get_git_short()
    date = datetime.date.today().isoformat()

    for strat in STRATEGIES:
        mod_path = f"S2.strategies.{strat}"
        mod = __import__(mod_path, fromlist=["backtest"])
        backtest = getattr(mod, "backtest")

        for sl in SL_GRID:
            for tp in TP_GRID:
                out_dir = os.path.join(RESULTS_S2, f"{strat}_sl{int(sl*100)}_tp{int(tp*100)}")
                print(f"Running {strat} sl={sl} tp={tp} -> {out_dir}")
                try:
                    res = backtest(df, out_dir=out_dir, sl_pct=sl, tp_pct=tp)
                    metrics = res.get("metrics", {})
                    row = {
                        "tag": tag,
                        "date": date,
                        "strategy": strat,
                        "sl_pct": sl,
                        "tp_pct": tp,
                        "total_return": metrics.get("total_return", None),
                        "annualized_return": metrics.get("annualized_return", None),
                        "max_drawdown": metrics.get("max_drawdown", None),
                        "volatility": metrics.get("volatility", None),
                        "sharpe": metrics.get("sharpe", None),
                        "notes": "grid-search",
                    }
                except Exception as e:
                    row = {
                        "tag": tag,
                        "date": date,
                        "strategy": strat,
                        "sl_pct": sl,
                        "tp_pct": tp,
                        "total_return": None,
                        "annualized_return": None,
                        "max_drawdown": None,
                        "volatility": None,
                        "sharpe": None,
                        "notes": f"error: {e}",
                    }
                rows.append(row)

    # write CSV
    keys = ["tag", "date", "strategy", "sl_pct", "tp_pct", "total_return", "annualized_return", "max_drawdown", "volatility", "sharpe", "notes"]
    with open(OUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    # compute pareto across all strategies combined
    dfres = pd.DataFrame(rows).dropna(subset=["annualized_return", "max_drawdown"]) 
    if dfres.empty:
        print("No successful runs to analyze.")
        return

    # convert to numeric
    dfres["annualized_return"] = pd.to_numeric(dfres["annualized_return"], errors="coerce")
    dfres["max_drawdown"] = pd.to_numeric(dfres["max_drawdown"], errors="coerce")

    # Pareto: higher annualized_return better, higher max_drawdown (less negative) better
    pts = dfres[["strategy", "sl_pct", "tp_pct", "annualized_return", "max_drawdown"]].copy()

    def is_dominated(i):
        r_i = pts.iloc[i]
        for j in range(len(pts)):
            if i == j:
                continue
            r_j = pts.iloc[j]
            # j dominates i if j.return >= i.return and j.drawdown >= i.drawdown and at least one strict
            if (r_j["annualized_return"] >= r_i["annualized_return"] and
                r_j["max_drawdown"] >= r_i["max_drawdown"] and
                (r_j["annualized_return"] > r_i["annualized_return"] or r_j["max_drawdown"] > r_i["max_drawdown"])):
                return True
        return False

    dominated = [is_dominated(i) for i in range(len(pts))]
    pts["dominated"] = dominated
    pareto = pts[~pts["dominated"]].copy()

    # save pareto table
    pareto_out = os.path.join(RESULTS_S2, "pareto_table.csv")
    pareto.to_csv(pareto_out, index=False)

    # plot
    plt.figure(figsize=(8, 5))
    # scatter all
    for strat in pts["strategy"].unique():
        sub = pts[pts["strategy"] == strat]
        plt.scatter(sub["max_drawdown"], sub["annualized_return"], label=strat)

    # highlight pareto
    plt.scatter(pareto["max_drawdown"], pareto["annualized_return"], s=120, facecolors='none', edgecolors='k', linewidths=1.5, label='Pareto')
    plt.xlabel('max_drawdown (negative is worse)')
    plt.ylabel('annualized_return')
    plt.title('S2 grid: max_drawdown vs annualized_return (Pareto front highlighted)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT_PARETO, dpi=150)
    plt.close()

    print(f"Wrote experiments CSV: {OUT_CSV}")
    print(f"Wrote pareto table: {pareto_out}")
    print(f"Wrote pareto plot: {OUT_PARETO}")


if __name__ == '__main__':
    run()
