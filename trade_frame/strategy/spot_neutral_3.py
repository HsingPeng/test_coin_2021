"""
基于 spot_neutral_2 ，这不是一个策略，而是一个指标
@Author : bboxhe@gmail.com

std_price = 当前的标准价格
diff_price = std_price * diff_rate

下跌 N * diff_price 再回弹一个 diff_price，则结束。
只记录
- 上涨为 num=0
- 下跌一个为 num=1
- 下跌两个及以上为 num=2+

统计：
-  "1" / ("1" + "2+") - 1
- 1天比例 3天比例 5天比例

"""

import controller
import math
import backtesting
import json
import pandas


class SpotNeutral3:
    def exec(self, _controller: controller.Controller, params: str):
        exchange = _controller.get_exchange()
        logger = exchange.logger

        diff_rate, target_coin, base_coin = params.split('-')

        diff_rate = float(diff_rate)
        symbol = target_coin + '/' + base_coin

        df = pandas.DataFrame()
        series = pandas.Series({
            'time': exchange.get_int_time(),
            '0': 0,
            '1': 1,
            '2+': 1,
            'total': 2,
        }, name=exchange.get_int_time())
        df = df.append(series, ignore_index=True)
        data_all = {
            '0': 0,
            '1': 1,
            '2+': 1,
            'total': 2,
        }

        log_startone_header = [
            'realtime',
            'std_price',
            'num=0',
            'num=1',
            'num=2+',
            'num_total',
            'win_rate',
            'win_rate_5d',
            'win_rate_3d',
            'win_rate_1d',
            'win_rate_12h',
            ]
        _controller.header_to_csv(log_startone_header, 'startone')

        # 开始循环
        while True:
            ticker_info = exchange.fetch_ticker(symbol)
            std_price = ticker_info['last']  # 基准价格
            diff_price = std_price * diff_rate
            min_price = std_price

            while True:
                ticker_info = exchange.fetch_ticker(symbol)
                current_price = ticker_info['last']
                N = math.floor((std_price - current_price) / diff_price)
                min_price = min(min_price, std_price - N * diff_price)

                # 回调了 diff_price
                if current_price - min_price > diff_price:
                    logger.debug('[%s] [finish wait]current_price=%s std_price=%s' %
                                 (exchange.get_str_time(), current_price, std_price))
                    data_now = {
                        'time': exchange.get_int_time(),
                        '0': 0,
                        '1': 0,
                        '2+': 0,
                        'total': 1,
                    }
                    data_all['total'] += 1

                    if N < 0:
                        data_now['0'] = 1
                        data_all['0'] += 1
                    elif N == 1:
                        data_now['1'] = 1
                        data_all['1'] += 1
                    else:
                        data_now['2+'] = 1
                        data_all['2+'] += 1
                    series = pandas.Series(data_now, name=exchange.get_int_time())
                    df = df.append(series, ignore_index=True)
                    break

            df = df[df['time'] > (exchange.get_int_time() - 3600 * 24 * 5)]     # 保留5天内
            df_3d = df[df['time'] > (exchange.get_int_time() - 3600 * 24 * 3)]     # 3天
            df_1d = df[df['time'] > (exchange.get_int_time() - 3600 * 24 * 1)]     # 1天
            df_12h = df[df['time'] > (exchange.get_int_time() - 3600 * 12)]     # 12小时
            log_startone = {
                'realtime': exchange.get_str_time(),
                'std_price': std_price,
                'num=0': data_all['0'],
                'num=1': data_all['1'],
                'num=2+': data_all['2+'],
                'num_total': data_all['total'],
                'win_rate': data_all['1'] / (data_all['1'] + data_all['2+']) - 0.5,
                'win_rate_5d': (df['1'].sum() / (df['1'].sum() + df['2+'].sum())) - 0.5,
                'win_rate_3d': (df_3d['1'].sum() / (df_3d['1'].sum() + df_3d['2+'].sum())) - 0.5,
                'win_rate_1d': (df_1d['1'].sum() / (df_1d['1'].sum() + df_1d['2+'].sum())) - 0.5,
                'win_rate_12h': (df_12h['1'].sum() / (df_12h['1'].sum() + df_12h['2+'].sum())) - 0.5,
            }
            _controller.data_to_csv(log_startone_header, [log_startone], 'startone')

