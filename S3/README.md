```markdown
# S3 — 仓位管理（基于 S1 策略，使用 Kelly 公式）

目标：在 S1 的基础策略上加入基于凯利公式（Kelly criterion）的仓位管理模块，使仓位按历史绩效动态调整，以期长期降低回撤并提高风险调整后收益。S3 提供原理说明、参数估计方法、回测集成步骤、伪代码示例以及实务建议和复现命令。

## 1. 简短结论
- Kelly 公式给出理论上长期最大化对数财富增长的仓位比例 f*；但估计噪声、交易成本和样本偏差会导致直接使用 f* 风险过大。实务上使用 fractional Kelly（例如 1/4 或 1/2 Kelly）并加上下限/上限、平滑与监控，是更稳健的做法。

## 2. 基本概念和公式
- 离散（胜/负、按交易）形式（适合以“每笔交易盈亏”为单位的估计）:
  - 设 p = 胜率（赢的概率），q = 1-p；g = 平均盈利（正数），l = 平均亏损（正数）；令 b = g/l。
  - Kelly: f* = p - q / b

- 连续（均值-方差近似，适合按日收益或连续收益序列）:
  - 设 μ = 期望超额收益（同一时间尺度），σ^2 = 收益方差。
  - Kelly（近似）: f* = μ / σ^2

说明：f* 表示建议投入的资金比例（占总资金）。若为负，表示不应开仓；若 >1，暗示理论上可杠杆，但实际通常受限。
# S3 — 基于 Kelly 的仓位管理（概要与复现指南）

本目录实现并实验了在 S1 策略基础上加入基于凯利公式（Kelly criterion）的仓位管理（称作 S3）。目标是提供一套可复现的流水线：

- 从回测数据滚动估计 Kelly 比例（离散交易层面或连续收益层面）；
- 在回测中按估计比例调整仓位（支持 fractional Kelly、上下限和平滑）；
- 提供网格敏感性分析与结果输出，便于在风险—收益间做权衡。

## 1. 简短结论

- Kelly 公式理论上最大化对数财富增长，但直接使用 f* 在样本噪声、成本与偏差存在时常导致过度波动或风险暴露。实务上推荐：fractional Kelly（如 0.25–0.5）、上下限（`max_alloc`）、以及对 f 的 EWMA 平滑，从而获得更稳健的风险—收益表现。

## 2. S3 的文件与目录（核心）

- `S3/backtest.py` — S3 专用回测器（在 S2 的基础上扩展），新增参数支持：`enable_kelly`, `kelly_dir`, `kelly_field`, `kelly_min_alloc`, `kelly_max_alloc`, `kelly_frac`, `smoothing_alpha` 等。修正了买入/卖出时手续费与 cash 更新的实现，避免 cash 被覆盖的 bug。
- `S3/strategies/` — 每个策略的 S3 包装器（如 `ma_crossover.py`），调用 S3 回测器并写入 `results/s3/<strategy>_.../`。
- `scripts/kelly_estimate.py` — 滚动估计 Kelly（离散或连续方法），输出 `results/s3/<strategy>_kelly/kelly_returns_rolling.csv` 和可视化 PNG。
- `scripts/compare_kelly_grid.py` — 网格实验脚本（不同 `kelly_max_alloc` 与 frac），会生成：
   - `results/s3/<strategy>_compare/grid/summary.csv`
   - `results/s3/<strategy>_compare/grid/return_vs_alloc.png`
   - 每个格点的回测子目录（包含 `equity.csv`, `metrics.json`, `trades.csv`）
- `results/s3/` — 存放 S3 的回测结果与估计输出。

注意：所有数据/输出遵循仓库约定（`data/raw/`、`data/processed/`、`results/`），时间列统一为 `datetime`（UTC）。

## 3. 快速运行 / 复现步骤

先决条件：在仓库根建立并激活虚拟环境，安装依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

步骤：

1) 准备数据（确保 `data/raw/btc_daily.csv` 可用，包含 ['datetime','open','high','low','close','volume']，时区 UTC）。

2) 生成 Kelly 估计（示例：对 ma_crossover 做 100 日/笔滚动估计）：

```bash
python3 scripts/kelly_estimate.py --strategy ma_crossover --window 100 --kelly_frac 0.25
```

输出：`results/s3/ma_crossover_kelly/kelly_returns_rolling.csv` 和 PNG 图像。

3) 运行 baseline 回测（不启用 Kelly）：

```bash
PYTHONPATH=. python3 -c "import pandas as pd; from S3.strategies.ma_crossover import backtest; df=pd.read_csv('data/raw/btc_daily.csv',parse_dates=['datetime']); out=backtest(df, out_dir='results/s3/ma_crossover_baseline', enable_kelly=False); print(out['metrics'])"
```

4) 运行 Kelly-enabled 回测（示例：使用上一步生成的 kelly_dir，f_smooth 字段，max_alloc=0.25）：

```bash
PYTHONPATH=. python3 -c "import pandas as pd; from S3.strategies.ma_crossover import backtest; df=pd.read_csv('data/raw/btc_daily.csv',parse_dates=['datetime']); out=backtest(df, out_dir='results/s3/ma_crossover_kelly_backtest', enable_kelly=True, kelly_dir='results/s3/ma_crossover_kelly', kelly_min_alloc=0.0, kelly_max_alloc=0.25, kelly_field='f_smooth'); print(out['metrics'])"
```

5) 运行网格实验（示例脚本）：

```bash
PYTHONPATH=. python3 scripts/compare_kelly_grid.py
```

输出会写入 `results/s3/ma_crossover_compare/grid/`（包含 `summary.csv` 与 `return_vs_alloc.png`）。

## 4. S3 与 S1 的对比（概括与示例结果）

在一次示例实验中（ma_crossover）：

- Baseline（S1 风格回测，不使用 Kelly）：
   - total_return ≈ +69.04%（final_equity ≈ 16904），annualized ≈ 10.05%，max_drawdown ≈ -42.19%，volatility ≈ 23.24%，Sharpe ≈ 0.399，trades=120。
- Kelly-enabled（使用 precomputed `f_smooth`，kelly_max_alloc=0.25）：
   - total_return ≈ +12.19%（final_equity ≈ 11219），annualized ≈ 2.12%，max_drawdown ≈ -6.62%，volatility ≈ 4.05%，Sharpe ≈ 0.377，trades=119。

结论：启用 Kelly（并配合 fractional/上限/平滑）在此样本上显著降低了最大回撤与波动，但也降低了绝对收益，体现了风险—收益的权衡。不同的 `kelly_max_alloc` 与 `kelly_frac` 会在这两者之间移动，网格实验（`scripts/compare_kelly_grid.py`）用于量化这一权衡并选取适合的参数点。

## 5. 复现实验注意事项与工程保证

- 禁止 look-ahead：所有信号与 Kelly 估计仅使用历史数据（signal -> next-day open）。
- 费用与现金处理：S3 回测已把买入费用计入买入成本，并在卖出时把手续费从卖出所得中扣除（并把卖出所得加入 cash），避免 cash 被覆盖导致的 wipeout。已将同样的修正同步到 `S2/backtest.py`。
- 单元测试：仓库包含针对回测现金/qty 行为的测试（例如 `tests/test_s2_backtest_cash.py`），用于捕捉买/卖时 cash 处理的回归。

