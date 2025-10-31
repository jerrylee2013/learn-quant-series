#!/usr/bin/env python3
"""
Generate comparison plots (equity and drawdown) for S1 vs S2 (SL/TP) strategies.
Saves PNGs to results/figs/
"""
import os
import pandas as pd
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(__file__))
RESULTS = os.path.join(ROOT, 'results')
FIGS = os.path.join(RESULTS, 'figs')
os.makedirs(FIGS, exist_ok=True)

STRATEGIES = ['ma_crossover', 'rsi', 'macd']

def load_equity(path):
    df = pd.read_csv(path, parse_dates=['datetime'])
    df = df.set_index('datetime')
    # ensure equity series is float
    df['equity'] = df['equity'].astype(float)
    return df['equity']

def draw_compare(strategy):
    s1_path = os.path.join(RESULTS, 's1', strategy, 'equity.csv')
    s2_path = os.path.join(RESULTS, 's2', f'{strategy}_sl_tp', 'equity.csv')
    if not os.path.exists(s1_path) or not os.path.exists(s2_path):
        print(f"Skipping {strategy}: missing files")
        return None

    s1 = load_equity(s1_path)
    s2 = load_equity(s2_path)
    # normalize timezone on both series so indexes are comparable
    def _normalize_series_index(s: pd.Series) -> pd.Series:
        # ensure datetime index
        s.index = pd.to_datetime(s.index)
        # if tz-aware, convert to UTC and make naive
        try:
            if getattr(s.index, 'tz', None) is not None:
                s.index = s.index.tz_convert('UTC').tz_localize(None)
        except Exception:
            # defensive: if any operation fails, keep the index as-is (it will usually be fine)
            s.index = pd.to_datetime(s.index)
        return s

    s1 = _normalize_series_index(s1)
    s2 = _normalize_series_index(s2)

    # align index (inner join keeps only overlapping timestamps)
    df = pd.concat([s1, s2], axis=1, join='inner')
    df.columns = ['S1', 'S2']

    # equity plot
    # prefer a commonly-available style; fall back to default if not found
    try:
        plt.style.use('ggplot')
    except Exception:
        pass
    fig, ax = plt.subplots(figsize=(10, 4))
    df['S1'].plot(ax=ax, label='S1 baseline')
    df['S2'].plot(ax=ax, label='S2 SL/TP')
    ax.set_title(f'{strategy} — Equity: S1 vs S2')
    ax.set_ylabel('Equity')
    ax.legend()
    eq_out = os.path.join(FIGS, f'{strategy}_equity_compare.png')
    fig.savefig(eq_out, bbox_inches='tight', dpi=150)
    plt.close(fig)

    # drawdown plot
    def drawdown(series):
        peak = series.cummax()
        dd = (series - peak) / peak
        return dd

    dd = df.apply(drawdown)
    fig, ax = plt.subplots(figsize=(10, 3))
    dd['S1'].plot(ax=ax, label='S1')
    dd['S2'].plot(ax=ax, label='S2')
    ax.set_title(f'{strategy} — Drawdown')
    ax.set_ylabel('Drawdown')
    ax.legend()
    dd_out = os.path.join(FIGS, f'{strategy}_drawdown_compare.png')
    fig.savefig(dd_out, bbox_inches='tight', dpi=150)
    plt.close(fig)

    return eq_out, dd_out

def main():
    produced = []
    for s in STRATEGIES:
        res = draw_compare(s)
        if res:
            produced.append((s, res))
            print('Saved', res)

    if not produced:
        print('No figures produced.')
    else:
        print(f'Produced figures for {len(produced)} strategies. Files saved to {FIGS}')

if __name__ == '__main__':
    main()
