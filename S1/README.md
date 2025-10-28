
这是本系列的第一篇文章，响应我的twitter博文https://x.com/Jerrylee778899/status/1982812330317537293
在这篇博文中，Grok为初学者提供了如下3个量化交易策略的思路以及回测数据源的链接：
## 策略说明
### MA交叉
趋势反转神器。短期MA（5日）上穿长期MA（20日）买入，下穿卖出。适合BTC周线，只需2指标，低资源。
### RSI超买超卖
RSI超买超卖：防追高杀跌。RSI>70卖，<30买（14日周期，日线算）。加MA过滤假信号，震荡市利器。
### MACD趋势跟随
动量+趋势。MACD线（12,26,9）上穿信号线买入，下穿卖出。BTC回测年化≈15%！

## 回测数据源
免费数据源：https://min-api.cryptocompare.com/data/v2/histoday?fsym=BTC&tsym=USDT&limit=2000

## 项目目标
基于上述策略和数据源，通过vscode的copilot让ai大模型使用python语言实现策略程序并给出回测结果。



