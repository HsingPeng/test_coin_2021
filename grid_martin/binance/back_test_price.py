"""
价格

"""

import pandas
import matplotlib.pyplot as plt
import json
import time
from multiprocessing.pool import Pool


def show(df_1):
    """
    绘制资金曲线
    :param df_1:DataFrame
    :return:
    """
    df1 = df_1.iloc[-1]
    ax4 = plt.subplot(111)
    ax4.cla()
    ax4.set_title('实时价格 ' + str(df1['open']))
    ax4.plot(df_1['candle_begin_time'], df_1['open'], 'k')

    plt.pause(0.0001)


pandas.set_option('expand_frame_repr', False) # 列太多时不换行

plt.figure(figsize=(10, 10))
plt.title('BTC定投回测')
plt.rcParams["font.family"] = 'Arial Unicode MS'
plt.ion()


def calculate_one(param):
    # 初始配置
    sell_level = param[0]     # 0 ~ 10
    diff_rate = param[1]      # 0.03 ~ 0.4 步进 0.02

    title = 'param_' + str(sell_level) + '_' + str(diff_rate)
    print('start ' + title)

    # === 由于是回测，一次读入全部数据
    file_name = 'trade_ETHUSDT_1618859303.414359.sort.pkl'
    source_df = pandas.read_pickle(file_name)

    # df.sort_values(by=['candle_begin_time'], inplace=True) # 任何原始数据读入都进行一下排序、去重，以防万一

    # 遍历每条数据，只保留最近的 max_len 条数据
    max_len = 288
    show_num = 0
    order_num = 0
    df = pandas.DataFrame()
    for candle_begin_time, row in source_df.iterrows():
        series = pandas.Series({
            'candle_begin_time': candle_begin_time,
            'open': row['price'],
            'high': row['price'],
            'low': row['price'],
            'close': row['price'],
            'volume': row['quantity'],
            'order_num': order_num,
        }, name=candle_begin_time)

        df = df.append(series, ignore_index=False)
        df = df.iloc[-max_len:]  # 保持最大K线数量不会超过max_len个

        # print(df)
        # print(json.dumps(info))
        df1 = df.iloc[-1]
        if show_num % 30 == 0:
            show(df)
            print([
                title,
                df1['candle_begin_time'],
                df1['close'],
            ], "\t")
        show_num += 1


def gen_param_list(m_list, n_list):
    """
    :param m_list:
    :param n_list:
    :return:
    """
    _para_list = []
    for m in m_list:
        for n in n_list:
            para = [m, n]
            _para_list.append(para)

    return _para_list


calculate_one([1, 0.05])
exit()

# =====并行提速
# max_order_level 2 ~ 12
# max_diff_rate 0.05 ~ 0.4 步进 0.02
# para_list = gen_param_list(range(0, 4, 1), [i / 1000 for i in list(range(40, 400, 20))])
para_list = gen_param_list(range(0, 4, 1), [0.004, 0.005, 0.007, 0.01, 0.02, 0.03, 0.04])
with Pool(processes=8) as pool:  # or whatever your hardware can support
    pool.map(calculate_one, para_list)
