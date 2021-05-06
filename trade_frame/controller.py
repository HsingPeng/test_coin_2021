"""
主框架
@Author : bboxhe@gmail.com

"""

import conf.conf
import exchange
import exchange_test
import logging
import sys
import importlib


class Controller:
    def __init__(self, logname):
        self.exchange = None
        self.logger = None
        self.set_logging(logname)

    def get_exchange(self) -> exchange.Exchange:
        return self.exchange

    def set_exchange(self, exchange_param: str):
        exchange_file, exchange_name = exchange_param.split('.')
        module = globals()[exchange_file]
        e = getattr(module, exchange_name)
        self.exchange = e(self.logger)

    def run(self, strategy_name: str, strategy_params: str):
        file_name, class_name = strategy_name.split('.')
        module = importlib.import_module('strategy.' + file_name)
        s = getattr(module, class_name)
        s.exec(s, self, strategy_params)

    def set_logging(self, filename):
        file_handler = logging.FileHandler(filename=filename)
        stdout_handler = logging.StreamHandler(sys.stdout)

        formatter = logging.Formatter('%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s')
        file_handler.setFormatter(formatter)
        stdout_handler.setFormatter(formatter)

        logger = logging.getLogger('trade_frame.%s' % filename)
        logger.setLevel(logging.DEBUG)      # 设置级别
        logger.addHandler(file_handler)
        # logger.addHandler(stdout_handler)
        self.logger = logger

        logging.getLogger('ccxt').setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
