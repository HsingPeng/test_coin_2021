"""
网格 + 马丁 计算各个下跌倍数的出现次数
"""

import pandas
import matplotlib.pyplot as plt
import json
import time
from multiprocessing.pool import Pool


pandas.set_option('expand_frame_repr', False) # 列太多时不换行


def calculate_one():
    file_name = 'ETH-USDT3.pkl'
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
    for candle_begin_time, row in source_df.iterrows():
        # 用 close 价格，按照 1% 回调算，类似跟踪止盈
        if last_low_price is None:
            last_high_price = row['close']
            last_low_price = row['close']
            diff_price = last_low_price * 0.005
        elif row['close'] - last_low_price > diff_price:
            num = int((last_high_price - last_low_price) % diff_price)
            if num not in num_ret:
                num_ret[num] = 0
            num_ret[num] = num_ret[num] + 1
            num_ret_last_time[num] = candle_begin_time

            last_low_price = None
            diff_price = None
        elif last_low_price > row['close']:
            last_low_price = row['close']

        show_num += 1
        if show_num % 10000 == 0:
            print(candle_begin_time, num_ret, num_ret_last_time)

    print(num_ret, num_ret_last_time)


calculate_one()
