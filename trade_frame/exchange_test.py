"""
封装ccxt exchange对象，支持模拟复写
@Author : bboxhe@gmail.com

"""

import ccxt
import conf.conf
import time
import datetime
import json
import pandas
import logging


class ExchangeTest:
    def __init__(self, logger: logging.Logger):
        self.logger = logger

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
        self.fee = 0.00075           # binance 扣的是 bnb，模拟的时候先用 usdt 扣吧
        self.fee_usdt = 0           # 费用总额
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

    def get_fee_mode(self) -> str:
        """
        返回费用模式
        :return: extra : bnb 等额外抵扣模式，normal: 正常扣费。
        """
        return 'extra'

    def add_fee_usdt(self, usdt) -> float:
        """
        添加费用记录
        :param usdt: 交易的等量usdt数量
        :return:
        """
        self.fee_usdt += usdt * self.fee
        return self.fee_usdt

    def get_fee_usdt(self) -> float:
        """
        返回模拟记录的费用
        由于bnb抵扣金额，会随着bnb价格浮动，无法准确计算策略结果，因此这里模拟记录费用
        :return:
        """
        return self.fee_usdt

    def next_data(self):
        for datetime1, row in self.source_df.iterrows():
            dtime: datetime.datetime = datetime1.to_pydatetime()
            dtime = dtime.replace(tzinfo=datetime.timezone.utc)
            atime = datetime.datetime.utcfromtimestamp(0)
            atime = atime.replace(tzinfo=datetime.timezone.utc)
            self.current_time = (dtime - atime).total_seconds()

            self.current_str_time = str(dtime)

            # 判断单子是否成交
            length = len(self.orders[self.symbol])
            need_del = []
            need_num = 10  # 目前只存最后 10 个单子，循环结束后删除
            for i in range(length):
                order = self.orders[self.symbol][i]
                if 'open' != order['status']:
                    if length > need_num:       # 记录不要的单子
                        need_del.append(i)
                    continue

                if 'sell' == order['side'] and ('market' == order['type'] or row['price'] >= order['price']):
                    self.orders[self.symbol][i]['status'] = 'closed'
                    self.orders[self.symbol][i]['filled'] = self.orders[self.symbol][i]['amount']
                    self.orders[self.symbol][i]['remaining'] = 0

                    # 计算余额
                    amount = order['amount']
                    if 'market' == order['type']:
                        price = row['price']
                    else:
                        price = order['price']
                    target, base = order['symbol'].split('/')
                    cost = amount * price

                    self.orders[self.symbol][i]['price'] = price
                    self.orders[self.symbol][i]['cost'] = cost

                    self.balance[target]['used'] -= amount
                    self.balance[target]['total'] -= amount
                    if 'extra' != self.get_fee_mode():
                        cost = cost * (1 - self.fee)  # 模拟扣费
                    self.balance[base]['free'] += cost
                    self.balance[base]['total'] += cost
                elif 'buy' == order['side'] and ('market' == order['type'] or row['price'] <= order['price']):
                    self.orders[self.symbol][i]['status'] = 'closed'
                    self.orders[self.symbol][i]['filled'] = self.orders[self.symbol][i]['amount']
                    self.orders[self.symbol][i]['remaining'] = 0

                    # 计算余额
                    if 'market' == order['type']:
                        cost = order['cost']
                        price = row['price']
                        amount = cost / price
                    else:
                        price = order['price']
                        amount = order['amount']
                        cost = amount * price
                    target, base = order['symbol'].split('/')

                    self.orders[self.symbol][i]['price'] = price
                    self.orders[self.symbol][i]['cost'] = cost
                    self.orders[self.symbol][i]['amount'] = amount

                    self.balance[base]['used'] -= cost
                    self.balance[base]['total'] -= cost
                    if 'extra' != self.get_fee_mode():
                        amount = amount * (1 - self.fee)
                    self.balance[target]['free'] += amount
                    self.balance[target]['total'] += amount

            # 删除不要的单子
            for i in range(length - need_num):
                if i >= len(need_del):
                    break
                del(self.orders[self.symbol][need_del[i]])

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

    def create_market_buy_order(self, symbol, cost, params=None):
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
            "type": "market",
            "timeInForce": "GTC",
            "postOnly": False,
            "side": "buy",
            "price": None,
            "amount": None,
            "cost": cost,
            "average": None,
            "filled": 0,
            "remaining": None,
            "status": "open",
            "fee": None,
            "trades": None
        }
        if self.orders[symbol] is None:
            self.orders[symbol] = []
        self.orders[symbol].append(order)

        self.sleep(self.request_delay)

        return order

    def create_market_sell_order(self, symbol, amount, params=None):
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
            "type": "market",
            "timeInForce": "GTC",
            "postOnly": False,
            "side": "sell",
            "price": None,
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

    def create_limit_sell_order(self, symbol, amount, price):
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

    def create_limit_buy_order(self, symbol, amount, price):
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
                    self.logger.debug('[exchange no retry][cancel_order]fake order status error. id:%s orders:%s' % (id, json.dumps(self.orders)))
                    return None

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
