import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def _calc_metrics(equity_series: pd.Series) -> dict:
    equity = equity_series.dropna()
    if equity.empty:
        return {}
    total_return = equity.iloc[-1] / equity.iloc[0] - 1
    days = (equity.index[-1] - equity.index[0]).days
    annualized_return = (1 + total_return) ** (365.0 / max(days, 1)) - 1
    daily_returns = equity.pct_change().dropna()
    volatility = daily_returns.std() * np.sqrt(252)
    sharpe = (daily_returns.mean() * np.sqrt(252)) / (daily_returns.std() + 1e-12)
    # max drawdown
    cummax = equity.cummax()
    drawdown = (equity - cummax) / cummax
    max_drawdown = drawdown.min()
    return {
        "total_return": float(total_return),
        "annualized_return": float(annualized_return),
        "max_drawdown": float(max_drawdown),
        "volatility": float(volatility),
        "sharpe": float(sharpe),
    }


def run_backtest_sl_tp(df: pd.DataFrame,
                       signals: pd.Series,
                       out_dir: str,
                       init_cash: float = 10000.0,
                       fee: float = 0.001,
                       sl_pct: float = 0.05,
                       tp_pct: float = 0.2,
                       skip_reindex: bool = False) -> dict:
    """A simple daily backtester that supports stop-loss and take-profit.

    Assumptions / simplifications:
    - Entry executed at next-day open after a 0->1 signal transition.
    - Stop-loss / take-profit are checked intraday using the same day's high/low
      AFTER entry (i.e. the open day counts for checking hits).
    - If both SL and TP are hit on the same day we conservatively assume SL was hit first.
    - Exit on signal 1->0 happens at next-day open.
    - When position remains at the end of data, we liquidate at the last close.
    """
    os.makedirs(out_dir, exist_ok=True)

    # Re-implement a straightforward, robust simulation similar to the debug runner
    df = df.copy()
    df = df.sort_values("datetime").reset_index(drop=True)
    df["datetime"] = pd.to_datetime(df["datetime"]) 
    df.set_index(pd.DatetimeIndex(df["datetime"].values), inplace=True)

    # align signals explicitly to the dataframe datetimes unless caller already aligned
    if skip_reindex:
        # assume signals is positional-aligned with df (same length)
        sig = pd.Series(signals).fillna(0).astype(int)
        if len(sig) != len(df):
            # fall back to reindexing if lengths mismatch
            sig = signals.reindex(pd.DatetimeIndex(df["datetime"].values)).fillna(0).astype(int)
    else:
        sig = signals.reindex(pd.DatetimeIndex(df["datetime"].values)).fillna(0).astype(int)

    cash = init_cash
    qty = 0.0
    equity_records = []
    trades = []

    in_position = False
    entry_price = None

    # Precompute scheduled entries/exits to enforce "signal -> next-day open" semantics
    scheduled_entry = [False] * len(sig)
    scheduled_exit = [False] * len(sig)
    for j in range(1, len(sig)):
        prev = sig.iloc[j - 1]
        cur = sig.iloc[j]
        if prev == 0 and cur == 1:
            if j + 1 < len(sig):
                scheduled_entry[j + 1] = True
        if prev == 1 and cur == 0:
            if j + 1 < len(sig):
                scheduled_exit[j + 1] = True

    for i, idx in enumerate(df.index):
        price_open = df.at[idx, "open"]
        price_high = df.at[idx, "high"]
        price_low = df.at[idx, "low"]
        price_close = df.at[idx, "close"]

        # First, handle scheduled exit at today's open (signal 1->0 from previous day)
        if scheduled_exit[i] and in_position:
            exit_price = price_open
            cash = qty * exit_price * (1 - fee)
            trades.append({
                "datetime": idx.isoformat(),
                "side": "sell",
                "price": float(exit_price),
                "qty": float(qty),
                "cash": float(cash),
                "reason": "signal_exit",
            })
            qty = 0.0
            in_position = False

        # Then, handle scheduled entry at today's open (signal 0->1 from previous day)
        if scheduled_entry[i] and (not in_position):
            entry_price = price_open
            qty = cash / entry_price if entry_price > 0 else 0.0
            cash = 0.0
            in_position = True
            trades.append({
                "datetime": idx.isoformat(),
                "side": "buy",
                "price": float(entry_price),
                "qty": float(qty),
                "cash": float(cash),
            })

        # If in position, check SL/TP intraday (using today's high/low)
        if in_position:
            sl_price = entry_price * (1 - sl_pct)
            tp_price = entry_price * (1 + tp_pct)
            hit_sl = price_low <= sl_price
            hit_tp = price_high >= tp_price

            if hit_sl and hit_tp:
                exit_price = sl_price
                reason = "sl"
            elif hit_sl:
                exit_price = sl_price
                reason = "sl"
            elif hit_tp:
                exit_price = tp_price
                reason = "tp"
            else:
                exit_price = None

            if exit_price is not None:
                cash = qty * exit_price * (1 - fee)
                trades.append({
                    "datetime": idx.isoformat(),
                    "side": "sell",
                    "price": float(exit_price),
                    "qty": float(qty),
                    "cash": float(cash),
                    "reason": reason,
                })
                qty = 0.0
                in_position = False

        equity = cash + (qty * price_close)
        equity_records.append({"datetime": idx, "equity": float(equity)})

    # final liquidation
    if in_position and qty > 0:
        last_idx = df.index[-1]
        last_close = df.at[last_idx, "close"]
        cash = qty * last_close * (1 - fee)
        trades.append({
            "datetime": last_idx.isoformat(),
            "side": "sell",
            "price": float(last_close),
            "qty": float(qty),
            "cash": float(cash),
            "reason": "liquidate_end",
        })
        qty = 0.0
        equity_records[-1]["equity"] = float(cash)

    equity_df = pd.DataFrame(equity_records).set_index("datetime")["equity"]

    metrics = _calc_metrics(equity_df)

    # write outputs
    equity_df.to_csv(os.path.join(out_dir, "equity.csv"), index_label="datetime")
    with open(os.path.join(out_dir, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    trades_df = pd.DataFrame(trades)
    if not trades_df.empty:
        trades_df.to_csv(os.path.join(out_dir, "trades.csv"), index=False)

    # plots
    try:
        plt.figure(figsize=(10, 4))
        equity_df.plot(title="Equity")
        plt.xlabel("")
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "equity.png"))
        plt.close()
    except Exception:
        pass

    return {"metrics": metrics, "equity": equity_df, "trades": trades}
