这是本系列的第一篇文章，响应我的twitter博文https://x.com/Jerrylee778899/status/1982812330317537293
在这篇博文中，Grok为我们提供了如下3个量化交易策略的思路以及回测数据源的链接：
# 策略说明（摘要）
MA 交叉：短期 MA=5 上穿长期 MA=20 买入，反向卖出；示例实现适度去噪并禁止 look-ahead。
RSI 超买/超卖：14 日 RSI，<30 买入，>70 卖出（可选择叠加 MA 过滤）。
MACD：参数 (12,26,9)，MACD 线与信号线的上/下穿为买卖信号。
以上3个策略将成为我们的第一系列（S1），本文档记录了 S1 的基线实现细节与使用说明。

# S1 — 基线实现（MA / RSI / MACD）

本目录实现了 S1 系列的最小可运行基线：数据获取、三条策略（MA 交叉、RSI、MACD）与统一回测引擎。目标是为我们提供可复现的端到端回测流水线。

快速链接：

- 策略实现：`S1/strategies/`（`ma_crossover.py`、`rsi.py`、`macd.py`）
- 数据适配器：`S1/data.py`（Cryptocompare 日线，缓存到 `data/raw/btc_daily.csv`）
- 回测引擎：`S1/backtest.py`（统一接口、写出 `results/`）
- Runner：`S1/run_all.py`（按策略批量运行并写入 `results/s1/<strategy>/`）

## 策略概要

- MA 交叉（MA short=5 / MA long=20） — 买入条件：`ma5.shift(1) <= ma20.shift(1)` 且 `ma5 > ma20`；卖出为反向条件。实现避免 look-ahead。
- RSI（period=14） — 超卖买入（RSI<30）、超买卖出（RSI>70）；可选 MA 过滤减少噪音。
- MACD（12,26,9） — MACD 线与信号线的上穿/下穿为买卖信号。

每个策略模块遵循统一约定：

- `generate_signals(df) -> pd.Series`：返回与输入数据对齐的持仓信号（1=持仓，0=空仓）。
- `backtest(df, signals, out_dir, **kwargs)`：调用统一回测逻辑并把结果输出到 `out_dir`。

## 数据（来源与缓存）

数据接口使用 Cryptocompare 的日线 API（示例：`/data/v2/histoday?fsym=BTC&tsym=USDT&limit=2000`）。

实现要点：

- 缓存位置：`data/raw/btc_daily.csv`（包含标准列 `['datetime','open','high','low','close','volume']`，且 `datetime` 以 UTC 表示）。
- 支持增量更新与历史分批填充（2000 天/批），以避免重复下载与超长请求。
- 输入校验：缺少必需列或空数据会抛出友好错误，便于排查。

## 快速开始（本地运行示例）

1. 创建并激活虚拟环境，安装依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. 运行 S1 runner（示例：回测 2021 年）：

```bash
python3 S1/run_all.py --start 2021-01-01 --end 2021-12-31
```

参数说明（常用）：

- `--start`/`--end`：回测时间窗口（可选）。
- `--no-update`：仅使用本地缓存数据，不触发网络下载。适合离线回测或 CI。

也可以在 Python 中直接调用回测接口：

```python
from S1 import backtest
# df：已加载的 OHLCV 数据
# signals：由策略 generate_signals 返回的 Series
backtest.run_backtest(df, signals, out_dir="results/s1/example", init_cash=10000, fee=0.001)
```

## 回测引擎要点

- 信号无 look-ahead：策略生成信号时仅使用当前及之前数据（实现上使用 `.shift(1)` 或等价手段）。
- 订单执行：基于“next-day open”成交（当天信号在下一根 K 线以开盘价执行），避免使用未来收盘价。
- 头寸管理（当前 baseline）：全仓买入 / 全部清仓卖出；可通过 `init_cash`、`fee` 等参数调整。未来迭代会增加仓位管理与滑点模型。

默认参数：

- `init_cash` = 10000.0
- `fee` = 0.001（0.1% 单边交易费）

## 回测输出（results）

回测结果写入：`results/s1/<strategy>/`，包含：

- `equity.csv`：时间序列（datetime, equity）
- `metrics.json`：关键指标（total_return、annualized_return、max_drawdown、volatility、sharpe）
- `trades.csv`：逐笔交易明细（datetime、side、price、qty、cash）
- `equity.png`、`drawdown.png`：默认生成的可视化图片

要点提示：

- `total_return` = (equity_end / equity_start) - 1
- `annualized_return`：按实际交易天数年化
- `max_drawdown`：最大历史回撤（负数表示跌幅）
- `sharpe`：简化年化夏普（使用 0 作为无风险收益率）

## 开发者与调试提示

- 保证数据列与时区正确（UTC）。
- 若策略出现异常信号或 NaN，先用 `df.tail()` 检查最近若干行是否包含缺失值或重复索引。
- 为避免 look-ahead，务必在信号逻辑中使用 `.shift(1)` 检查前一根 bar 的交叉状态或直接在已知历史上进行回测验证。

## 风险提示
本项目仅供学习与研究使用，不构成任何投资建议。加密货币市场波动剧烈，实际交易风险极高。请在充分理解风险的前提下谨慎操作。


