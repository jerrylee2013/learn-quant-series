"""简单回测工具：接收 OHLCV DataFrame 和信号序列，支持按时间范围回放并导出结果与图像。

主要函数：
- run_backtest(df, signals, out_dir, start=None, end=None, init_cash=10000, fee=0.001)

输出目录 out_dir 下会产生：
- equity.csv (datetime, equity)
- metrics.json
- trades.csv
- equity.png, drawdown.png
"""
from __future__ import annotations
import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Optional, List, Dict


def _metrics(equity: pd.Series) -> Dict:
    returns = equity.pct_change().dropna()
    total_ret = equity.iloc[-1] / equity.iloc[0] - 1
    days = (equity.index[-1] - equity.index[0]).days
    years = max(days / 365.25, 1/252)
    ann_ret = (1 + total_ret) ** (1 / years) - 1
    running_max = equity.cummax()
    drawdown = (equity - running_max) / running_max
    max_dd = drawdown.min()
    vol = returns.std() * np.sqrt(252)
    sharpe = (returns.mean() * 252) / (returns.std() * np.sqrt(252)) if returns.std() > 0 else None
    return {
        "total_return": float(total_ret),
        "annualized_return": float(ann_ret),
        "max_drawdown": float(max_dd),
        "volatility": float(vol),
        "sharpe": float(sharpe) if sharpe is not None else None,
    }


def run_backtest(df: pd.DataFrame,
                 signals: pd.Series,
                 out_dir: str,
                 start: Optional[str] = None,
                 end: Optional[str] = None,
                 kline: str = "1d",
                 init_cash: float = 10000.0,
                 fee: float = 0.001) -> Dict:
    """按 signals 回测。signals 应与 df 对齐，取值为 1（持仓）或 0（空仓）。

    交易执行在下一日 open (避免 look-ahead)。当 signals.shift(1)==0 and signals==1 => 在 next bar open 买入
    当 signals.shift(1)==1 and signals==0 => 在 next bar open 卖出
    """
    os.makedirs(out_dir, exist_ok=True)
    data = df.copy()
    data = data.set_index("datetime")
    if start:
        data = data[data.index >= pd.to_datetime(start).tz_localize('UTC')]
    if end:
        data = data[data.index <= pd.to_datetime(end).tz_localize('UTC')]
    signals = signals.reindex(data.index).fillna(0).astype(int)

    cash = init_cash
    position = 0.0  # number of coins held
    equity_curve = []
    trades: List[Dict] = []

    prev_sig = 0
    for i in range(len(data)-1):
        idx = data.index[i]
        next_idx = data.index[i+1]
        price_next_open = data.iloc[i+1]["open"]
        sig = int(signals.iloc[i])
        # trade decisions based on current sig, execute next bar open
        if prev_sig == 0 and sig == 1:
            # buy full allocation
            qty = cash / price_next_open
            cost = qty * price_next_open * (1 + fee)
            position += qty
            cash -= cost
            trades.append({"datetime": next_idx.isoformat(), "side": "buy", "price": float(price_next_open), "qty": float(qty), "cash": float(cash)})
        elif prev_sig == 1 and sig == 0 and position > 0:
            # sell all
            proceeds = position * price_next_open * (1 - fee)
            trades.append({"datetime": next_idx.isoformat(), "side": "sell", "price": float(price_next_open), "qty": float(position), "cash": float(cash + proceeds)})
            cash += proceeds
            position = 0.0
        # compute equity at close of current day
        close = data.iloc[i]["close"]
        equity = cash + position * close
        equity_curve.append((idx, equity))
        prev_sig = sig

    # last bar equity
    last_idx = data.index[-1]
    last_close = data.iloc[-1]["close"]
    equity_curve.append((last_idx, cash + position * last_close))

    eq_df = pd.DataFrame(equity_curve, columns=["datetime", "equity"]).set_index("datetime")
    eq_df.index = pd.to_datetime(eq_df.index)

    metrics = _metrics(eq_df["equity"])
    # attach metadata: actual backtest window and kline
    try:
        start_used = eq_df.index[0].isoformat()
        end_used = eq_df.index[-1].isoformat()
    except Exception:
        start_used = start
        end_used = end
    metrics["start"] = start_used
    metrics["end"] = end_used
    metrics["kline"] = kline

    # save outputs
    eq_df.to_csv(os.path.join(out_dir, "equity.csv"))
    with open(os.path.join(out_dir, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    trades_df = pd.DataFrame(trades)
    if not trades_df.empty:
        trades_df.to_csv(os.path.join(out_dir, "trades.csv"), index=False)

    # plots
    plt.figure(figsize=(10, 4))
    plt.plot(eq_df.index, eq_df["equity"], label="Equity")
    plt.title("Equity Curve")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "equity.png"))
    plt.close()

    running_max = eq_df["equity"].cummax()
    drawdown = (eq_df["equity"] - running_max) / running_max
    plt.figure(figsize=(10, 3))
    plt.plot(drawdown.index, drawdown.values, color="red")
    plt.title("Drawdown")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "drawdown.png"))
    plt.close()

    return {"metrics": metrics, "equity": eq_df, "trades": trades}


if __name__ == "__main__":
    # quick smoke test (requires data file)
    from S1.data import download_and_cache
    df = download_and_cache()
    # trivial buy-and-hold signals
    sig = pd.Series(1, index=df["datetime"])
    out = run_backtest(df, sig, out_dir="results/s1/test", start=None, end=None)
    print(out["metrics"])
