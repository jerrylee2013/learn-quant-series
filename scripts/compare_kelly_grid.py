#!/usr/bin/env python3
"""Compare backtest results across a grid of kelly_max_alloc and fractional-kelly multipliers.

Outputs:
- results/s3/ma_crossover_compare/grid/summary.csv
- results/s3/ma_crossover_compare/grid/return_vs_alloc.png
- per-run folders under results/s3/ma_crossover_compare/grid/run_<idx>/
"""
import json
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from S3.strategies.ma_crossover import backtest

ROOT = Path(__file__).resolve().parents[1]
DATA_CSV = ROOT / 'data' / 'raw' / 'btc_daily.csv'
ORIG_KELLY = Path('results/s3/ma_crossover_kelly/kelly_returns_rolling.csv')
OUT_DIR = Path('results/s3/ma_crossover_compare/grid')
OUT_DIR.mkdir(parents=True, exist_ok=True)

# grid settings (can be tuned)
MAX_ALLOCS = [0.01, 0.05, 0.1, 0.25, 0.5]
FRAC_FACTORS = [0.25, 0.5, 1.0]

runs = []
idx = 0

df = pd.read_csv(DATA_CSV, parse_dates=['datetime'])
orig_kelly = pd.read_csv(ORIG_KELLY, parse_dates=['datetime']).set_index('datetime')

for frac in FRAC_FACTORS:
    for max_alloc in MAX_ALLOCS:
        idx += 1
        run_dir = OUT_DIR / f'run_{idx:02d}_f{frac}_max{max_alloc}'
        run_dir.mkdir(parents=True, exist_ok=True)
        # prepare modified kelly dir
        kelly_dir = run_dir / 'kelly'
        kelly_dir.mkdir(exist_ok=True)
        # adjust f_smooth (if present) by frac
        mod = orig_kelly.copy()
        # find a sensible column to scale
        for col in ['f_smooth', 'f_adj', 'f_raw']:
            if col in mod.columns:
                mod[col] = mod[col].astype(float) * frac
                break
        # write to kelly_returns_rolling.csv in the kelly_dir
        mod.reset_index().to_csv(kelly_dir / 'kelly_returns_rolling.csv', index=False)

        # run backtest using this modified kelly_dir and the max_alloc clamp
        print(f'Run {idx}: frac={frac}, max_alloc={max_alloc} -> out {run_dir}')
        out = backtest(df, out_dir=str(run_dir), sl_pct=0.05, tp_pct=0.2,
                       enable_kelly=True, kelly_dir=str(kelly_dir), kelly_min_alloc=0.0,
                       kelly_max_alloc=float(max_alloc), kelly_field='f_smooth')

        metrics = out['metrics']
        trades_count = len(out.get('trades', [])) if out.get('trades') is not None else 0
        final_equity = float(out['equity'].iloc[-1])

        runs.append({
            'run_idx': idx,
            'frac': frac,
            'kelly_max_alloc': max_alloc,
            'total_return': metrics.get('total_return'),
            'annualized_return': metrics.get('annualized_return'),
            'max_drawdown': metrics.get('max_drawdown'),
            'volatility': metrics.get('volatility'),
            'sharpe': metrics.get('sharpe'),
            'trades': trades_count,
            'final_equity': final_equity,
            'out_dir': str(run_dir),
        })

# save summary
summary_df = pd.DataFrame(runs)
summary_df.to_csv(OUT_DIR / 'summary.csv', index=False)
print('Wrote', OUT_DIR / 'summary.csv')

# plot total_return vs max_alloc for each frac
plt.figure(figsize=(8,5))
for frac in sorted(summary_df['frac'].unique()):
    sub = summary_df[summary_df['frac']==frac]
    plt.plot(sub['kelly_max_alloc'], sub['total_return'], marker='o', label=f'frac={frac}')
plt.xlabel('kelly_max_alloc')
plt.ylabel('total_return')
plt.title('Total return vs kelly_max_alloc (per frac)')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig(OUT_DIR / 'return_vs_alloc.png')
print('Wrote', OUT_DIR / 'return_vs_alloc.png')

# also write JSON summary
with open(OUT_DIR / 'summary.json','w') as f:
    json.dump(runs, f, indent=2)

print('Done grid runs. Summary in', OUT_DIR)
