"""
网格 + 马丁 回测

网格规则：
- 根据当前价位计算1%的价格。
- 每下跌1%，按1倍数买入开仓数量。
- 每回调1%就卖出全部数量。不回调则继续按倍数买入开仓数量。
- 根据当前价格重置1%的价格。

如果网格最大支持10%回调。只要10%里面，有一次1%的回调，就能盈利。
盈利金额是 1% * 1% = 万分之一
假设一天波动1000次1%（不多，完全靠谱），一天的利润就是 10%。
当然得扣除手续费，千分之二，买卖有两次。按1%算，手续费就是 1000 * 0.2% * 1% * 2 = 4%
还好，看起来利润比手续费高，当然不回调的次数可能更多一点，所以手续费会更加高一点。
一天利润 6%，如果平均一天只波动100次，一天利润 0.6%，一年219%，相当可以。

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
    ax1 = plt.subplot(411)
    ax1.cla()
    ax1.set_title(str(df1['candle_begin_time']) + ' 倍数 ' + str(df1['order_num']))
    ax1.plot(df_1['candle_begin_time'], df_1['order_num'], 'g')
    ax2 = plt.subplot(412)
    ax2.cla()
    ax2.set_title('余额 ' + str(df1['balance_amount']))
    ax2.plot(df_1['candle_begin_time'], df_1['balance_amount'], 'b')
    ax3 = plt.subplot(413)
    ax3.cla()
    ax3.set_title('余币数 ' + str(df1['balance_size']))
    ax3.plot(df_1['candle_begin_time'], df_1['balance_size'], 'c')
    ax4 = plt.subplot(414)
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
    max_order_level = param[0]  # 2 ~ 12
    max_diff_rate = param[1]      # 0.05 ~ 0.4 步进 0.02
    level_list = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]        # 13 级
    total_level = level_list[max_order_level - 1] * 2
    symbol_config = {
        'max_order_level': max_order_level,  # 资金最多能下单几次，10代表剩余资金可以下10次单
        'max_diff_rate': max_diff_rate,  # 最大破网百分比
        'total_level': total_level,  # 资金分成多少份
        'level_list': level_list,
        # 'level_list': [1, 1, 2, 2, 4, 4, 8, 8, 16, 16, 32, 32],
        'fee': 0.001  # 手续费，千分之一
    }

    title = 'param_' + str(max_order_level) + '_' + str(max_diff_rate)
    print('start ' + title)

    init_info = {
        'init_balance_amount': 200,  # 初始余额
    }

    # 初始化数据
    info = {
        'balance_amount': init_info['init_balance_amount'],  # 余额
        'balance_size': 0,  # 剩余的币数
        'diff_price': None,  # 当前价差
        'order_num': 0,  # 已经下单的次数，0 代表没下单，1~9 代表下了几次单，一轮还没有结束
        'last_buy_price': None,  # 上个买单的价格
        'last_buy_amount': None,  # 上个买单的数量
        'buy_order': None,
        'sell_order': None,
    }

    # === 由于是回测，一次读入全部数据
    # file_name = 'ETH-USDT2_2000.csv'
    file_name = 'ETH-USDT3.pkl'
    source_df = pandas.read_pickle(file_name)

    # df.sort_values(by=['candle_begin_time'], inplace=True) # 任何原始数据读入都进行一下排序、去重，以防万一

    # 遍历每条数据，只保留最近的3条数据
    max_len = 288
    show_num = 0
    df = pandas.DataFrame()
    for candle_begin_time, row in source_df.iterrows():
        series = pandas.Series({
            'candle_begin_time': candle_begin_time,
            'open': row['open'],
            'high': row['high'],
            'low': row['low'],
            'close': row['close'],
            'volume': row['volume'],
            'balance_amount': info['balance_amount'],
            'balance_size': info['balance_size'],
            'order_num': info['order_num']
        }, name=candle_begin_time)

        df = df.append(series, ignore_index=False)
        df = df.iloc[-max_len:]  # 保持最大K线数量不会超过max_len个
        # print(df.iloc[-1].to_json())
        # print(json.dumps(info))
        df1 = df.iloc[-1]
        if show_num % 10 == 0:
            show(df)
            print([
                title,
                df1['candle_begin_time'],
                df1['close'],
                df1['balance_amount'],
                df1['balance_size'],
                df1['order_num'],
                json.dumps(info),
            ], "\t")
        show_num += 1

        # 方便debug
        # if str(df1['candle_begin_time']) == '2017-09-04 05:15:00':
        #    print('aaaa')

        total_level = symbol_config['total_level']
        level_list = symbol_config['level_list']
        max_diff_rate = symbol_config['max_diff_rate']
        max_order_level = symbol_config['max_order_level']
        fee = symbol_config['fee']
        # 计算上次下单请求是否成交，计算余额
        """
        1 先看单子能否成交
        2 填充字段
        info :
        'balance_amount': 100,          # 余额
        'balance_size': 0,           # 剩余的币数
        'diff_price': 344,            # 当前价差
        'per_order_amount': 0,          # 每次交易的金额
        'order_num': 1,                 # 已经下单的次数，0 代表没下单，1~9 代表下了几次单，一轮还没有结束
        'last_buy_price': 54341,            # 上个买单的价格
        'last_buy_amount':2,                # 上个买单的数量
        'buy_order': {
            'order_size':0.1                # 下单卖出的数量，卖单需要
            'order_price':414134            # 下单价格
            'order_amount':200              # 下单买入的金额，买单需要
            'state':'submit',               # 状态 submit 下单 finish 成交
            'flag':'deal_now',             # 回测特殊标记，deal_now 第一个买单和最后一个爆单，直接成交
        },
        'sell_order':{}
        """
        low = df.iloc[-1]['low']
        high = df.iloc[-1]['high']
        buy_order = info['buy_order']
        sell_order = info['sell_order']

        # 买单成交，第一单简化，直接成交
        if buy_order is not None and 'submit' == buy_order['state'] \
                and (low <= buy_order['order_price'] or 'deal_now' == buy_order['flag']):
            order_price = buy_order['order_price']
            order_amount = buy_order['order_amount']
            order_size = order_amount / order_price * (1 - fee)
            # 计算余额
            info['balance_amount'] = info['balance_amount'] - order_amount
            info['balance_size'] = info['balance_size'] + order_size
            info['last_buy_price'] = order_price
            info['last_buy_amount'] = order_amount
            info['buy_order']['state'] = 'finish'
        # 卖单成交，爆单简化，直接成交
        elif sell_order is not None and 'submit' == sell_order['state'] \
                and (sell_order['order_price'] <= high or 'deal_now' == sell_order['flag']):
            order_price = sell_order['order_price']
            order_size = sell_order['order_size']
            order_amount = order_price * order_size * (1 - fee)
            # 计算余额
            info['balance_amount'] = info['balance_amount'] + order_amount
            info['balance_size'] = info['balance_size'] - order_size
            info['sell_order']['state'] = 'finish'

        # 计算信号，下单
        """
        状态
        1 当前没有单子 -> 下一单
        2 开一单 -> 等待成交
        3 一单成交 -> 同时开获利单、下一单
        4 同时开获利单、下一单 -> 等待成交
        5 获利单成交 -> 取消下一单，本轮结束
        6 下一单成交 -> 取消当前获利单。同时开获利单、下一单

        if buy_order is None:
            下一单 buy_order
        elif 'finish' == buy_order.state:
            sell_order = None
            下一单 sell_order
            if order_num < max_order_level:
                order_num = order_num + 1
                buy_order = None
        if 'finish' == sell_order.state:
            order_num = 0
            buy_order = None
            sell_order = None
        """
        balance_amount = info['balance_amount']
        order_num = info['order_num']
        buy_order = info['buy_order']
        sell_order = info['sell_order']
        close = df.iloc[-1]['close']

        # 没有下单，下一单
        if buy_order is None and order_num < max_order_level:
            if 0 == order_num:
                # 计算价差
                diff_price = (close * max_diff_rate) / max_order_level
                # 每一份金额
                per_order_amount = balance_amount / total_level
                # 订单单价 第一单简化操作，就等于当前价
                order_price = close
                flag = 'deal_now'

                info['diff_price'] = diff_price
                info['per_order_amount'] = per_order_amount
            else:
                # 获取价差
                diff_price = info['diff_price']
                # 获取每一份金额
                per_order_amount = info['per_order_amount']
                # 订单单价 低于前面价一个diff
                order_price = info['last_buy_price'] - diff_price
                flag = ''

            # 订单金额 每一份的金额 * 份数
            order_amount = per_order_amount * level_list[order_num]
            # 下一单
            info['buy_order'] = {
                'order_size': None,  # 下单卖出的数量，卖单需要
                'order_price': order_price,  # 下单价格
                'order_amount': order_amount,  # 下单买入的金额，买单需要
                'state': 'submit',  # 状态 submit 下单 finish 成交
                'flag': flag,  # 回测特殊标记，deal_now 第一个买单和最后一个爆单，直接成交
            }
        if buy_order is not None and 'finish' == buy_order['state']:
            order_size = info['balance_size']
            diff_price = info['diff_price']
            order_price = info['last_buy_price'] + diff_price
            info['sell_order'] = {
                'order_size': order_size,  # 下单卖出的数量，卖单需要
                'order_price': order_price,  # 下单价格
                'order_amount': None,  # 下单买入的金额，买单需要
                'state': 'submit',  # 状态 submit 下单 finish 成交
                'flag': '',
            }

            info['order_num'] = order_num + 1
            info['buy_order'] = None
        if sell_order is not None and 'finish' == sell_order['state']:
            info['order_num'] = 0
            info['buy_order'] = None
            info['sell_order'] = None
        # 最后一个num要考虑破网，如果下跌超过一个diff，重新提交卖单，直接成交
        if order_num == max_order_level \
                and sell_order is not None \
                and (info['last_buy_price'] - close) > info['diff_price']:
            order_size = info['balance_size']
            order_price = close
            info['sell_order'] = {
                'order_size': order_size,  # 下单卖出的数量，卖单需要
                'order_price': order_price,  # 下单价格
                'order_amount': None,  # 下单买入的金额，买单需要
                'state': 'submit',  # 状态 submit 下单 finish 成交
                'flag': 'deal_now',
            }

    print('finish ' + title)


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


calculate_one([1, 0.005])

exit()

# =====并行提速
# max_order_level 2 ~ 12
# max_diff_rate 0.05 ~ 0.4 步进 0.02
para_list = gen_param_list(range(2, 13, 1), [i / 100 for i in list(range(5, 41, 2))])
with Pool(processes=8) as pool:  # or whatever your hardware can support
    pool.map(calculate_one, para_list)
