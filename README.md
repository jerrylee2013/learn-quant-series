
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

# 运行 S1 系列回测示例（例如回测 2021 全年）
python3 S1/run_all.py --start 2021-01-01 --end 2021-12-31
```

说明：工程依赖放在 `requirements.txt`，目前包含常用的量化与数据分析包（pandas、numpy、matplotlib、backtrader、yfinance 等）。

## 项目目录结构（当前约定）
仓库采用模块化结构以便逐步扩展，主要目录说明如下：

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

## 快速开始
1. 克隆仓库并进入目录。
2. 按上面的环境设置创建虚拟环境并安装依赖。
3. 运行 S1 runner 示例：

```bash
python3 S1/run_all.py --start 2021-01-01 --end 2021-12-31
```

回测结果将保存在 `results/s1/<strategy>/` 中。

