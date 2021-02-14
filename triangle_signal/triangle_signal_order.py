"""
交易信号
利用最新的成交价格判断的
"""
import sys
import json
import asyncio

import okex.account_api as account
import okex.futures_api as future
import okex.lever_api as lever
import okex.spot_api as spot
import okex.swap_api as swap
import okex.index_api as index
import okex.option_api as option
import okex.system_api as system
import okex.information_api as information
import okex.ws_api as ws
import conf as conf

loop = asyncio.get_event_loop()
wsAPI = ws.WsAPI()

url = 'wss://real.okex.com:8443/ws/v3'

api_key = conf.Config.api_key
secret_key = conf.Config.secret_key
passphrase = conf.Config.passphrase


# 拿到所有交易对
spotAPI = spot.SpotAPI(api_key, secret_key, passphrase, False)
result = loop.run_until_complete(spotAPI.get_coin_info())
print(json.dumps(result))

channels = []                                # channels = ["spot/trade:BTC-USDT"]
pair_set = {}                                # pair_set['BTC'] = 1;
pairs = {}                                   # pairs[('USDT', 'BTC')] = (price, size, timestamp, base_coin)
triangle_pairs = []                          # triangle_pairs[] = (base, target1, target2)
ws_queue = asyncio.Queue(100)                # 用于接收订阅数据

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


async def read_queue(ws_queue):
    while True:
        response = await ws_queue.get()
        print(response)


tasks = [
    # 订阅挂单信息
    asyncio.ensure_future(wsAPI.subscribe_without_login(url, channels, ws_queue)),
    # 保存挂单信息到变量
    asyncio.ensure_future(read_queue(ws_queue))
    # 定时扫描数据，下单
]
loop.run_until_complete(asyncio.wait(tasks))

loop.close()

exit()

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



