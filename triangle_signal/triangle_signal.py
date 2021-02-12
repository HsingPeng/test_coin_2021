"""
交易信号
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
    elif (coin_2, coin_1) in pairs:
        key = (coin_2, coin_1)
    else:
        return ()

    return pairs[key]


def set_trade_info(coin_base, coin_target, price, size, timestamp):
    global pairs

    pairs[(coin_base, coin_target)] = (
        float(price),
        float(size),
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

channels = []               # channels = ["spot/trade:BTC-USDT"]
pair_set = {}               # pair_set['BTC'] = 1;
pairs = {}                  # pairs[('USDT', 'BTC')] = (price, size, timestamp, base_coin)
triangle_pairs = []         # triangle_pairs[] = (base, target1, target2)

# 初始化币对
for coin_info in result:
    instrument_id = coin_info['instrument_id']      # BTC-USDT
    # min_size = coin_info['min_size']
    coins = instrument_id.split('-')

    channels.append('spot/trade:' + instrument_id)
    pair_set[coins[0]] = 1
    pair_set[coins[1]] = 1
    pairs[(coins[1], coins[0])] = (0.0, 0.0, '', coins[1])

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
            # 暂时只需要 USDT
            if 'USDT' != coin1:
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
    if 'table' not in info or not info['table'] == 'spot/trade':
        continue

    data = info['data'][0]
    coins = data['instrument_id'].split('-')

    # 如果时间前移了，扫描交易链
    if not time_last == data['timestamp']:
        calculate_pairs(data['timestamp'])

    # 把每一条数据入库，然后计算三角套利
    set_trade_info(
        coin_base=coins[1],
        coin_target=coins[0],
        price=data['price'],
        size=data['size'],
        timestamp=data['timestamp']
    )



