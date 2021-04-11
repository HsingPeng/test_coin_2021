"""
网格 + 马丁 回测

新策略：
● 当前价格投入一个单位
● 下跌扛单，直到扛到 num=a 时卖掉止损。亏损会随着num增大而增大。
● 上涨 num=1 就卖掉盈利

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
    sell_level = param[0]     # 0 ~ 10
    diff_rate = param[1]      # 0.03 ~ 0.4 步进 0.02

    total_level = 3
    symbol_config = {
        'sell_level': sell_level,  # 抗几次单就卖掉
        'diff_rate': diff_rate,  # 一个单位间隔的百分比
        'total_level': total_level,  # 资金分成多少份
        'fee': 0.001  # 手续费，千分之一
    }

    title = 'param_' + str(sell_level) + '_' + str(diff_rate)
    print('start ' + title)

    init_info = {
        'init_balance_amount': 200,  # 初始余额
    }

    # 初始化数据
    info = {
        'balance_amount': init_info['init_balance_amount'],  # 余额
        'balance_size': 0,  # 剩余的币数
        'diff_price': None,  # 当前价差
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

    # 遍历每条数据，只保留最近的 max_len 条数据
    max_len = 288
    show_num = 0
    order_num = 0
    df = pandas.DataFrame()
    for candle_begin_time, row in source_df.iterrows():
        # 一个k线重复多次，是因为当前K线是5min，太宽了，需要细化。
        for i in range(30, 190, 30):
            series = pandas.Series({
                'candle_begin_time': candle_begin_time + pandas.DateOffset(seconds=i),
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'volume': row['volume'],
                'balance_amount': info['balance_amount'],
                'balance_size': info['balance_size'],
                'order_num': order_num,
            }, name=candle_begin_time)

            df = df.append(series, ignore_index=False)
            df = df.iloc[-max_len:]  # 保持最大K线数量不会超过max_len个
            # print(df.iloc[-1].to_json())
            # print(json.dumps(info))
            df1 = df.iloc[-1]
            if show_num % 1000 == 0:
                # show(df)
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
            if str(df1['candle_begin_time']) == '2017-08-17 04:05:30':
                print('aaaa')

            total_level = symbol_config['total_level']
            diff_rate = symbol_config['diff_rate']
            sell_level = symbol_config['sell_level']
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
            if buy_order is None:  # 没下单
                下一单，立刻成交
            elif sell_order is None:    # 卖单已成交
                重置
                last_buy_price = None
                diff_price = None
                buy_order = None
                sell_order = None
            elif (last_buy_price - low) > (diff_price * sell_level):  # 达到止损卖单触发条件
                下卖单，立刻成交
            else:       # 更新获利卖单
                sell_order = None
                更新 sell_order
            
            """
            balance_amount = info['balance_amount']
            buy_order = info['buy_order']
            sell_order = info['sell_order']
            diff_price = info['diff_price']
            last_buy_price = info['last_buy_price']

            close = df.iloc[-1]['close']

            if buy_order is None:               # 没下单
                # 计算价差
                diff_price = close * diff_rate
                # 每一份金额
                per_order_amount = balance_amount / total_level
                # 订单单价 第一单简化操作，就等于当前价
                order_price = close
                flag = 'deal_now'

                info['diff_price'] = diff_price
                info['per_order_amount'] = per_order_amount

                # 订单金额 每一份的金额 * 份数
                order_amount = per_order_amount
                # 下一单
                info['buy_order'] = {
                    'order_size': None,  # 下单卖出的数量，卖单需要
                    'order_price': order_price,  # 下单价格
                    'order_amount': order_amount,  # 下单买入的金额，买单需要
                    'state': 'submit',  # 状态 submit 下单 finish 成交
                    'flag': flag,  # 回测特殊标记，deal_now 第一个买单和最后一个爆单，直接成交
                }
            elif sell_order is not None and 'finish' == sell_order['state']:        # 卖单已成交
                # 重置
                info['last_buy_price'] = None
                info['diff_price'] = None
                info['buy_order'] = None
                info['sell_order'] = None
                order_num = -1
            elif (last_buy_price - low) > (diff_price * (sell_level + 1)):  # 达到止损卖单触发条件
                order_num = int((last_buy_price - low) / diff_price)
                order_size = info['balance_size']
                order_price = close
                # 下卖单，立刻成交
                info['sell_order'] = {
                    'order_size': order_size,  # 下单卖出的数量，卖单需要
                    'order_price': order_price,  # 下单价格
                    'order_amount': None,  # 下单买入的金额，买单需要
                    'state': 'submit',  # 状态 submit 下单 finish 成交
                    'flag': 'deal_now',
                }
            elif 'finish' == buy_order['state']:  # 买单已成交，更新获利卖单
                order_size = info['balance_size']
                order_num = int((last_buy_price - low) / diff_price)
                order_price = last_buy_price - order_num * diff_price + diff_price
                info['sell_order'] = {
                    'order_size': order_size,  # 下单卖出的数量，卖单需要
                    'order_price': order_price,  # 下单价格
                    'order_amount': None,  # 下单买入的金额，买单需要
                    'state': 'submit',  # 状态 submit 下单 finish 成交
                    'flag': '',
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


calculate_one([1, 0.02])

exit()

# =====并行提速
# max_order_level 2 ~ 12
# max_diff_rate 0.05 ~ 0.4 步进 0.02
para_list = gen_param_list(range(2, 13, 1), [i / 100 for i in list(range(5, 41, 2))])
with Pool(processes=8) as pool:  # or whatever your hardware can support
    pool.map(calculate_one, para_list)
