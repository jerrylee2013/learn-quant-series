这是本系列的第二篇记录，来源于 twitter（https://x.com/Jerrylee778899/status/1983721492484649154）。


# S1 回测摘要（关键指标）（时间区间：2020-05-07 — 2025-10-28）

| 策略 | total_return | annualized_return | max_drawdown | volatility | sharpe |
|---|---:|---:|---:|---:|---:|
| MA 交叉 (results/s1/ma_crossover/) | +359.7% (3.5967) | 32.10% (0.3210) | -63.07% (-0.6307) | 34.66% (0.3466) | 0.727 |
| RSI (results/s1/rsi/) | +64.97% (0.6497) | 9.57% (0.0957) | -68.36% (-0.6836) | 33.94% (0.3394) | 0.356 |
| MACD (results/s1/macd/) | +418.13% (4.1813) | 35.02% (0.3502) | -52.40% (-0.5240) | 33.46% (0.3346) | 0.785 |

> 注：上述指标来自 `results/s1/<strategy>/metrics.json`。



# S2 — 策略改进计划（止损 / 止盈 等）

## 改进目标（总体方向）

S2 将优先实现下列改进以提升“风险调整后收益”（目标：降低最大回撤并提升或稳定年化收益、提高夏普）：

- 增加风险管理（止损、止盈、仓位限制）。
- 引入趋势过滤（如 200 日均线）以避免在熊市频繁进场。
- 在信号层面加入额外过滤（成交量、RSI/MACD 互证、零轴过滤等）。
- 以实验方式调参（网格搜索或简单回测扫描）并记录每次变更的结果。

## 具体改进建议（来自 Grok，作为 S2 的初始任务列表）

### 通用改进

1. 止损 / 止盈（Stop-Loss / Take-Profit）
	- 示例：固定 5–10% 止损，20–30% 止盈。
	- 作用：在大幅回撤时限制损失，预期能显著降低最大回撤（trade-off：年化可能小幅下降）。

2. 仓位管理
	- 可用 Kelly 公式或简单规则（例如胜率 > 50% 时仓位乘以 1.5；或固定分批建仓）。
	- 作用：减少单笔风险暴露，改善回撤/波动表现。

3. 趋势过滤
	- 仅在 BTC > 200 日均线时允许做多，避免熊市信号。

### 策略级改进（任务级别说明）

#### MA 交叉

- 用 EMA 替换 SMA（提高对价格变动的敏感度）。
- 增加成交量过滤：仅当当日成交量 > 20 日均量时，信号有效。
- 结合 200 日 MA 做趋势过滤（只在多头市场执行买入）。

预期效果（估计）：年化上升 ~5–10%，最大回撤显著下降（示例目标：≤ 40%），夏普提升。

#### RSI 策略

- 动态阈值：在牛市采用更宽松的买入阈值（如 RSI<40 买入，>60 卖出），在熊市反向或更保守。
- 只在价格 > MA50 时才考虑买入（MA 过滤）。
- 加入背离检测（Divergence）作为额外卖出条件。

预期效果：改善年化与回撤，夏普中等提升。

#### MACD 策略

- 零轴过滤：只有当 MACD > 0 时才考虑多头信号，避免在负趋势中回补多头。
- 与 RSI 互证：MACD 买信号 + RSI < 50 做二次确认。
- 尝试参数微调（例如 11,24,8）以提高灵敏度并在样本上进行验证。

预期效果：在保证收益的同时进一步降低回撤，目标夏普 > 1.0（需验证）。

## S2 的成果

下面把 S2 目前完成的两项成果写清楚：

1) 在 S1 基础上引入了 Stop-Loss / Take-Profit（SL/TP）机制

- 目录结构（相关文件）

```
S2/
	backtest.py                # 支持 SL/TP 的日度回测器 (run_backtest_sl_tp)
	strategies/
		ma_crossover.py          # 调用 run_backtest_sl_tp 的封装
		rsi.py
		macd.py
scripts/
	plot_compare.py            # 对比 S1 与 S2 的净值/回撤图（已处理时区对齐）
```

- 主要功能与说明
	- 在 `S2/backtest.py` 中实现 `run_backtest_sl_tp(df, signals, out_dir, ..., sl_pct=0.05, tp_pct=0.2, ...)`。
	- 执行语义：信号 0->1 的下一交易日开仓；信号 1->0 的下一交易日开仓卖出；入场当天会用当日 high/low 检查是否触及 SL/TP（若同日同时触及，保守假设先触及 SL）。
	- 默认参数：`sl_pct=0.05`（5%），`tp_pct=0.20`（20%）。这些默认值同时在各策略的 `backtest` 函数签名中体现（例如 `S2/strategies/ma_crossover.py`）。

- 如何复现（单点）

```bash
source .venv/bin/activate
python3 -c "import pandas as pd; from S2.strategies.ma_crossover import backtest; df=pd.read_csv('data/raw/btc_daily.csv', parse_dates=['datetime']); backtest(df, out_dir='results/s2/ma_crossover_test', sl_pct=0.05, tp_pct=0.2)"
```

运行后会在 `results/s2/ma_crossover_test/` 生成 `equity.csv`、`metrics.json`、`trades.csv`（若有交易）。

2) 完成了 SL/TP 参数的网格搜索与 Pareto 分析

- 目录结构（相关文件）

```
scripts/
	s2_grid_search.py          # 新增：对 SL/TP 网格批量回测并产出 Pareto 分析
results/
	s2/
		experiments_grid.csv     # 网格搜索结果汇总（生成）
		pareto_table.csv         # Pareto 前沿表（生成）
		pareto_front.png         # Pareto 可视化图（生成）
		<strategy>_slX_tpY/      # 每个组合的回测产物（equity.csv, metrics.json, trades.csv）
results/figs/
	*_equity_compare.png       # 比较图（可选）
```

- 主要功能与说明
	- 脚本 `scripts/s2_grid_search.py` 在默认网格 sl ∈ [0.03,0.05,0.08]，tp ∈ [0.10,0.20,0.30] 上对三条策略依次运行回测。
	- 每次试验将指标（total_return、annualized_return、max_drawdown、volatility、sharpe 等）汇总到 `results/s2/experiments_grid.csv`。
	- 基于年化收益（越大越好）和最大回撤（越接近 0 越好）计算 Pareto 前沿，结果写入 `results/s2/pareto_table.csv` 并画图保存在 `results/s2/pareto_front.png`。

- 如何复现（整个网格）

```bash
source .venv/bin/activate
python3 scripts/s2_grid_search.py
```

脚本运行结束后会在 `results/s2/` 下生成 `experiments_grid.csv`、`pareto_table.csv`、`pareto_front.png`，以及每个参数组合对应的回测目录（例如 `results/s2/macd_sl5_tp30/`）。

（注）如果要更细的网格或并行加速，可修改 `scripts/s2_grid_search.py` 中的 `SL_GRID` / `TP_GRID` 并在需要时用多进程并行执行。




