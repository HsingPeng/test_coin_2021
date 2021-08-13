# test_coin_2021

## 依赖

- 国内无法连接okex，可以买个香港阿里云
- 系统里需要 python3
- pip3 install requests
- pip3 install websockets
- pip3 install asyncio
- pip3 install pysocks
- pip3 install pandas
- pip3 install matplotlib
- pip3 install ccxt
- pip3 install pyecharts
- pip3 install epoll
- pip3 install websocket-client

国内安装依赖比较慢，换源教程：https://www.jianshu.com/p/142bb83746e5

## 项目

### 三角套利

目录 triangle_signal

triangle_deal_pairs.py 三角套利，可运行版本

1. cp conf.py.template conf.py
2. 把okex的api密钥填写到 conf.py
3. python3 triangle_deal_pairs.py

日志在 main.log

### 网格 + 马丁

马丁规则：
- 根据当前价位计算1%的价格。
- 每下跌1%，按1倍数买入开仓数量。
- 每回调1%就卖出全部数量。不回调则继续按倍数买入开仓数量。
- 根据当前价格重置1%的价格。

如果网格最大支持10%回调。只要10%里面，有一次1%的回调，就能盈利。

#### 回测代码目录 grid_martin

binance 数据回测，报表

#### 实盘代码目录 grid_spot_trade

binance 实盘

grid_spot_trade.py 不等回调
grid_spot_num_trade.py 会等待回调

### 中性策略1（网格 + 马丁衍生策略）

在 trade_frame

trade_frame 是一个支持成交单级别的回测和实盘框架，已支持binance。

网格 + 马丁 衍生策略位置：strategy/spot_neutral_1.py

### 资金费套利

swap_rate_monitor_okdex.py okex监控永续资金费率
