
这是本系列的第一篇文章，响应我的twitter博文https://x.com/Jerrylee778899/status/1982812330317537293
在这篇博文中，Grok为初学者提供了如下3个量化交易策略的思路以及回测数据源的链接：
## 策略说明（摘要）
MA 交叉：短期 MA=5 上穿长期 MA=20 买入，反向卖出；示例实现适度去噪并禁止 look-ahead。
RSI 超买/超卖：14 日 RSI，<30 买入，>70 卖出（可选择叠加 MA 过滤）。
MACD：参数 (12,26,9)，MACD 线与信号线的上/下穿为买卖信号。

## 策略对应文件
`S1/strategies/ma_crossover.py` — MA(5,20) 策略实现。
`S1/strategies/rsi.py` — RSI(14) 策略实现。
`S1/strategies/macd.py` — MACD(12,26,9) 策略实现。

以上模块均暴露两个函数：
`generate_signals(df) -> pd.Series`：返回与输入 `df` 对齐的 1/0 信号序列（1 表示持仓）。
`backtest(df, signals, out_dir, **kwargs)`：调用统一回测引擎并把结果写入 `out_dir`（见下）。

## 数据源
统一数据源实现：`S1/data.py` 使用 Cryptocompare 日线接口（示例：
`https://min-api.cryptocompare.com/data/v2/histoday?fsym=BTC&tsym=USDT&limit=2000`），并把数据缓存到 `data/raw/btc_daily.csv`。下载器支持按日期范围下载、增量更新及分批（2000 天/批）回填历史数据。

## 如何运行回测
1. 激活虚拟环境并安装依赖（参见仓库根 README）：

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

2. 运行 S1 的统一 runner（示例回测 2021 年）：

```bash
python3 S1/run_all.py --start 2021-01-01 --end 2021-12-31
```

可选：如果想直接使用回测引擎设置起始资金或交易成本，可在 Python 中调用 `S1.backtest.run_backtest(df, signals, out_dir, init_cash=5000, fee=0.002)`。

## 回测方法说明
信号生成：各策略的 `generate_signals` 仅使用当前及更早的历史数据（通过 `.shift(1)` 等方式避免 look-ahead）。
交易执行：回测引擎在 "next-day open" 执行下单（即当日生成信号后，在下一根 K 线的开盘价成交），从而避免使用未来收盘价导致的偏差。
持仓与头寸管理：当前实现采用简单仓位管理——买入时以全部现金买入（全仓），卖出时全部清仓。交易费默认为 `fee=0.001`，可在调用 `run_backtest` 时修改。

## 起始资金与参数
默认起始资金：`init_cash=10000.0`（可通过 `run_backtest` 覆盖）。
交易成本：默认 `fee=0.001`（0.1%），可通过 `run_backtest` 覆盖。

## 如何查看与解释结果
回测结果保存在 `results/s1/<strategy>/`，包含：
`equity.csv`：时间序列（datetime, equity），用于绘制净值曲线。
`metrics.json`：主要指标（total_return、annualized_return、max_drawdown、volatility、sharpe）。
`trades.csv`：逐笔交易明细（datetime、side、price、qty、cash）。
`equity.png` / `drawdown.png`：可直接查看的图像文件。

如何解读：
`total_return`：回测期间的累计收益率（净值结束/开始 - 1）。
`annualized_return`：年化收益率（按实际天数折算）。
`max_drawdown`：最大回撤（负数，越小越糟糕）。
`sharpe`：年化夏普比率（使用无风险率 0 简化计算）。

## 给初学者的简短提示
回测结果只是历史表现，不代表未来收益；务必注意过拟合与样本外验证。
小心数据问题（缺失、时区不一致、列名不标准会导致错误）。本项目强制要求 `['datetime','open','high','low','close','volume']` 且 `datetime` 为 UTC。
若想对比不同起始资金或手续费，请在调用 `run_backtest` 时传入 `init_cash` / `fee` 并记录结果目录。




