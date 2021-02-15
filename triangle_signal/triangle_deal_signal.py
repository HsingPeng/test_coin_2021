"""
交易信号
用买一卖一挂单判断
"""
import sys
import json

import okex.account_api as account
import okex.futures_api as future
import okex.lever_api as lever
import okex.spot_api as spot
import okex.swap_api as swap
import okex.index_api as index
import okex.option_api as option
import okex.system_api as system
import okex.information_api as information


def get_trade_info(coin_1, coin_2):
    """
    :param coin_1: string
    :param coin_2: string
    :return: (price, size, timestamp, base_coin)
    """
    global pairs

    if (coin_1, coin_2) in pairs:
        key = (coin_1, coin_2)
    else:
        return ()   # 这里拿去计算会报错

    return pairs[key]


def set_trade_info(coin_base, coin_target, best_ask, best_bid, best_ask_size, best_bid_size, timestamp):
    global pairs

    # 买操作，看的是卖一 best_ask
    pairs[(coin_base, coin_target)] = (
        float(best_ask),
        float(best_ask_size),
        timestamp,
        coin_base
    )

    # 卖操作
    pairs[(coin_target, coin_base)] = (
        float(best_bid),
        float(best_bid_size),
        timestamp,
        coin_base
    )


def deal_coin(base_coin, coin_1, coin_2, price, coin1_size):
    # 计算交易 目标币数量 = 当前币数量 * 价格
    # 基础币是当前币，就是买，否则是卖
    if coin_1 == base_coin:
        coin2_size = coin1_size / price
    elif coin_2 == base_coin:
        coin2_size = coin1_size * price
    else:
        coin2_size = 0

    return coin2_size


def calculate_pairs(timestamp):
    global triangle_pairs

    # 依次扫描每个交易链
    for pair in triangle_pairs:
        coin1 = pair[0]
        coin2 = pair[1]
        coin3 = pair[2]

        info1 = get_trade_info(coin1, coin2)
        info2 = get_trade_info(coin2, coin3)
        info3 = get_trade_info(coin3, coin1)
        if 0.0 == info1[0] or 0.0 == info2[0] or 0.0 == info3[0]:
            continue

        init_size = 100     # 初始币数量，就是 USDT 数量
        coin2_size = deal_coin(info1[3], coin1, coin2, info1[0], init_size)
        coin3_size = deal_coin(info2[3], coin2, coin3, info2[0], coin2_size)
        final_size = deal_coin(info3[3], coin3, coin1, info3[0], coin3_size)

        if final_size < 103:
            continue

        # print(init_size, info1, info2, info3, pair, coin2_size, coin3_size, final_size)

        print(timestamp, coin1, coin2, coin3, final_size, sep="\t")


api_key = ""
secret_key = ""
passphrase = ""


# 拿到所有交易对
spotAPI = spot.SpotAPI(api_key, secret_key, passphrase, False)
result = spotAPI.get_coin_info()
# print(json.dumps(result))

pair_set = {}               # pair_set['BTC'] = 1;
pairs = {}                  # pairs[('USDT', 'BTC')] = (price, size, timestamp, base_coin)
triangle_pairs = []         # triangle_pairs[] = (base, target1, target2)

# 初始化币对
for coin_info in result:
    instrument_id = coin_info['instrument_id']      # BTC-USDT
    # min_size = coin_info['min_size']
    coins = instrument_id.split('-')

    pair_set[coins[0]] = 1
    pair_set[coins[1]] = 1
    pairs[(coins[1], coins[0])] = (0.0, 0.0, '', coins[1])
    pairs[(coins[0], coins[1])] = (0.0, 0.0, '', coins[1])

# 初始化交易链
for coin1 in pair_set.keys():
    for coin2 in pair_set.keys():
        for coin3 in pair_set.keys():
            if not ((coin1, coin2) in pairs or (coin2, coin1) in pairs):
                continue
            if not ((coin2, coin3) in pairs or (coin3, coin2) in pairs):
                continue
            if not ((coin1, coin3) in pairs or (coin3, coin1) in pairs):
                continue
            # 需要赚哪个币
            if 'ETH' != coin1:
                continue
            triangle_pairs.append((coin1, coin2, coin3))

print('start...')

# 读取成交记录
input_file = sys.argv[1]
f = open(input_file, 'r')

time_last = ''
while True:
    line_str = f.readline()
    if not line_str:
        break
    line = line_str.split("\t")
    if not len(line) == 2:
        continue
    info = json.loads(line[1])
    if not info:
        continue
    if 'table' not in info or not info['table'] == 'spot/ticker':
        continue

    data = info['data'][0]
    coins = data['instrument_id'].split('-')

    # 如果时间前移了，扫描交易链，然后计算三角套利
    if not time_last == data['timestamp']:
        calculate_pairs(data['timestamp'])

    # 把每一条数据入库
    set_trade_info(
        coin_base=coins[1],
        coin_target=coins[0],
        best_ask=data['best_ask'],
        best_bid=data['best_bid'],
        best_ask_size=data['best_ask_size'],
        best_bid_size=data['best_bid_size'],
        timestamp=data['timestamp']
    )

