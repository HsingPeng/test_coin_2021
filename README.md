# test_coin_2021

## 依赖

- 国内无法连接okex，可以买个香港阿里云
- 系统里需要 python3
- pip3 install requests
- pip3 install websockets
- pip3 install asyncio

## 执行
triangle_deal_pairs.py 三角套利，可运行版本

1. cp conf.py.template conf.py
2. 把okex的api密钥填写到 conf.py
3. python3 triangle_deal_pairs.py

日志在 main.log