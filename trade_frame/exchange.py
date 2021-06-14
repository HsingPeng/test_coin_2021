"""
封装ccxt exchange对象，支持模拟复写
@Author : bboxhe@gmail.com

"""

import ccxt
import conf.conf
import logging
import time
import datetime


class Exchange:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.exchange = None
        self.fee = 0.00075  # 这里需要手动填写上正确的费用率
        self.fee_usdt = 0   # 初始化手续费统计变量

    def sleep(self, second):
        time.sleep(second)

    def get_str_time(self) -> str:
        return datetime.datetime.now().strftime('%H:%M:%S.%f')

    def get_int_time(self) -> int:
        atime = datetime.datetime.utcfromtimestamp(0)
        atime = atime.replace(tzinfo=datetime.timezone.utc)
        return (datetime.datetime.now() - atime).total_seconds()

    def load_data(self, filename, symbol, base_amount, target_amount):
        pass

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

    def fetch_ticker(self, symbol, params=None):
        if params is None:
            params = {}

        while True:
            try:
                return self.exchange.fetch_ticker(symbol, params)
            except Exception as e:
                self.logger.debug('[exchange retry]%s' % e)
                time.sleep(0.01)
                continue

    def fetch_ohlcv(self, symbol, timeframe='1m', since=None, limit=None, params=None):
        if params is None:
            params = {}

        while True:
            try:
                return self.exchange.fetch_ohlcv(symbol, timeframe, since, limit, params)
            except Exception as e:
                self.logger.debug('[exchange retry]%s' % e)
                time.sleep(0.01)
                continue

    def fetch_balance(self, params=None):
        if params is None:
            params = {}

        while True:
            try:
                return self.exchange.fetch_balance(params)
            except Exception as e:
                self.logger.debug('[exchange retry]%s' % e)
                time.sleep(0.01)
                continue

    def create_market_buy_order(self, symbol, cost, params=None):
        if params is None:
            params = {}

        while True:
            try:
                self.exchange.create_market_buy_order(symbol, cost, params)
            except Exception as e:
                self.logger.debug('[exchange retry]%s' % e)
                time.sleep(0.01)
                continue

    def create_market_sell_order(self, symbol, amount, params=None):
        if params is None:
            params = {}

        while True:
            try:
                self.exchange.create_market_sell_order(symbol, amount, params)
            except Exception as e:
                self.logger.debug('[exchange retry]%s' % e)
                time.sleep(0.01)
                continue

    def create_limit_sell_order(self, symbol, amount, price):
        while True:
            try:
                return self.exchange.create_limit_sell_order(symbol, amount, price)
            except Exception as e:
                self.logger.debug('[exchange retry]%s' % e)
                time.sleep(0.01)
                continue

    def create_limit_buy_order(self, symbol, amount, price):
        while True:
            try:
                return self.exchange.create_limit_sell_order(symbol, amount, price)
            except Exception as e:
                self.logger.debug('[exchange retry]%s' % e)
                time.sleep(0.01)
                continue

    def fetch_orders(self, symbol=None, since=None, limit=None, params=None):
        if params is None:
            params = {}

        while True:
            try:
                return self.exchange.fetch_orders(symbol, since, limit, params)
            except Exception as e:
                self.logger.debug('[exchange retry]%s' % e)
                time.sleep(0.01)
                continue

    def cancel_order(self, id, symbol=None, params=None):
        if params is None:
            params = {}

        while True:
            try:
                return self.exchange.cancel_order(id, symbol, params)
            except ccxt.errors.OrderNotFound as e:      # 订单不存在时，特殊处理
                self.logger.debug('[exchange no retry]%s' % e)
                return {}
            except Exception as e:
                self.logger.debug('[exchange retry]%s' % e)
                time.sleep(0.01)
                continue

    def fetch_trades(self, symbol, since=None, limit=None, params=None):
        if params is None:
            params = {}

        while True:
            try:
                return self.exchange.fetch_trades(symbol, since, limit, params)
            except ccxt.errors.OrderNotFound as e:      # 订单不存在时，特殊处理
                self.logger.debug('[exchange no retry]%s' % e)
                return {}
            except Exception as e:
                self.logger.debug('[exchange retry]%s' % e)
                time.sleep(0.01)
                continue

    def start_websocket_push(self):
        """
        使用 websocket 推送行情和成交记录。需要子类实现
        :return:
        """
        raise Exception('未实现方法')
