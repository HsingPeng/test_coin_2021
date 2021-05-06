"""
封装ccxt exchange对象，支持模拟复写
@Author : bboxhe@gmail.com

"""

import ccxt
import conf.conf
import logging
import time
import datetime
import json
import pandas


class ExchangeTest:
    def __init__(self):
        self.source_df = None           # 回测数据
        self.current_time = None        # 回测中的当前时间
        self.current_str_time = None        # 回测中的当前时间
        self.source_row = None            # 回测数据生成器
        self.symbol = None
        self.target_coin = None
        self.base_coin = None
        self.id_alloc = 1000

        self.balance = {
            'BTC': {
                'free': 0,
                'used': 0,
                'total': 0,
            },
            'USDT': {
                'free': 500,
                'used': 0,
                'total': 500,
            },
            'ETH': {
                'free': 0,
                'used': 0,
                'total': 0,
            },
            'EOS': {
                'free': 0,
                'used': 0,
                'total': 0,
            },
        }
        self.orders = {
            'EOS/USDT': []
        }
        self.fee = 0.00075      # binance 扣的是 bnb，模拟的时候先用 usdt 扣吧
        self.request_delay = 0.01     # 模拟请求延迟 秒。每请求一次，时间线都往后走

    def gen_id(self) -> int:
        """
        生成一个int类型的唯一id，用于订单
        :return:int
        """
        self.id_alloc += 1
        return self.id_alloc

    def sleep(self, second) -> None:
        """
        回测需要假睡眠。跳过指定时间。过程中，判断单子是否成交
        :param second:
        :return:
        """
        last_time = self.current_time
        while True:
            if last_time is None:
                # 说明是第一次进
                next(self.source_row)
                last_time = self.current_time
                continue

            next(self.source_row)
            if self.current_time - last_time > second:
                break

    def get_str_time(self) -> str:
        return self.current_str_time

    def next_data(self):
        for datetime1, row in self.source_df.iterrows():
            dtime: datetime.datetime = datetime1.to_pydatetime()
            dtime = dtime.replace(tzinfo=datetime.timezone.utc)
            atime = datetime.datetime.utcfromtimestamp(0)
            atime = atime.replace(tzinfo=datetime.timezone.utc)
            self.current_time = (dtime - atime).total_seconds()

            self.current_str_time = str(dtime)

            # 判断单子是否成交
            for i in range(len(self.orders[self.symbol])):
                order = self.orders[self.symbol][i]
                if 'open' != order['status']:
                    continue

                if 'sell' == order['side'] and row['price'] >= order['price']:
                    self.orders[self.symbol][i]['status'] = 'closed'
                    self.orders[self.symbol][i]['filled'] = self.orders[self.symbol][i]['amount']
                    self.orders[self.symbol][i]['remaining'] = 0

                    # 计算余额
                    amount = order['amount']
                    price = order['price']
                    target, base = order['symbol'].split('/')
                    cost = amount * price

                    self.balance[target]['used'] -= amount
                    self.balance[target]['total'] -= amount
                    self.balance[base]['free'] += cost * (1 - self.fee)     # 模拟扣费
                    self.balance[base]['total'] += cost * (1 - self.fee)     # 模拟扣费
                elif 'buy' == order['side'] and row['price'] <= order['price']:
                    self.orders[self.symbol][i]['status'] = 'closed'
                    self.orders[self.symbol][i]['filled'] = self.orders[self.symbol][i]['amount']
                    self.orders[self.symbol][i]['remaining'] = 0

                    # 计算余额
                    amount = order['amount']
                    price = order['price']
                    target, base = order['symbol'].split('/')
                    cost = amount * price

                    self.balance[base]['used'] -= cost
                    self.balance[base]['total'] -= cost
                    self.balance[target]['free'] += amount * (1 - self.fee)     # 模拟扣费
                    self.balance[target]['total'] += amount * (1 - self.fee)     # 模拟扣费

            yield dtime, row

    def load_data(self, pklname, symbol: str, base_amount, target_amount):
        """
        加载回测数据
        :param pklname:
        :param symbol: str
        :param base_amount:
        :param target_amount:
        :return:
        """
        self.source_df = pandas.read_pickle(pklname)
        self.source_row = self.next_data()

        self.symbol = symbol
        target_coin, base_coin = symbol.split('/')
        self.target_coin = target_coin
        self.base_coin = base_coin
        self.orders[symbol] = []
        self.balance[base_coin] = {
            'free': base_amount,
            'used': 0,
            'total': base_amount,
        }
        self.balance[target_coin] = {
            'free': target_amount,
            'used': 0,
            'total': target_amount,
        }

    def fetch_ticker(self, symbol, params=None):
        dtime, row = next(self.source_row)

        return {
            "symbol": symbol,
            "timestamp": self.current_time,
            "datetime": self.current_str_time,
            # "high": 6.6981,
            # "low": 6.1775,
            # "bid": 6.3199,
            # "bidVolume": 1516.76,
            # "ask": 6.32,
            # "askVolume": 104.31,
            # "vwap": 6.44493944,
            # "open": 6.4256,
            # "close": 6.3212,
            "last": float(row['price']),
            # "previousClose": 6.4258,
            # "change": -0.1044,
            # "percentage": -1.625,
            # "average": None,
            # "baseVolume": 26606738.96,
            # "quoteVolume": 171478821.1781,
            # "info": {}
        }

    def fetch_balance(self, params=None):
        return self.balance

    def create_limit_sell_order(self, symbol, *args):
        amount = args[0]
        price = args[1]
        cost = amount * price

        # 计算余额
        target, base = symbol.split('/')
        if self.balance[target]['free'] < amount:
            raise Exception('insufficient coin:%s amount:%s' % (target, amount))

        self.balance[target]['free'] -= amount
        self.balance[target]['used'] += amount

        id = self.gen_id()
        order = {
            "info": {},
            "id": str(id),
            "clientOrderId": "fakeClientOrderId%d" % id,
            "timestamp": self.current_time * 1000,
            "datetime": self.current_str_time,
            "lastTradeTimestamp": None,
            "symbol": symbol,
            "type": "limit",
            "timeInForce": "GTC",
            "postOnly": False,
            "side": "sell",
            "price": price,
            "amount": amount,
            "cost": 0,
            "average": None,
            "filled": 0,
            "remaining": amount,
            "status": "open",
            "fee": None,
            "trades": None
        }

        if self.orders[symbol] is None:
            self.orders[symbol] = []
        self.orders[symbol].append(order)

        self.sleep(self.request_delay)

        return order

    def create_limit_buy_order(self, symbol, *args):
        amount = args[0]
        price = args[1]
        cost = amount * price

        # 计算余额
        target, base = symbol.split('/')
        if self.balance[base]['free'] < cost:
            raise Exception('insufficient coin:%s cost:%s' % (base, cost))

        self.balance[base]['free'] -= cost
        self.balance[base]['used'] += cost

        id = self.gen_id()
        order = {
            "info": {},
            "id": str(id),
            "clientOrderId": "fakeClientOrderId%d" % id,
            "timestamp": self.current_time * 1000,
            "datetime": self.current_str_time,
            "lastTradeTimestamp": None,
            "symbol": symbol,
            "type": "limit",
            "timeInForce": "GTC",
            "postOnly": False,
            "side": "buy",
            "price": price,
            "amount": amount,
            "cost": 0,
            "average": None,
            "filled": 0,
            "remaining": amount,
            "status": "open",
            "fee": None,
            "trades": None
        }
        if self.orders[symbol] is None:
            self.orders[symbol] = []
        self.orders[symbol].append(order)

        self.sleep(self.request_delay)

        return order

    def fetch_orders(self, symbol=None, since=None, limit=None, params=None):
        if self.orders[symbol] is None:
            self.orders[symbol] = []

        self.sleep(self.request_delay)
        return self.orders[symbol]

    def cancel_order(self, id, symbol, params=None):
        if self.orders[symbol] is None:
            self.orders[symbol] = []

        order = None
        for i in range(len(self.orders[symbol])):
            if id == self.orders[symbol][i]['id']:
                if 'open' != self.orders[symbol][i]['status']:
                    logging.debug('[exchange no retry]fake order status error. id:%s orders:%s' % (id, json.dumps(self.orders)))

                self.orders[symbol][i]['status'] = 'canceled'
                order = self.orders[symbol][i]

        if order is None:
            raise ccxt.errors.OrderNotFound('fake order not found')     # 模拟出错

        # 计算余额
        amount = order['amount']
        price = order['price']
        side = order['side']
        target, base = order['symbol'].split('/')
        cost = amount * price

        if 'sell' == side:
            self.balance[target]['used'] -= amount
            self.balance[target]['free'] += amount
        else:
            self.balance[base]['used'] -= cost
            self.balance[base]['free'] += cost

        self.sleep(self.request_delay)
        return order
