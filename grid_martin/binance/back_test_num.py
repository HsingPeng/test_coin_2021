"""
网格 + 马丁 计算各个下跌倍数的出现次数
"""

import pandas
import matplotlib.pyplot as plt
import json
import time
import datetime
from multiprocessing.pool import Pool


pandas.set_option('expand_frame_repr', False) # 列太多时不换行


def calculate_one():
    file_name = 'ETHUSDT-1m-2021-03.pkl'
    source_df = pandas.read_pickle(file_name)

    # 遍历每条数据
    """
    num_ret = {
        1 => 300,
        2 => 200,
        3 => 100,
        4 => 50,
        5 => 10,
    }
    """
    num_ret = {}
    num_ret_last_time = {}
    last_high_price = None
    last_low_price = None
    diff_price = None
    show_num = 0
    for opentime, row in source_df.iterrows():
        for i in range(30, 190, 30):
            candle_begin_time = datetime.datetime.utcfromtimestamp(opentime / 1000)
            candle_begin_time = candle_begin_time + pandas.DateOffset(seconds=i)
            # 用 low 价格，按照 1% 回调算，类似跟踪止盈
            if last_low_price is None:
                last_high_price = row['low']
                last_low_price = row['low']
                diff_price = last_low_price * 0.01
            elif row['low'] - last_low_price > diff_price:
                num = int((last_high_price - last_low_price) / diff_price)
                if num not in num_ret:
                    num_ret[num] = 0
                num_ret[num] = num_ret[num] + 1
                num_ret_last_time[num] = candle_begin_time

                last_low_price = None
                diff_price = None
            elif last_low_price > row['low']:
                last_low_price = row['low']

            show_num += 1
            if show_num % 10000 == 0:
                print(candle_begin_time, row['low'], last_high_price, last_low_price, diff_price, num_ret, num_ret_last_time)

    print(num_ret, num_ret_last_time)


calculate_one()
