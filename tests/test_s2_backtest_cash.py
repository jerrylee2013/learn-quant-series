import pandas as pd
from S2.backtest import run_backtest_sl_tp


def make_df(opens):
    dates = pd.date_range("2020-01-01", periods=len(opens), freq="D")
    df = pd.DataFrame({
        "datetime": dates,
        "open": opens,
        "high": opens,
        "low": opens,
        "close": opens,
        "volume": [1.0] * len(opens),
    })
    return df


def test_full_invest_buy_sell_consistent():
    # prices chosen so entry and exit prices are equal -> final cash should be C * (1-f)/(1+f)
    opens = [100.0, 100.0, 100.0, 100.0]
    df = make_df(opens)
    # signals: 0,1,0,0 -> buy at day2 open, sell at day3 open (scheduled)
    signals = pd.Series([0, 1, 0, 0], index=pd.DatetimeIndex(df["datetime"]))

    init_cash = 10000.0
    fee = 0.001
    out = run_backtest_sl_tp(df, signals, out_dir="results/tmp_test_s2_1", init_cash=init_cash, fee=fee, sl_pct=0.05, tp_pct=0.2, skip_reindex=True)
    trades = out["trades"]
    # find the scheduled sell (reason == 'signal_exit')
    sell = None
    for t in trades:
        if t.get("reason") == "signal_exit":
            sell = t
            break
    assert sell is not None, "expected a scheduled sell trade"
    final_cash = float(sell["cash"])
    expected = init_cash * (1 - fee) / (1 + fee)
    # allow small relative tolerance
    assert abs(final_cash - expected) / expected < 1e-6


if __name__ == "__main__":
    test_full_invest_buy_sell_consistent()
    print("ok")
