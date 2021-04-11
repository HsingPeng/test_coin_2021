"""
网格 + 马丁 计算各个下跌倍数的出现次数，跟踪止盈
止盈：最高点下跌 0.5%
止损：- 0.5%。
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
    num_ret = {
        '+num': 0,
        '+value': 0,
        '-num': 0,
        '-value': 0,
    }
    last_high_price = None
    open_price = None
    diff_price = None
    diff_price_low = None
    show_num = 0
    for candle_begin_time, row in source_df.iterrows():
        for i in range(30, 190, 30):
            candle_begin_time = candle_begin_time + pandas.DateOffset(seconds=i)
            # 用 low 价格，按照 1% 回调算，类似跟踪止盈
            if open_price is None:
                last_high_price = row['close']
                open_price = row['close']
                diff_price = open_price * 0.005
                diff_price_low = open_price * 0.01
            elif (open_price < row['close'] and (last_high_price - row['close']) > diff_price) \
                    or (open_price - row['close'] > diff_price_low):  # 亏损
                if row['close'] > open_price:   # +
                    num_ret['+num'] += 1
                    num_ret['+value'] += (row['close'] - open_price)
                else:
                    num_ret['-num'] += 1
                    num_ret['-value'] += (row['close'] - open_price)

                last_high_price = None
                open_price = None
                diff_price = None
                diff_price_low = None
            else:
                last_high_price = max(row['close'], last_high_price)

            show_num += 1
            if show_num % 10000 == 0:
                print(candle_begin_time, row['close'], last_high_price, diff_price, num_ret)

    print(num_ret)


calculate_one()
