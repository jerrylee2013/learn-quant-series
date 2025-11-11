
# learn-quant-series

这个仓库将记录小白如何通过 AI 大模型学习量化交易的进阶过程。

## 项目目标
1. 使用 ChatGPT、Grok 等大模型，学习量化交易的基础知识和进阶技巧，初期主要以加密货币（BTC）为示例。
2. 利用大模型完成策略从需求整理、代码设计、实现、回测到结果展示的全流程。
3. 将学习过程中的代码与文档整理成可复用的教学资料并输出可视化回测结果。

通过本项目，目标是帮助量化初学者借助大模型快速搭建并验证交易策略。

## 环境设置（Python）
建议在仓库根创建并使用虚拟环境，安装工程依赖：

```bash
# 在 macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

说明：工程依赖放在 `requirements.txt`，目前包含常用的量化与数据分析包（pandas、numpy、matplotlib、backtrader、yfinance 等）。

## 项目目录结构（当前约定）
仓库采用模块化结构以便逐步扩展，主要目录说明如下：

```
```
.
├── .github/                      # CI / copilot 指南（.github/copilot-instructions.md）
├── S1/                           # 第 1 个系列：策略实现、回测与数据适配
│   ├── data.py                   # 数据下载与缓存（Cryptocompare）
│   ├── backtest.py               # 简易回测引擎（净值、指标、图像输出）
│   ├── run_all.py                # 运行器：对 S1 中的策略批量回测
│   └── strategies/               # S1 的具体策略实现（ma_crossover, rsi, macd）
├── data/                         # 数据目录（`data/raw/`、`data/processed/`）
├── results/                      # 回测结果（按系列/策略保存 equity.csv, metrics.json, png）
├── requirements.txt              # Python 依赖清单
├── .gitignore
└── README.md
```

开发约定（摘要）：
- 原始数据存放 `data/raw/`，处理后放 `data/processed/`；时间列必须为 `datetime` 且为 UTC。 
- 每个策略放在 `strategies/`，至少实现：
	- `generate_signals(df) -> pd.Series`（返回 1/0 信号序列）
	- `backtest(df, signals) -> dict` 或调用公共回测器输出结果至 `results/`。
- 回测输出目录格式：`results/<series>/<strategy>/`，包含 `equity.csv`、`metrics.json`、`trades.csv`、`equity.png`、`drawdown.png`。


## 学习进度
下面会根据学习的进度进行更新。每个主题是一个系列，我会单独创建子目录并在 README 中记录实现细节与使用说明。比如S1代表第一个系列。

### 系列一 基础策略实现与回测
#### 简介
该系列实现了三种基础量化交易策略（MA 交叉、RSI、MACD），并基于 Cryptocompare 的 BTC 日线数据进行了回测。

更多细节与代码参见：`S1/README.md`

#### 回测成果
这里列出系列一中3个策略的回测摘要（关键指标）（时间区间：2020-05-07 — 2025-10-28）

| 策略 | total_return | annualized_return | max_drawdown | volatility | sharpe |
|---|---:|---:|---:|---:|---:|
| MA 交叉 (results/s1/ma_crossover/) | +359.7% (3.5967) | 32.10% (0.3210) | -63.07% (-0.6307) | 34.66% (0.3466) | 0.727 |
| RSI (results/s1/rsi/) | +64.97% (0.6497) | 9.57% (0.0957) | -68.36% (-0.6836) | 33.94% (0.3394) | 0.356 |
| MACD (results/s1/macd/) | +418.13% (4.1813) | 35.02% (0.3502) | -52.40% (-0.5240) | 33.46% (0.3346) | 0.785 |

#### 改进建议（来自Grok）

##### 通用改进
1. 止损 / 止盈（Stop-Loss / Take-Profit）
	- 示例：固定 5–10% 止损，20–30% 止盈。
	- 作用：在大幅回撤时限制损失，预期能显著降低最大回撤（trade-off：年化可能小幅下降）。
2. 仓位管理
	- 可用 Kelly 公式或简单规则（例如胜率 > 50% 时仓位乘以 1.5；或固定分批建仓）。
	- 作用：减少单笔风险暴露，改善回撤/波动表现。
3. 趋势过滤
	- 仅在 BTC > 200 日均线时允许做多，避免熊市信号。

##### 策略专项改进
- MA 交叉：
	- 用 EMA 替换 SMA（提高对价格变动的敏感度）。
	- 增加成交量过滤：仅当当日成交量 > 20 日均量时，信号有效。
	- 结合 200 日 MA 做趋势过滤（只在多头市场执行买入）。

	预期效果（估计）：年化上升 ~5–10%，最大回撤显著下降（示例目标：≤ 40%），夏普提升。
- RSI：
	- 动态阈值：在牛市采用更宽松的买入阈值（如 RSI<40 买入，>60 卖出），在熊市反向或更保守。
	- 只在价格 > MA50 时才考虑买入（MA 过滤）。
	- 加入背离检测（Divergence）作为额外卖出条件。

	预期效果：改善年化与回撤，夏普中等提升。
- MACD：
	- 零轴过滤：只有当 MACD > 0 时才考虑多头信号，避免在负趋势中回补多头。
	- 与 RSI 互证：MACD 买信号 + RSI < 50 做二次确认。
	- 尝试参数微调（例如 11,24,8）以提高灵敏度并在样本上进行验证。

	预期效果：在保证收益的同时进一步降低回撤，目标夏普 > 1.0（需验证）。

后续的系列中，我们将逐项实现上述改进，并对比回测结果。

### 系列二 止盈止损对策略的影响
1. 加入了止损/止盈（SL/TP）的功能
2. 止盈止损参数网格搜索，寻找合适的止盈止损参数配置

更多细节与代码参见：`S2/README.md`

### 系列三 仓位管理对策略的影响
1. 本系列介绍在 S1 引入仓位管理机制以提升策略的风险调整后收益表现。
2. 基于 Kelly 公式的仓位管理网格搜索与分析

更多细节与可视化报告参见：`S3/README.md` 或 `docs/s3/ma_crossover_kelly_grid.md`
	- 网格分析与可视化报告（包含 summary.csv 与代表性图片）：`docs/s3/ma_crossover_kelly_grid.md`
