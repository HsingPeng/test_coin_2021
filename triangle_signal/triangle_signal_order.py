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

trade_channels = []                                # channels = ["spot/trade:BTC-USDT"]
order_channels = []                                # channels = ["spot/order:BTC-USDT"]
pair_set = {}                                # pair_set['BTC'] = 1;
pairs = {}                                   # pairs[('USDT', 'BTC')] = (price, size, timestamp, base_coin)
triangle_pairs = []                          # triangle_pairs[] = (base, target1, target2)
ticker_queue = asyncio.Queue(100)                # 用于接收订阅数据
order_queue = asyncio.Queue(100)                # 用于接收订阅数据

# 初始化币对
for coin_info in result:
    instrument_id = coin_info['instrument_id']      # BTC-USDT
    # min_size = coin_info['min_size']
    coins = instrument_id.split('-')

    pair_set[coins[0]] = 1
    pair_set[coins[1]] = 1
    pairs[(coins[1], coins[0])] = (0.0, 0.0, '', coins[1])
    pairs[(coins[0], coins[1])] = (0.0, 0.0, '', coins[1])
    trade_channels.append('spot/ticker:' + instrument_id)
    order_channels.append('spot/order:' + instrument_id)

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
            if 'USDT' != coin1:
                continue
            triangle_pairs.append((coin1, coin2, coin3))

print('start...')


# 保存订阅数据
async def update_ticker_info(ws_queue):
    while True:
        response = await ws_queue.get()     # key: timestamp res
        # print('update_ticker_info', response)

        if 'table' not in response['res']:
            continue
        if not 'spot/ticker' == response['res']['table']:
            continue
        data = response['res']['data'][0]
        coins = data['instrument_id'].split('-')

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


# 计算 下单
async def operate(ws_queue):
    while True:
        print('operate')
        await asyncio.sleep(100)


tasks = [
    # 订阅挂单信息
    asyncio.ensure_future(wsAPI.subscribe_without_login(url, trade_channels, ticker_queue)),
    # 订阅订单结果
    asyncio.ensure_future(wsAPI.subscribe(url, api_key, passphrase, secret_key, order_channels, order_queue)),
    # 保存挂单信息到变量
    asyncio.ensure_future(update_ticker_info(ticker_queue)),
    # 计算 下单
    asyncio.ensure_future(operate(order_queue))
]
loop.run_until_complete(asyncio.wait(tasks))

loop.close()

exit()
