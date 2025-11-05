# 跟着AI学量化交易：系列二 策略改进--止损/止盈 
本章介绍在 S1 基础上对三条策略（MA 交叉、RSI、MACD）做出的改进计划与实现，重点是引入止损/止盈（SL/TP）机制以提升风险调整后收益表现。


## 成果说明

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




