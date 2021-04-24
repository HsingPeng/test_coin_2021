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


def calculate_one(para):
    file_name = 'trade_ETHUSDT_1618859303.414359.sort.pkl'
    source_df = pandas.read_pickle(file_name)

    # 打开文件
    f = open('ret_num/%s' % para, 'w')

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
    # diff = 0.01
    diff = para / 1000
    last_high_price = None
    last_low_price = None
    diff_price = None
    show_num = 0
    for candle_begin_time, row in source_df.iterrows():
        # 用 low 价格，按照 1% 回调算，类似跟踪止盈
        if last_low_price is None:
            last_high_price = row['price']
            last_low_price = row['price']
            diff_price = last_low_price * diff
        elif row['price'] - last_low_price > diff_price:
            num = int((last_high_price - last_low_price) / diff_price)
            if num not in num_ret:
                num_ret[num] = 0
            num_ret[num] = num_ret[num] + 1
            num_ret_last_time[num] = candle_begin_time

            last_low_price = None
            diff_price = None
        elif last_low_price > row['price']:
            last_low_price = row['price']

        show_num += 1
        if show_num % 10000 == 0:
            # print(candle_begin_time, row['price'], last_high_price, last_low_price, diff_price, num_ret,
            #      num_ret_last_time)
            line = "\t".join([
                str(candle_begin_time),
                str(row['price']),
                str(last_high_price),
                str(last_low_price),
                str(diff_price),
                str(num_ret),
                json.dumps(num_ret_last_time)
            ])
            f.write(line + "\n")

    print(num_ret, num_ret_last_time)
    f.close()


# calculate_one()

para_list = range(1, 30, 1)
with Pool(processes=8) as pool:  # or whatever your hardware can support
    pool.map(calculate_one, para_list)
