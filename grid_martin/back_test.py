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

import pandas as pd
from datetime import timedelta
import numpy as np

pd.set_option('expand_frame_repr', False) # 列太多时不换行

# 初始配置
symbol_config = {
    'max_order_level': 10,  # 资金最多能下单几次，10代表剩余资金可以下10次单
    'max_diff_rate': 0.1,   # 最大破网百分比
    'total_level': 2048,        # 资金分成多少份
    'level_list': [1, 2, 4, 8, 16, 32, 64, 128, 256, 1024],
}

init_info = {
    'init_balance_amount': 2048,        # 初始余额
}

# 初始化数据
info = {
    'balance_amount': init_info['init_balance_amount'],  # 余额
    'balance_size': 0,      # 剩余的币数
    'diff_price': None,  # 当前价差
    'order_num': 0,  # 已经下单的次数，0 代表没下单，1~9 代表下了几次单，一轮还没有结束
    'last_buy_price': None,  # 上个买单的价格
    'last_buy_amount': None,  # 上个买单的数量
    'buy_order': None,
    'sell_order': None,
}

# === 由于是回测，一次读入全部数据
source_df = pd.read_csv(
    filepath_or_buffer='ETH-USDT2_2000.csv',
    encoding='gbk',
    parse_dates=['candle_begin_time'],
    index_col=['candle_begin_time'],
)

# df.sort_values(by=['candle_begin_time'], inplace=True) # 任何原始数据读入都进行一下排序、去重，以防万一

# 遍历每条数据，只保留最近的3条数据
max_len = 3
df = pd.DataFrame()
for candle_begin_time, row in source_df.iterrows():
    series = pd.Series({
            'open': row['open'],
            'high': row['high'],
            'low': row['low'],
            'close': row['close'],
            'volume': row['volume'],
        }, name=candle_begin_time)

    df = df.append(series, ignore_index=False)
    df = df.iloc[-max_len:]  # 保持最大K线数量不会超过max_len个
    # print(df)

    # 计算上次下单请求是否成交，计算余额
    """
    'balance_amount': 100,          # 余额
    'diff_price': 344,            # 当前价差
    'per_order_amount': 0,          # 每次交易的金额
    'order_num': 1,                 # 已经下单的次数，0 代表没下单，1~9 代表下了几次单，一轮还没有结束
    'last_buy_price': 54341,            # 上个买单的价格
    'last_buy_amount':2,                # 上个买单的数量
    'buy_order': {
            'order_size':0.1                # 下单卖出的数量，卖单需要
            'order_price':414134            # 下单价格
            'order_amount':200              # 下单买入的金额，买单需要
            'state':1                       # 状态 1 下单 2 成交
        },
    'sell_order':{}
    """

    # 计算信号，下单
    """
    状态
    1 当前没有单子 order_num = 0
    - 计算下单价格 order_price，下单金额 order_amount，提交一单。
    - diff_price = (close * max_diff_rate) / total_level        计算价差
    - order_price = close - diff_price   订单单价
    - order_amount = (balance_amount / total_level) * level_list[order_num]     订单金额
    - order(order_price, order_amount) 下买单
    2 开一单 order_num == 1 && buy_order.length == 1
    - 等待成交
    3 一单成交 order_num == 1 && buy_order.length == 0
    - 同时开获利单、下一单
    4 同时开获利单、下一单 order_num >= 2 && buy_order.length == 1 && sell_order.length == 1
    - 等待成交
    5 获利单成交 order_num >= 2 && buy_order.length == 1 && sell_order.length == 0
    - 取消下一单，本轮结束
    6 下一单成交 order_num >= 2 && buy_order.length == 0 && sell_order.length == 1
    - 取消当前获利单。同时开获利单、下一单
    """
    total_level = symbol_config['total_level']
    level_list = symbol_config['level_list']
    max_diff_rate = symbol_config['max_diff_rate']
    max_order_level = symbol_config['max_order_level']
    balance_amount = info['balance_amount']
    order_num = info['order_num']
    buy_order = info['buy_order']
    sell_order = info['sell_order']

    # 1 当前没有单子 -> 下一单
    if 0 == order_num:
        close = df.iloc[-1]['close']
        # 计算价差
        diff_price = (close * max_diff_rate) / max_order_level
        # 订单单价 低于当前价一个diff
        order_price = close - diff_price
        # 每一份金额
        per_order_amount = balance_amount / total_level
        # 订单金额 每一份的金额 * 份数
        order_amount = per_order_amount * level_list[order_num]
        # 下一单
        info['buy_order'] = {
            'order_size': None,                     # 下单卖出的数量，卖单需要
            'order_price': order_price,             # 下单价格
            'order_amount': order_amount,           # 下单买入的金额，买单需要
            'state': 1                              # 状态 1 下单 2 成交
        }
        info['diff_price'] = diff_price
        info['per_order_amount'] = per_order_amount
        info['order_num'] = 1
    elif 1 == order_num:
        # 3 一单成交 -> 同时开获利单、下一单
        if buy_order is None:
            per_order_amount = info['per_order_amount']
            close = df.iloc[-1]['close']
            # 计算价差
            diff_price = info['diff_price']
            # 订单单价 低于前面价一个diff
            order_price = info['last_buy_price'] - diff_price
            order_amount = per_order_amount * level_list[order_num]
            info['buy_order'] = {
                'order_size': None,                     # 下单卖出的数量，卖单需要
                'order_price': order_price,             # 下单价格
                'order_amount': order_amount,           # 下单买入的金额，买单需要
                'state': 1                              # 状态 1 下单 2 成交
            }

            balance_size = info['balance_size']
            order_price = info['last_buy_price'] + diff_price
            info['sell_order'] = {
                'order_size': balance_size,  # 下单卖出的数量，卖单需要
                'order_price': order_price,  # 下单价格
                'order_amount':  None,  # 下单买入的金额，买单需要
                'state': 1  # 状态 1 下单 2 成交
            }
        # 2 开一单 -> 等待成交
        else:
            pass
    else:
        # 4 同时开获利单、下一单 -> 等待成交
        if buy_order is not None and sell_order is not None:
            pass
        # 5 获利单成交 -> 取消下一单，本轮结束
        elif buy_order is not None and sell_order is None:
            info['buy_order'] = None
            info['sell_order'] = None
            info['order_num'] = 0
            info['diff_price'] = None
            info['last_buy_price'] = None
            info['last_buy_amount'] = None
        # 6 下一单成交 -> 取消当前获利单。同时开新获利单、下一单
        elif buy_order is None and sell_order is not None:
            order_num = order_num + 1
            info['order_num'] = order_num

            per_order_amount = info['per_order_amount']
            close = df.iloc[-1]['close']
            # 计算价差
            diff_price = info['diff_price']
            # 订单单价 低于前面价一个diff
            order_price = info['last_buy_price'] - diff_price
            order_amount = per_order_amount * level_list[order_num]
            info['buy_order'] = {
                'order_size': None,  # 下单卖出的数量，卖单需要
                'order_price': order_price,  # 下单价格
                'order_amount': order_amount,  # 下单买入的金额，买单需要
                'state': 1  # 状态 1 下单 2 成交
            }

            balance_size = info['balance_size']
            order_price = info['last_buy_price'] + diff_price
            info['sell_order'] = {
                'order_size': balance_size,  # 下单卖出的数量，卖单需要
                'order_price': order_price,  # 下单价格
                'order_amount': None,  # 下单买入的金额，买单需要
                'state': 1  # 状态 1 下单 2 成交
            }
        # 7 理论不可能发生，获利单、下一单都成交 -> 本轮结束
        else:
            info['buy_order'] = None
            info['sell_order'] = None
            info['order_num'] = 0
            info['diff_price'] = None
            info['last_buy_price'] = None
            info['last_buy_amount'] = None

exit()

# =====读入数据
df = pd.read_csv(
    filepath_or_buffer='ETH-USDT2_2000.csv',
    encoding='gbk',
    parse_dates=['candle_begin_time'],
    index_col=['candle_begin_time'],
)

# 任何原始数据读入都进行一下排序、去重，以防万一
df.sort_values(by=['candle_begin_time'], inplace=True)
# df.drop_duplicates(subset=['candle_begin_time'], keep='last', inplace=True)
# df.reset_index(inplace=True, drop=True)

df.dropna(subset=['open'], inplace=True)  # 去除一天都没有交易的周期
df = df[df['volume'] > 0]  # 去除成交量为0的交易周期

# para_list = signal_simple_bolling_para_list()
para_list = [[1]]

# =====遍历参数
rtn = pd.DataFrame()
for para in para_list:
    _df = df.copy()
    # 计算交易信号
    _df = signal_simple_bolling(_df, para=para)
    # 计算实际持仓
    _df = position_for_OKEx_future(_df)
    # 计算资金曲线
    _df = equity_curve_for_OKEx_USDT_future_next_open(_df, slippage=slippage, c_rate=c_rate, leverage_rate=leverage_rate,
                                                      face_value=face_value, min_margin_ratio=min_margin_ratio)
    # 计算收益
    r = _df.iloc[-1]['equity_curve']
    print(para, '策略最终收益：', r)
    rtn.loc[str(para), 'equity_curve'] = r

# =====输出
rtn.sort_values(by='equity_curve', ascending=False, inplace=True)
print(rtn)





