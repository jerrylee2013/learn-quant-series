import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Optional


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


def _read_kelly_series(kelly_dir: Optional[str], prefer_field: str = "f_smooth") -> Optional[pd.DataFrame]:
    """Try to read precomputed kelly CSVs under kelly_dir and return a DataFrame with a datetime index or trade_index."""
    if not kelly_dir:
        return None
    base = os.path.abspath(kelly_dir)
    # prefer returns-based CSV
    returns_csv = os.path.join(base, "kelly_returns_rolling.csv")
    trades_csv = os.path.join(base, "kelly_trades_rolling.csv")
    try:
        if os.path.exists(returns_csv):
            df = pd.read_csv(returns_csv, parse_dates=["datetime"]).set_index("datetime")
            if prefer_field in df.columns:
                return df
            # try common names
            for c in ["f_smooth", "f_adj", "f_raw"]:
                if c in df.columns:
                    return df
        if os.path.exists(trades_csv):
            df = pd.read_csv(trades_csv)
            # trades-based uses trade_index column
            if "trade_index" in df.columns:
                return df.set_index("trade_index")
            return df
    except Exception:
        return None
    return None


def run_backtest_sl_tp(df: pd.DataFrame,
                       signals: pd.Series,
                       out_dir: str,
                       init_cash: float = 10000.0,
                       fee: float = 0.001,
                       sl_pct: float = 0.05,
                       tp_pct: float = 0.2,
                       skip_reindex: bool = False,
                       start: Optional[str] = None,
                       end: Optional[str] = None,
                       kline: str = "1d",
                       # S3 additions
                       enable_kelly: bool = False,
                       kelly_dir: Optional[str] = None,
                       kelly_min_alloc: float = 0.0,
                       kelly_max_alloc: float = 0.25,
                       kelly_field: str = "f_smooth") -> dict:
    """A simple daily backtester with optional Kelly-based position sizing.

    New parameters (S3):
    - enable_kelly: if True, attempt to read precomputed Kelly fractions from `kelly_dir`.
    - kelly_dir: directory where `kelly_returns_rolling.csv` or `kelly_trades_rolling.csv` live.
    - kelly_min_alloc / kelly_max_alloc: clamp the chosen fraction.
    - kelly_field: which column to use from the kelly CSV (default 'f_smooth').
    """
    os.makedirs(out_dir, exist_ok=True)

    # read kelly series if requested
    kelly_df = None
    if enable_kelly:
        kelly_df = _read_kelly_series(kelly_dir, prefer_field=kelly_field)

    # Re-implement a straightforward, robust simulation similar to the debug runner
    df = df.copy()
    df = df.sort_values("datetime").reset_index(drop=True)
    df["datetime"] = pd.to_datetime(df["datetime"]) 
    df.set_index(pd.DatetimeIndex(df["datetime"].values), inplace=True)

    # align signals explicitly to the dataframe datetimes unless caller already aligned
    if skip_reindex:
        sig = pd.Series(signals).fillna(0).astype(int)
        if len(sig) != len(df):
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

    # track number of completed trades to align with trades-based kelly if needed
    completed_trades = 0

    for i, idx in enumerate(df.index):
        price_open = df.at[idx, "open"]
        price_high = df.at[idx, "high"]
        price_low = df.at[idx, "low"]
        price_close = df.at[idx, "close"]

        # First, handle scheduled exit at today's open (signal 1->0 from previous day)
        if scheduled_exit[i] and in_position:
            exit_price = price_open
            # add proceeds to cash rather than overwriting (protect against qty==0)
            proceeds = qty * exit_price * (1 - fee)
            cash = cash + proceeds
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
            completed_trades += 1

        # Then, handle scheduled entry at today's open (signal 0->1 from previous day)
        if scheduled_entry[i] and (not in_position):
            entry_price = price_open

            # determine position size: either full-cash (old behavior) or Kelly-based
            desired_qty = 0.0
            if enable_kelly and kelly_df is not None:
                try:
                    f = None
                    # if kelly_df indexed by datetime, pick last <= idx
                    if isinstance(kelly_df.index, pd.DatetimeIndex):
                        sel = kelly_df.loc[kelly_df.index <= idx]
                        if not sel.empty:
                            if kelly_field in sel.columns:
                                f = float(sel[kelly_field].iloc[-1])
                            else:
                                # fallback
                                f = float(sel.iloc[-1].iloc[-1])
                    else:
                        # trades-based: use completed_trades as index
                        ti = min(completed_trades, int(kelly_df.index.max()))
                        if ti in kelly_df.index:
                            if kelly_field in kelly_df.columns:
                                f = float(kelly_df.loc[ti, kelly_field])
                            else:
                                f = float(kelly_df.iloc[ti].iloc[-1])
                    if f is None or np.isnan(f):
                        f = 0.0
                except Exception:
                    f = 0.0
                # clamp
                f = max(kelly_min_alloc, min(kelly_max_alloc, f))
                invest = f * (cash + qty * entry_price)
                # Cannot invest more than cash available
                invest = max(0.0, min(invest, cash))
                # account for buy-side fee: compute quantity so that buy_cost = qty*entry_price*(1+fee) <= invest
                desired_qty = invest / (entry_price * (1 + fee)) if entry_price > 0 else 0.0
            else:
                # legacy full-invest behavior
                # account for buy-side fee when fully investing
                desired_qty = cash / (entry_price * (1 + fee)) if entry_price > 0 else 0.0

            qty = desired_qty
            # apply buy cost including fee so available cash reflects execution cost
            buy_cost = qty * entry_price * (1 + fee)
            cash = cash - buy_cost
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
                # add proceeds to cash (do not overwrite existing cash)
                proceeds = qty * exit_price * (1 - fee)
                cash = cash + proceeds
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
                completed_trades += 1

        equity = cash + (qty * price_close)
        equity_records.append({"datetime": idx, "equity": float(equity)})

    # final liquidation
    if in_position and qty > 0:
        last_idx = df.index[-1]
        last_close = df.at[last_idx, "close"]
        proceeds = qty * last_close * (1 - fee)
        cash = cash + proceeds
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
    # attach metadata
    try:
        start_used = equity_df.index[0].isoformat()
        end_used = equity_df.index[-1].isoformat()
    except Exception:
        start_used = start
        end_used = end
    metrics["start"] = start_used
    metrics["end"] = end_used
    metrics["kline"] = kline

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
