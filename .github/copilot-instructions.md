```markdown
# Copilot 指南 — learn-quant-series

## 项目概览（来自 `README.md` / `S1/README.md`）
本仓库以“使用大模型（ChatGPT / Grok / Copilot）辅助学习量化交易”为核心，目标是把从需求整理、代码设计、实现、回测到结果展示的整个学习过程记录并产出可复用代码与文档。第一个系列（`S1/README.md`）列出了三种示例策略（MA 交叉、RSI、MACD）和用于回测的 BTC 日线免费数据源。

## 本文件的用途（对 AI 代理的具体指令）
- 阅读并理解 `S1/README.md` 中的策略与数据源说明。
- 优先生成可运行的最小实现（MVP）：包含数据获取、信号生成、回测 runner、结果导出与至少一条单元/集成测试。

## 仓库约定（AI 应遵守的具体规则）
- 数据位置与格式：
  - 原始数据放 `data/raw/`（CSV 或 Parquet），处理后数据放 `data/processed/`。
  - 必须包含列：['datetime','open','high','low','close','volume']，时区统一为 UTC。
- 策略模块约定：每个策略放 `strategies/`，模块应至少暴露两个函数：
  - `generate_signals(df) -> pd.Series`（返回每个 bar 的持仓信号或交易信号）
  - `backtest(df, signals) -> dict`（运行回测并返回结果字典，包含净值序列与指标）
- 回测输出格式：写入 `results/<series>/<strategy>/`，包含 `equity.csv`（时间、净值）、`metrics.json`（主要指标）与若干图片（净值曲线、回撤图等）。

## S1 中的策略（摘自 `S1/README.md`，AI 实现时可直接参考）
- MA 交叉：短期 MA=5，长期 MA=20；示例信号（无 look-ahead）：
  - buy: 当 ma5.shift(1) <= ma20.shift(1) 且 ma5 > ma20
  - sell: 反向条件
- RSI：14 日周期，超买 >70 卖出，超卖 <30 买入；建议叠加 MA 过滤噪音信号。
- MACD：参数 (12,26,9)，MACD 线向上穿越信号线作为买入信号，向下穿越为卖出信号。
- 推荐数据源示例：
  - Cryptocompare 日线接口：
    https://min-api.cryptocompare.com/data/v2/histoday?fsym=BTC&tsym=USDT&limit=2000

## 最小可运行开发流程（可复制粘贴）
1. 在仓库根目录创建虚拟环境并安装依赖（请在仓库根添加 `requirements.txt`）：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. 推荐的开发顺序（AI 代理可按此顺序自动执行）：
  - 实现 `utils/data_sources/cryptocompare.py`：负责下载、解析并缓存 BTC 历史日线到 `data/raw/`。
  - 实现 `strategies/s1_ma_crossover.py`：包含 `generate_signals`（基于 ma5/ma20）和 `backtest`（简单市值/等权回测、含交易成本配置）。
  - 添加测试 `tests/test_s1_ma_crossover.py`：使用小样本（例如 100 条）验证信号边界与无 look-ahead。
  - 将回测结果写入 `results/s1/ma_crossover/`，包括 `equity.csv`、`metrics.json` 和图像（PNG）。

## 校验与验收要点（AI 生成代码必须满足）
1. 严格禁止 look-ahead：所有信号只使用当前及之前的历史数据。
2. 可重复执行：在干净环境下运行脚本会产出 `results/` 下的文件。
3. 错误处理：对缺失列/空数据抛出带说明的异常，输入检查明确友好。
4. 单元测试：至少包含 1 个正常路径测试与 1 个边界条件测试。

## AI 协作提示（提升实用性与可维护性）
- 优先产出小而完整的单元（MVP），并通过小步迭代完善（实现 -> 测试 -> 文档 -> 可视化）。
- 在生成数据访问代码时加入重试、超时与本地缓存（例如在 `data/raw/` 保存原始响应）。
- 将关键参数（MA 长短、RSI 周期、交易成本等）放在模块顶部的常量或配置文件中，便于调参与测试。
- 在回测结果中至少计算并输出：累计收益、年化收益、最大回撤、夏普比率。

## 常见问题与注意事项
- 数据列名与时区不一致会导致回测结果错误，务必统一为 UTC 并按列名约定检查输入。
- 回测应考虑交易成本和滑点，默认在回测配置中提供可调整的成本参数。
- 不要一次性生成复杂框架；先实现单个策略的端到端可运行版本，再抽象出公共模块。

## 示例下一步（建议）
- 优先实现 `strategies/s1_ma_crossover.py` 的最小可运行版本并提交 PR；实现应包含数据下载器、信号生成、简单回测与一条测试。

如果你希望我现在就实现 S1 的 MA 策略（包含测试与结果导出），请回复“请实现 S1 MA 策略”，我会接着创建相应的文件并在本地运行基本验证。

```
```markdown
# Copilot 指南 — learn-quant-series

## 项目概览（来自 `README.md` / `S1/README.md`）
本仓库以“使用大模型（ChatGPT / Grok / Copilot）辅助学习量化交易”为核心，目标是把从需求整理、代码设计、实现、回测到结果展示的整个学习过程记录并产出可复用代码与文档。第一个系列（`S1/README.md`）列出了三种示例策略（MA交叉、RSI、MACD）和 BTC 的免费日线回测数据源。

## 本文件的用途（对 AI 代理的具体指令）
- 读懂 `S1/README.md` 中的策略与数据源，优先生成最小可运行（MVP）实现。
- 输出的交付物应包含：策略脚本（`strategies/`）、回测 runner（`backtesting/`）、结果（`results/`）与一个简单的验证测试（`tests/`）。

## 关键仓库约定（可被 AI 直接遵循）
- 数据位置与格式：`data/raw/` 存原始下载数据（CSV/Parquet），`data/processed/` 存清洗后的 DataFrame；标准列为 ['datetime','open','high','low','close','volume']，时区 UTC。
- 策略模块约定：每个策略放 `strategies/`，模块应暴露 `generate_signals(df) -> pd.Series` 和 `backtest(df, signals) -> result_dict`。
- 结果与可视化：回测输出写入 `results/<series>/<strategy>/`，包含 `equity.csv`、`metrics.json` 与若干图像 `*.png`。

## S1 示例策略（直接摘自 `S1/README.md`，AI 可据此实现）
- MA 交叉：短期 MA=5, 长期 MA=20，信号示例：`if ma5.shift(1) <= ma20.shift(1) and ma5 > ma20: buy`。
- RSI：14 日，超买 >70 卖出，超卖 <30 买入，建议加 MA 过滤假信号。
- MACD：参数 (12,26,9)，MACD 上穿信号线买入。
- 推荐回测数据源（示例）：https://min-api.cryptocompare.com/data/v2/histoday?fsym=BTC&tsym=USDT&limit=2000

## 开发与运行最小流程（复制粘贴即可）
1. 在仓库根目录创建虚拟环境并安装依赖（请在仓库根添加 `requirements.txt`）：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. 快速开发步骤（AI 推荐顺序）：
  - 实现 `utils/data_sources/cryptocompare.py`：下载并缓存 BTC 历史日线到 `data/raw/`。
  - 实现 `strategies/s1_ma_crossover.py`：`generate_signals` + 简单回测 `backtest`。
  - 添加测试 `tests/test_s1_ma_crossover.py`：用 100 条样本数据校验信号数量与边界条件。
  - 将回测结果写到 `results/s1/ma_crossover/` 并在 `notebooks/` 中画图。

## 校验与验收要点（AI 生成代码必须满足）
1. 无 look-ahead：信号仅使用当前及之前的历史数据（禁止访问未来 bar）。
2. 可重复跑：在干净环境下运行脚本会产出 `results/` 下的文件。 
3. 错误处理：对缺失列/空数据给出清晰异常。
4. 基本单测：包含 1 个 happy-path 测试和 1 个边界测试。

## AI 协作提示（高效产出）
- 优先实现小而完整的单元（MVP），并以可运行例子为中心迭代。
- 在 PR 描述中引用 `S1/README.md` 中的策略条目与数据源链接。
- 生成代码时把关键参数（例如 MA 长短、RSI 周期、交易成本）放到模块开头的常量或配置文件，方便后续调参。

## 小结与下一步建议
- 当前仓库已写入 `S1/README.md` 的策略方向，下一步优先实现 `strategies/s1_ma_crossover.py` 的最小可运行版并提交 PR。若你希望我现在立即实现并在本地验证，请回复 “请实现 S1 MA 策略”，我会在同一分支下创建实现、测试与结果目录。

```# Copilot Instructions for learn-quant-series

## Project Overview
This repository documents a beginner's journey in learning quantitative trading. The project will evolve to include tutorials, code examples, backtesting frameworks, and trading strategies implemented in Python.

## Architecture Patterns

### Expected Directory Structure
As the project develops, maintain this structure:
```
├── tutorials/           # Step-by-step learning materials
├── strategies/          # Trading strategy implementations
├── data/               # Market data and datasets
├── backtesting/        # Backtesting frameworks and utilities
├── notebooks/          # Jupyter notebooks for analysis
├── utils/              # Common utilities and helpers
└── tests/              # Unit and integration tests
```

### Data Management
- Store raw market data in `data/raw/` with standardized formats (CSV, Parquet)
- Keep processed/cleaned data in `data/processed/`
- Use consistent datetime indexing (UTC timezone)
- Implement data validation for OHLCV (Open, High, Low, Close, Volume) data

### Strategy Development
- Each strategy should inherit from a base `Strategy` class
- Include mandatory methods: `generate_signals()`, `calculate_returns()`, `get_positions()`
- Store strategy parameters in configuration files (YAML/JSON)
- Document entry/exit rules and risk management clearly

## Development Workflow

### Python Environment
- Use virtual environments (venv or conda)
- Pin dependency versions in `requirements.txt`
- Common dependencies: pandas, numpy, matplotlib, yfinance, backtrader, zipline

### Code Style
- Follow PEP 8 conventions
- Use type hints for function parameters and returns
- Docstrings should follow NumPy/Google format
- Variable names should be descriptive: `close_price` not `cp`

### Testing Strategy
- Test backtesting logic with known datasets
- Mock external data sources in tests
- Validate strategy returns against expected benchmarks
- Include edge cases (market crashes, low volume periods)

## Quantitative Trading Specifics

### Data Sources Integration
- When adding new data sources, create adapters in `utils/data_sources/`
- Standardize column names: `['datetime', 'open', 'high', 'low', 'close', 'volume']`
- Handle missing data and market holidays consistently
- Cache expensive data operations

### Performance Metrics
- Always calculate: Sharpe ratio, maximum drawdown, total return, volatility
- Include benchmark comparisons (S&P 500, relevant sector indices)
- Generate performance tearsheets using standard libraries (pyfolio, quantstats)
- Store results in `results/` with timestamps

### Risk Management
- Implement position sizing rules in all strategies
- Set maximum portfolio allocation per trade (typically 5-10%)
- Include stop-loss and take-profit mechanisms
- Monitor correlation between positions

## Documentation Standards
- Each tutorial should include: objective, prerequisites, key concepts, code examples
- Strategy documentation must include: hypothesis, parameters, expected performance, risks
- Use Jupyter notebooks for educational content with clear explanations
- Include visualization for all key concepts (price charts, performance graphs)

## Common Pitfalls to Avoid
- Never look-ahead bias in backtesting (don't use future data)
- Account for transaction costs and slippage in performance calculations
- Validate data quality before using in strategies
- Don't overfit strategies to historical data
- Consider market regime changes when evaluating long-term strategies

## Example Implementations
When creating new strategies or tutorials, reference existing patterns in:
- `strategies/moving_average_crossover.py` (when implemented)
- `tutorials/01_data_acquisition.ipynb` (when implemented)
- `backtesting/base_backtest.py` (when implemented)