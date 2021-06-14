"""
binance
@Author : bboxhe@gmail.com

"""

import ccxt
import conf.conf
import logging
import time
import datetime
import sys
import threading
import websocket


class WsThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.ws = None
        self.url = 'wss://stream.binance.com:9443/stream?streams=btcusdt@aggTrade/T80T31ljwp4Sz0G1HAOGbhxOjD3OuB3RiFPyjJqr8PV4dNPkUrjDHNf0yv23'

    def run(self):
        self.ws = websocket.WebSocketApp(self.url,
                                         on_open=self.on_open,
                                         on_message=self.on_message,
                                         on_error=self.on_error,
                                         on_close=self.on_close)
        # 针对网络设置代理
        if conf.conf.Config.http_proxy_host is not None:
            host = conf.conf.Config.http_proxy_host
            port = conf.conf.Config.http_proxy_port
            proxy_type = conf.conf.Config.proxy_type
            self.ws.run_forever(http_proxy_host=host, http_proxy_port=port, proxy_type=proxy_type)
        else:
            self.ws.run_forever()

    def on_message(self, ws, message):
        print("####### on_message #######")
        print(self)
        print(message)

    def on_error(self, ws, error):
        print("####### on_error #######")
        print(self)
        print(error)

    def on_close(self, ws, close_status_code, close_msg):
        print("####### on_close #######")
        print(self)
        self.ws = None

    def on_open(self, ws):
        print("####### on_open #######")
        print(self)

    def heartbeat(self):
        print("####### heartbeat #######")


class ExchangeBinance:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        exchange = ccxt.binance()

        # 针对网络设置代理
        if conf.conf.Config.proxies is not None:
            exchange.proxies = conf.conf.Config.proxies

        # API 密钥设置
        exchange.apiKey = conf.conf.Config.binance_api_key
        exchange.secret = conf.conf.Config.binance_secret_key
        exchange.password = ''  # okex在创建第三代api的时候，需要填写一个Passphrase。这个填写到这里即可

        self.exchange = exchange
        self.fee = 0.00075  # binance 扣的是 bnb，这里需要手动填写上正确的费用率
        self.fee_usdt = 0

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

    def create_market_buy_order(self, symbol, amount, params=None):
        if params is None:
            params = {}

        while True:
            try:
                self.exchange.create_market_buy_order(symbol, amount, params)
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

        # 获取 listen key
        ret = self.exchange.publicPostUserDataStream()
        spot_listen_key = ret['listenKey']

        # 开启 websocket


        pass


if __name__ == "__main__":
    logger = logging.getLogger('exchange_binance')
    logger.setLevel(logging.DEBUG)  # 设置级别
    stdout_handler = logging.StreamHandler(sys.stdout)
    logger.addHandler(stdout_handler)       # 同时在命令行输出

    exchange = ExchangeBinance(logger)
    exchange.start_websocket_push()
