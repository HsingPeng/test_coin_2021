"""
回测入口
@Author : bboxhe@gmail.com

"""

import sys
import controller
import pandas
import importlib
from multiprocessing.pool import Pool
import time
import json


class BackTesting:
    def __init__(self, ):
        # 初始化
        pass

    def test(self, params: str, _strategy_name: str, _strategy_params: str):
        target_coin, base_coin, starttime, endtime, time_interval = params.split('-')
        symbol = target_coin + '/' + base_coin

        c = controller.Controller('backtesting_test_%s_%s_%s' % (params, _strategy_name, _strategy_params))
        c.set_exchange('exchange_test.ExchangeTest')
        e = c.get_exchange()

        # 初始金额，这种参数先写死吧，之后完善
        base_amount = 10000
        target_amount = 0
        e.load_data('data/backtesting_getdata_%s.pkl' % params, symbol, base_amount, target_amount)

        c.run(_strategy_name, _strategy_params)

    def getdata(self, params: str):
        """
        成交历史
        :param params:
        :return:
        """
        target_coin, base_coin, starttime, endtime = params.split('-')
        symbol = target_coin + '/' + base_coin

        csv_name = 'data/backtesting_getdata_%s.csv' % params
        header = ['datetime', 'timestamp', 'id', 'price', 'amount', 'side']
        self.header_to_csv(header, csv_name)

        c = controller.Controller('backtesting_getdata_%s' % params)
        c.set_exchange('exchange.Exchange')
        e = c.get_exchange()

        # 获取数据
        from_id = None
        while True:
            if from_id is None:
                data = e.fetch_trades(symbol, since=int(starttime), limit=1000)
            else:
                data = e.fetch_trades(symbol, limit=1000, params={'fromId': from_id})   # 可能会超过一点截止时间

            if 0 == len(data):
                break

            data = sorted(data, key=lambda d: int(d['id']))

            from_id = int(data[-1]['id']) + 1
            self.data_to_csv(header, data, csv_name)

            if data[-1]['timestamp'] >= int(endtime):
                break

    def get_ohlcv_data(self, params: str):
        """
        K线历史
        :param params:
        :return:
        """
        target_coin, base_coin, starttime, endtime, time_interval = params.split('-')
        symbol = target_coin + '/' + base_coin

        csv_name = 'data/backtesting_getdata_%s.csv' % params
        header = ['datetime', 'timestamp', 'price', 'volume', 'open', 'high', 'low', 'close']
        self.header_to_csv(header, csv_name)

        c = controller.Controller('backtesting_get_ohlcv_data_%s' % params)
        c.set_exchange('exchange.Exchange')
        e = c.get_exchange()

        # 获取数据
        start_time_since = int(starttime)
        running = True
        while running:
            data_row = e.fetch_ohlcv(symbol=symbol, timeframe=time_interval, since=start_time_since, limit=1000)
            # [[1622822400000, 2658.01, 2658.49, 2650.98, 2652.05, 2116.27542],[...]]

            data = []
            for row in data_row:
                if int(row[0]) >= int(endtime):
                    running = False
                    continue

                data.append({
                    "datetime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(row[0]) / 1000)),
                    "timestamp": row[0],
                    "price": row[1],
                    "volume": row[5],
                    "open": row[1],
                    "high": row[2],
                    "low": row[3],
                    "close": row[4],
                })

            data = sorted(data, key=lambda d: int(d['timestamp']))

            self.data_to_csv(header, data, csv_name)

            start_time_since = data[-1]['timestamp']
            if data[-1]['timestamp'] >= int(endtime):
                break

    def header_to_csv(self, header, csv_name):
        file = open(csv_name, 'x')
        file.write("\t".join(header) + "\n")
        file.close()

    def data_to_csv(self, header, data, csv_name):
        """
        从数据里解析数据，存储到csv文件
        :param header:
        :param data:
        :param csv_name:
        :return :
        """
        file = open(csv_name, 'a')

        for deal in data:
            data = []
            for key in header:
                data.append(str(deal[key]))
            line = "\t".join(data)
            file.write("%s\n" % line)

        file.close()

    def csv_to_pkl(self, params: str):
        csv_name = 'data/backtesting_getdata_%s.csv' % params
        pkl_name = 'data/backtesting_getdata_%s.pkl' % params
        source_df = pandas.read_csv(
            filepath_or_buffer=csv_name,
            encoding='utf8',
            sep="\t",
            parse_dates=['datetime'],
            index_col=['datetime'],
        )

        # pkl格式
        source_df.to_pickle(pkl_name)  # 格式另存


def multi_test(params):
    symbol_params, _strategy_name, _strategy_params = params
    print(symbol_params, _strategy_name, _strategy_params)

    try:
        BackTesting().test(symbol_params, _strategy_name, _strategy_params)
    except Exception as e:
        print('exception:', symbol_params, _strategy_name, _strategy_params, str(e))


if __name__ == "__main__":
    usage = 'usage:python3 backtesting.py [getdata|test|csv2pkl] symbol-starttime-endtime [strategy_name params]' \
            + "\n example:python3 backtesting.py getdata ETH-USDT-1620132107000-1620142907000" \
            + "\n example:python3 backtesting.py csv2pkl ETH-USDT-1620132107000-1620142907000" \
            + "\n example:python3 backtesting.py test ETH-USDT-1620132107000-1620142907000 " \
              "spot_neutral_1.SpotNeutral1 0.0009-ETH-USDT-11" \
            + "\n example:python3 backtesting.py multitest ETH-USDT_spot_neutral_1 8"
    if 3 > len(sys.argv):
        print(usage)
        exit(1)

    params = sys.argv[2]

    trading = BackTesting()

    if 'getdata' == sys.argv[1]:
        trading.getdata(params)
    if 'get_ohlcv_data' == sys.argv[1]:
        trading.get_ohlcv_data(params)
    elif 'test' == sys.argv[1]:
        if 5 > len(sys.argv):
            print(usage)
            exit(1)
        strategy_name = sys.argv[3]
        strategy_params = sys.argv[4]
        trading.test(params, strategy_name, strategy_params)
    elif 'csv2pkl' == sys.argv[1]:
        trading.csv_to_pkl(params)
    elif 'multitest' == sys.argv[1]:
        if 4 > len(sys.argv):
            print(usage)
            exit(1)

        module = importlib.import_module('param.' + sys.argv[2])
        params = module.get_para_list()

        with Pool(processes=int(sys.argv[3])) as pool:  # or whatever your hardware can support
            pool.map(multi_test, params)
    else:
        print(usage)
        exit(1)

    print('finish')
