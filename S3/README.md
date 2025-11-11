# S3 — 仓位管理（基于 S1 策略，使用 Kelly 公式）

## 概要（系列目标）
- 目标：在已有的 S1 策略（例如 MA 交叉）基础上，引入基于凯利公式的动态仓位管理模块，使每笔交易的仓位按历史胜率与盈亏比估计的 Kelly 比例调整，从而在长期上改善风险调整后的收益（降低回撤、提高收益稳定性）。
- 本系列（S3）包含：Kelly 参数估计工具、回测中对接 Kelly 仓位逻辑、网格敏感性分析脚本、以及复现示例与说明。

- 详细网格分析与可视化报告已保存于 `docs/s3/ma_crossover_kelly_grid.md`（包含 summary.csv、对比图与代表性净值图），可直接在 GitHub 上浏览。

## 凯利公式原理（要点）
- 离散（按单笔交易）Kelly：设 p 为胜率（概率），q = 1 - p；设平均盈利为 g，平均亏损为 l，令 b = g / l（盈亏比）。经典的单笔 Kelly 比例为：

  f* = p - q / b

  解释：当 f* 为正时表示理论上应投入该比例的资金以最大化对数财富增长；当为负时表示不应开仓（空仓或对冲）。该公式适用于独立、同分布且赔率固定的离散交易情形。

- 连续（基于收益率）Kelly：若把每期策略收益视为近似正态分布，记 μ 为策略的期望超额收益（期望回报），σ^2 为收益方差，则连续近似的 Kelly 比例可写为：

  f* = μ / σ^2

  说明：该表达式来自对对数财富增长率的二阶近似，适用于以收益分布直接估计仓位的情形。

- 实务调整（非常重要）：直接使用原始 f* 常因样本噪声、非平稳、交易成本与滑点导致风险过高。常见稳健化处理包括：
  - fractional Kelly：按比例缩放（例如 0.25 或 0.5 Kelly）；
  - EWMA / rolling smoothing：对 f* 进行指数加权或滚动平均以降低短期波动；
  - 上下界约束：对每笔交易设定 min/max allocation（例如 [0, 0.25]）；
  - 将交易成本（手续费、滑点）纳入收益/赔率估计中。

## S3 下的文件与目录（主要项）
- `S3/backtest.py`：S3 专用回测器，支持启用/禁用 Kelly 仓位（参数：`enable_kelly`, `kelly_dir`, `kelly_min_alloc`, `kelly_max_alloc`, `kelly_field` 等）。已处理买卖手续费与现金增量更新（避免覆写现金）。
- `S3/strategies/`：S3 下的策略包装器（例如对 `s1_ma_crossover` 的薄包装），负责把 signal 传入 S3 的回测器。
- `scripts/kelly_estimate.py`：用于根据交易或收益序列计算滚动/连续 Kelly 估计（支持 fractional Kelly、EWMA 平滑、窗口大小等），输出 CSV 与可视化图片到 `results/s3/<strategy>_kelly/`。
- `scripts/compare_kelly_grid.py`：对一组 fractional factors（如 0.25/0.5/1.0）和 `kelly_max_alloc` 值（例如 [0.01,0.05,0.1,0.25,0.5]）做网格回测，汇总 `summary.csv` 并绘制 `return_vs_alloc.png`。
- `tests/test_s2_backtest_cash.py`：单元测试，验证回测器在含手续费情况下的买/卖现金流与 qty 计算正确性。
- `results/`：回测与估计结果输出（默认在 `.gitignore` 中，不会被自动提交）。网格输出示例位置：`results/s3/ma_crossover_compare/grid/summary.csv` 与绘图 `return_vs_alloc.png`。

## 如何运行（快速复现）
前提：在项目根目录下创建并激活虚拟环境，安装依赖（仓库根若已有 `requirements.txt`）：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

常用命令（在仓库根运行）：

- 生成 Kelly 估计（示例，ma_crossover）：

```bash
PYTHONPATH=. python3 scripts/kelly_estimate.py --strategy ma_crossover --window 250 --method continuous --kelly_frac 1.0
```

- 运行 S3 回测（不启用 Kelly，做基线）：

```bash
PYTHONPATH=. python3 -c "from S3.backtest import run_backtest_sl_tp; run_backtest_sl_tp('ma_crossover', enable_kelly=False)"
```

- 运行 S3 回测（启用 Kelly，并指定 kelly 目录）：

```bash
PYTHONPATH=. python3 -c "from S3.backtest import run_backtest_sl_tp; run_backtest_sl_tp('ma_crossover', enable_kelly=True, kelly_dir='results/s3/ma_crossover_kelly', kelly_field='f_smooth', kelly_min_alloc=0.0, kelly_max_alloc=0.25)"
```

- 运行网格比较（会生成 `results/s3/ma_crossover_compare/grid/summary.csv` 与图像）：

```bash
PYTHONPATH=. python3 scripts/compare_kelly_grid.py
```

输出位置（默认）:
- 网格摘要 CSV： `results/s3/ma_crossover_compare/grid/summary.csv`
- 网格图像： `results/s3/ma_crossover_compare/grid/return_vs_alloc.png`
- 单次回测输出： `results/s3/<strategy>_kelly_backtest/`（包含 `equity.csv`, `metrics.json`, `trades.csv` 等）

注意：`results/` 目录通常被 `.gitignore` 忽略。如果你想将最终分析纳入版本控制，我推荐把小型分析文档复制到 `docs/` 或 `reports/` 下再提交（而非把整个 `results/` 强制加入 git）。

## 凯利网格搜索：实验设置与主要发现

实验说明（已执行）：
- 网格参数：
  - fractional factors (缩放 f_smooth)： {0.25, 0.5, 1.0}
  - kelly_max_alloc（对每笔交易允许的最大仓位）： {0.01, 0.05, 0.1, 0.25, 0.5}
- 每个格点运行完整回测并记录指标（total_return、annualized_return、max_drawdown、volatility、sharpe、trades、final_equity 等）。结果保存在 `results/s3/ma_crossover_compare/grid/summary.csv`。

代表性数值摘录（部分行，展示典型 trade-off）：
- run4 (frac=0.25, max_alloc=0.25): total_return ≈ 0.15634，max_drawdown ≈ -0.05783，Sharpe ≈ 0.4862，final_equity ≈ 11563.41
- run10(frac=0.5,  max_alloc=0.5) : total_return ≈ 0.31580，max_drawdown ≈ -0.11307，Sharpe ≈ 0.4838，final_equity ≈ 13157.96
- run14(frac=1.0,  max_alloc=0.25): total_return ≈ 0.12192，max_drawdown ≈ -0.06621，Sharpe ≈ 0.3775，final_equity ≈ 11219.21

结论性分析：
- 更激进的配置（较高的 `kelly_max_alloc` 与较大 frac）通常能提高累计回报与最终净值，但也明显增加最大回撤与波动率——典型的风险/收益权衡。网格显示存在“中间值”较优的情况（例如 frac=0.25 且 max_alloc=0.25 给出了相对较高的 Sharpe 与可控回撤）。
- 直接使用未经缩减的 Kelly（frac=1.0）在多数情形下会导致更高波动及较低或不稳定的 Sharpe，说明估计噪声和样本误差对原始 Kelly 比例的影响很大。

建议（实践可借鉴）：
- 初始默认：fractional Kelly = 0.25，kelly_max_alloc = 0.10 ~ 0.25（视风控偏好）。
- 必须对 `f*` 做平滑（例如 EWMA）与上下界约束，并在回测中包含交易成本与滑点模拟。避免在小样本上直接使用未经平滑的 f*。

## 如何复现网格实验（step-by-step）
1. 激活虚拟环境并安装依赖（参见上方命令）。
2. 生成/缓存所需的价格数据（如果仓库已有 `data/raw/`，跳过）：

```bash
# 如果实现了数据下载器，可运行，例如：
PYTHONPATH=. python3 utils/data_sources/cryptocompare.py --save data/raw/btc_daily.csv
```

3. 计算 Kelly 估计（示例）：

```bash
PYTHONPATH=. python3 scripts/kelly_estimate.py --strategy ma_crossover --window 250 --method continuous --kelly_frac 1.0
```

4. 运行网格比较（默认网格）：

```bash
PYTHONPATH=. python3 scripts/compare_kelly_grid.py
```

5. 查看输出：

```bash
ls results/s3/ma_crossover_compare/grid
# 打开 summary.csv 或 return_vs_alloc.png
```


## 实现与注意事项（工程要点）
- 严格禁止 look-ahead：所有信号只使用当时及之前的数据（信号在 next-open 执行）；Kelly 的估计也只能用历史样本（rolling window/expanding）来近似。
- 费用与现金流：买入时将买方手续费包含在买入成本（qty = invest / (entry_price * (1 + fee))），卖出时将手续费从卖出收益中扣除并用 `cash += proceeds` 累加，避免覆写现金余额。
- 当 Kelly 序列缺失或不可用时，回测可以回退到基线仓位或基于收益的连续估计。代码中已实现安全回退逻辑。
- 边界情况：空数据、缺失列、窗口不足、非常小的波动会导致不稳定估计；代码在输入检查处会抛出带说明的异常。

## 小型“契约”（输入/输出 / 失败模式）
- 输入：标准 OHLCV DataFrame（列 ['datetime','open','high','low','close','volume']，UTC 时区），以及已生成的 `kelly` CSV（包含 datetime 与 `f_smooth` 字段）。
- 输出：回测结果写入 `results/.../`（`equity.csv`, `metrics.json`, `trades.csv`）以及网格 `summary.csv` 与可视化图片。
- 失败模式：缺列、数据太短、window 超出范围时抛异常并提示修复建议。


