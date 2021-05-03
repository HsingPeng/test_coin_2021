"""
相比于 grid_spot_trade.py 使用抗单。根据回测数据这样的赢率会更高。

假设 diff=0.09%
1 -> 1.009 平掉 0.0009
1 -> 0.99 开仓 0.0009

# 开始
按市场价买入 1 个单位的币（这一步先手动操作吧）
balance_coin = 当前币的数量

开始循环
1. 按当前价格开一买单 price = std_price - diff_price
2. 按当前价格开一卖单 price = std_price + diff_price
3. 等待完全成交，先使用轮训，后续要求快的话，可以使用 websocket
- 只要其中一单完全成交，撤销剩下的单子。如果两个单子都成交，以卖单为准。
4.1 如果触发卖单完全成交，当前循环结束
4.2 如果触发买单完全成交，进入回调等待阶段
5. 如果在最低价回调 diff_price，当前循环结束。
当前循环结束
"""

import ccxt
import conf
import json
import logging
import time
import sys

file_handler = logging.FileHandler(filename='main.log')
stdout_handler = logging.StreamHandler(sys.stdout)
handlers = [file_handler, stdout_handler]
logging.basicConfig(level=logging.DEBUG
                    , format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s'
                    , handlers=handlers)
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
diff_rate = 0.0009
base_coin = 'USDT'
target_coin = 'ETH'
symbol = target_coin + '/' + base_coin

per_usdt = 11   # 由于当前比较特殊，资金不够。所以每次交易都用11usdt。之后改成比例
std_price = None
min_price = None

# 开始循环
while True:
    # 第一次获取当前价格
    if std_price is None:
        while True:
            try:
                ticker_info = exchange.fetch_ticker(symbol)
            except Exception as e:
                logging.debug('[exchange retry]%s' % e)
                time.sleep(0.5)
                continue
            else:
                break
        std_price = ticker_info['last']
        min_price = std_price

    while True:
        try:
            balance_info = exchange.fetch_balance()
        except Exception as e:
            logging.debug('[exchange retry]%s' % e)
            time.sleep(0.5)
            continue
        else:
            break
    logging.info('start one std_price=%s, ETH=%s USDT=%s TOTAL=%s'
                 % (
                     std_price, balance_info['ETH']['total'],
                     balance_info['USDT']['total'],
                     balance_info[base_coin]['total'] + std_price * balance_info[target_coin]['total']
                 ))

    # 开一单，卖单
    price = std_price * (1 + diff_rate)
    amount = per_usdt / price
    while True:
        try:
            sell_order_info = exchange.create_limit_sell_order(symbol, amount, price)
        except Exception as e:
            logging.debug('[exchange retry]%s' % e)
            time.sleep(0.5)
            continue
        else:
            break
    logging.debug('[create sell]amount=%s, price=%s' % (sell_order_info['amount'], sell_order_info['price']))

    # 开一单，买单
    price = std_price * (1 - diff_rate)
    amount = per_usdt / price
    while True:
        try:
            buy_order_info = exchange.create_limit_buy_order(symbol, amount, price)
        except Exception as e:
            logging.debug('[exchange retry]%s' % e)
            time.sleep(0.5)
            continue
        else:
            break
    logging.debug('[create buy]amount=%s, price=%s' % (buy_order_info['amount'], buy_order_info['price']))

    # 循环等待完全成交
    not_finish = True
    while not_finish:
        # 如果没有完成，休眠 0.5 秒
        time.sleep(0.5)

        while True:
            try:
                orders_info = exchange.fetch_orders(symbol)
            except Exception as e:
                logging.debug('[exchange retry]%s' % e)
                time.sleep(0.5)
                continue
            else:
                break
        for one_order in orders_info:
            if buy_order_info['id'] == one_order['id'] and 'closed' == one_order['status']:
                not_finish = False
                std_price = one_order['price']

                # 把剩余的撤单
                while True:
                    try:
                        exchange.cancel_order(sell_order_info['id'], symbol)
                    except Exception as e:
                        logging.debug('[exchange retry]%s' % e)
                        time.sleep(0.5)
                        continue
                    else:
                        break

                logging.debug('[closed buy]amount=%s, price=%s' % (one_order['amount'], one_order['price']))

                # 循环等待回调
                while True:
                    while True:
                        try:
                            ticker_info = exchange.fetch_ticker(symbol)
                        except Exception as e:
                            logging.debug('[exchange retry]%s' % e)
                            time.sleep(0.5)
                            continue
                        else:
                            break
                    current_price = ticker_info['last']
                    min_price = min(min_price, current_price)
                    logging.debug('[waiting finish]min_price=%s, current_price=%s' % (min_price, current_price))
                    if (current_price - min_price) > (std_price * diff_rate):   # 代表回调了一个diff价格
                        break
                    time.sleep(0.5)                 # 轮询
            if sell_order_info['id'] == one_order['id'] and 'closed' == one_order['status']:
                not_finish = False
                std_price = one_order['price']

                # 把剩余的撤单
                while True:
                    try:
                        exchange.cancel_order(buy_order_info['id'], symbol)
                    except Exception as e:
                        logging.debug('[exchange retry]%s' % e)
                        time.sleep(0.5)
                        continue
                    else:
                        break

                logging.debug('[closed sell]amount=%s, price=%s' % (one_order['amount'], one_order['price']))

    while True:
        try:
            balance_info = exchange.fetch_balance()
        except Exception as e:
            logging.debug('[exchange retry]%s' % e)
            time.sleep(0.5)
            continue
        else:
            break
    logging.info('finish one std_price=%s, ETH=%s USDT=%s TOTAL=%s' % (
        std_price,
        balance_info[target_coin]['total'],
        balance_info[base_coin]['total'],
        balance_info[base_coin]['total'] + std_price * balance_info[target_coin]['total']
    ))
