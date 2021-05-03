"""
假设 diff=1%
1 -> 1.01 平掉 0.01
1 -> 0.99 开仓 0.01

1 假设上涨 0.01 ，余额 1.01，卖掉 0.01，剩余 1。
2 假设继续上涨，卖掉 0.01
1 假设下跌 0.01，余额 0.99，买入 0.01
2 假设继续下跌 0.01，继续买入 0.01

## 开始
按市场价买入 1 个单位的币（这一步先手动操作吧）
balance_coin = 当前币的数量

开始循环
- last_order_price = 当前price
- init_coin_amount = balance_coin
- 开一单，卖单，price = last_order_price * 1.01，num = 0.01 * init_coin_amount
- 开一单，买单，price = last_order_price * 0.99，num = 0.01 * init_coin_amount
等待完全成交，先使用轮训，后续要求快的话，可以使用 websocket
- 只要其中一单完全成交，撤销剩下的单子。如果两个单子都成交，以第一个单子为准。
当前循环结束

"""

import ccxt
import conf
import json
import logging
import time

logging.basicConfig(filename='main.log', level=logging.DEBUG
                    , format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s')
logging.getLogger('ccxt').setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

exchange = ccxt.binance()

# 针对网络设置代理
if conf.Config.proxies is not None:
    exchange.proxies = conf.Config.proxies

# API 密钥设置
exchange.apiKey = conf.Config.binance_api_key
exchange.secret = conf.Config.binance_secret_key
exchange.password = ''  # okex在创建第三代api的时候，需要填写一个Passphrase。这个填写到这里即可

# 初始化
diff_rate = 0.005
base_coin = 'USDT'
target_coin = 'ETH'
symbol = target_coin + '/' + base_coin

init_coin_amount = 0.98870355   # 当前币的数量，目前手动指定，之后可以自动化
last_order_price = None

# 开始循环
while True:
    # 第一次获取当前价格
    if last_order_price is None:
        ticker_info = exchange.fetch_ticker(symbol)
        last_order_price = ticker_info['last']
        if last_order_price <= 0:
            logging.error('ticker info error:%s' % json.dumps(ticker_info))
            exit(1)

    balance_info = exchange.fetch_balance()
    logging.info('start one amount=%s price=%s, ETH=%s USDT=%s'
                 % (init_coin_amount, last_order_price, balance_info['ETH']['total'], balance_info['USDT']['total']))

    # 开一单，卖单
    price = last_order_price * (1 + diff_rate)
    amount = init_coin_amount * diff_rate
    sell_order_info = exchange.create_limit_sell_order(symbol, amount, price)
    logging.debug('[create sell]amount=%s, price=%s' % (sell_order_info['amount'], sell_order_info['price']))

    # 开一单，买单
    price = last_order_price * (1 - diff_rate)
    amount = init_coin_amount * diff_rate
    buy_order_info = exchange.create_limit_buy_order(symbol, amount, price)
    logging.debug('[create buy]amount=%s, price=%s' % (buy_order_info['amount'], buy_order_info['price']))

    # 循环等待完全成交
    not_finish = True
    while not_finish:
        # 如果没有完成，休眠 0.5 秒
        time.sleep(0.5)

        orders_info = exchange.fetch_orders(symbol)
        for one_order in orders_info:
            if buy_order_info['id'] == one_order['id'] and 'closed' == one_order['status']:
                not_finish = False
                last_order_price = one_order['price']
                init_coin_amount = init_coin_amount + one_order['amount']

                # 把剩余的撤单
                exchange.cancel_order(sell_order_info['id'], symbol)

                logging.debug('[closed buy]amount=%s, price=%s' % (one_order['amount'], one_order['price']))
            if sell_order_info['id'] == one_order['id'] and 'closed' == one_order['status']:
                not_finish = False
                last_order_price = one_order['price']
                init_coin_amount = init_coin_amount - one_order['amount']

                # 把剩余的撤单
                exchange.cancel_order(buy_order_info['id'], symbol)

                logging.debug('[closed sell]amount=%s, price=%s' % (one_order['amount'], one_order['price']))

    balance_info = exchange.fetch_balance()
    logging.info('finish one amount=%s price=%s, ETH=%s USDT=%s' % (
        init_coin_amount,
        last_order_price,
        balance_info[target_coin]['total'],
        balance_info[base_coin]['total']
    ))
