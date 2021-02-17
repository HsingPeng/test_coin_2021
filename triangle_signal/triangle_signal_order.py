"""
交易信号
利用最新的成交价格判断的
"""
import sys
import json
import asyncio
import bisect
import logging

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


def get_trade_info(coin_1, coin_2):
    """
    :param coin_1: string
    :param coin_2: string
    :return: (price, size, timestamp, base_coin, target_coin, min_size, tick_size)
    """
    global pairs

    if (coin_1, coin_2) in pairs:
        key = (coin_1, coin_2)
    else:
        return ()   # 这里拿去计算会报错

    return pairs[key]


def set_trade_info(coin_base, coin_target, best_ask, best_bid, best_ask_size, best_bid_size, timestamp):
    global pairs

    min_size = pairs[(coin_base, coin_target)][5]

    # print('set_trade_info', coin_base, coin_target, best_ask, best_bid, best_ask_size, best_bid_size, timestamp, min_size, tick_size)

    # 去掉最小交易量大于 10 usdt 的
    if 'USDT' == coin_base and (float(min_size) * float(best_bid)) > 10.0:
        best_ask = 0.0
        best_bid = 0.0
    elif 'BTC' == coin_base and (float(min_size) * float(best_bid)) > 0.0001:
        best_ask = 0.0
        best_bid = 0.0
    elif 'ETH' == coin_base and (float(min_size) * float(best_bid)) > 0.001:
        best_ask = 0.0
        best_bid = 0.0

    # 买操作，看的是卖一 best_ask
    pairs[(coin_base, coin_target)] = (
        float(best_ask),
        float(best_ask_size),
        timestamp,
        coin_base,
        coin_target,
        min_size,
        pairs[(coin_base, coin_target)][6]
    )

    # 卖操作
    pairs[(coin_target, coin_base)] = (
        float(best_bid),
        float(best_bid_size),
        timestamp,
        coin_base,
        coin_target,
        min_size,
        pairs[(coin_target, coin_base)][6]
    )


def deal_coin(base_coin, coin_1, coin_2, price, coin1_size, best_size):
    # 计算交易 目标币数量 = 当前币数量 * 价格
    # 基础币是当前币，就是买，否则是卖
    if coin_1 == base_coin:
        coin2_size = coin1_size / price
        side = 'buy'
        instrument_id = coin_2 + '-' + base_coin
        notional = coin1_size
        size = ''
    elif coin_2 == base_coin:
        coin2_size = coin1_size * price
        side = 'sell'
        instrument_id = coin_1 + '-' + base_coin
        notional = ''
        size = coin1_size
    else:
        coin2_size = 0
        side = ''
        instrument_id = ''
        notional = ''
        size = ''

    if best_size < coin1_size:
        coin2_size = 0

    return coin2_size, side, instrument_id, notional, size


def calculate_pairs():
    global triangle_pairs

    profit_list = []

    # 依次扫描每个交易链
    for pair in triangle_pairs:
        coin1, coin2, coin3 = pair

        price1, size1, timestamp1, base_coin1, target_coin1, min_size1, tick_size1 = get_trade_info(coin1, coin2)
        price2, size2, timestamp2, base_coin2, target_coin2, min_size2, tick_size2 = get_trade_info(coin2, coin3)
        price3, size3, timestamp3, base_coin3, target_coin3, min_size3, tick_size3 = get_trade_info(coin3, coin1)

        if 0.0 == price1 or 0.0 == price2 or 0.0 == price3:
            continue

        init_size = 1.0  # 初始币数量，就是 USDT 数量，如果挂单数量不满足，就放弃
        coin1_size, side1, instrument_id1, notional1, size1 \
            = deal_coin(base_coin1, coin1, coin2, price1, init_size, size1)
        coin2_size, side2, instrument_id2, notional2, size2 \
            = deal_coin(base_coin2, coin2, coin3, price2, coin1_size, size2)
        final_size, side3, instrument_id3, notional3, size3 \
            = deal_coin(base_coin3, coin3, coin1, price3, coin2_size, size3)

        # print('calculate_pairs', pair, init_size, coin1_size, coin2_size, final_size, sep="\t")

        if final_size < 1.01:
            continue

        bisect.insort(profit_list, (
            final_size,
            init_size,
            (side1, instrument_id1, notional1, size1, min_size1, tick_size1),
            (side2, instrument_id2, notional2, size2, min_size2, tick_size2),
            (side3, instrument_id3, notional3, size3, min_size3, tick_size3)
        ))

    profit_list.reverse()
    return profit_list


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


async def get_filled_order(ws_queue, order_id):
    while True:
        response = await ws_queue.get()

        if 'table' not in response['res']:
            continue
        if not 'spot/order' == response['res']['table']:
            continue

        logging.debug('get_filled_order ' + json.dumps(response))

        data = response['res']['data'][0]
        if not order_id == data['order_id']:
            continue
        if -1 == int(data['state']):
            logging.error('订单错误 ' + json.dumps(response))
            exit()
        if not 2 == int(data['state']):
            continue

        filled_notional = data['filled_notional']
        filled_size = data['filled_size']
        fee = data['fee']

        if '' == fee:
            fee = 0

        return float(filled_notional), float(filled_size), float(fee)


async def take_one_order(ws_queue, side, instrument_id, notional, size, tick_size):
    """
    下单并且等待订单成交
    :param ws_queue:
    :param side:
    :param instrument_id:
    :param notional:
    :param size:
    :param tick_size:
    :return:
    """
    # 格式化最小限额
    if not size == '':
        size = int(float(size) / tick_size) * tick_size

    logging.debug('take_one_order ' + '交易' + json.dumps((instrument_id, side, tick_size, size, '-', notional)))

    # 下一单
    result = await spotAPI.take_order(
            instrument_id=instrument_id,
            side=side,
            client_oid='',
            type='market',
            size=size,
            price='',
            order_type=0,
            notional=notional
        )

    logging.debug(('take_one_order' + ' result' . format(result)))

    if not result['result']:
        logging.error(('take_one_order '
                       + json.dumps(('交易出错', result, instrument_id, side, tick_size, size, '-', notional))))
        return

    filled_notional, filled_size, fee = await get_filled_order(ws_queue, result['order_id'])

    logging.debug('take_one_order' + json.dumps((filled_notional, filled_size, fee, result, tick_size, size)))

    return filled_notional, filled_size, fee


# 计算 下单
async def operate(ws_queue):
    while True:
        logging.debug('operate' + json.dumps(()))
        await asyncio.sleep(0.2)

        # 找出最佳交易对
        profit_list = calculate_pairs()

        if len(profit_list) == 0:
            continue

        logging.info('profit_list' + json.dumps(('一轮开始', profit_list[0])))
        final_size, init_size, order1, order2, order3 = profit_list[0]

        # 下单，等待结果
        size_or_notional = 10         # 暂时用x美元交易

        for order in [
            order1, order2, order3
        ]:
            side0, instrument_id0, notional0, size0, min_size0, tick_size0 = order
            # 初始值根据 buy sell 填充给不同的参数
            if 'buy' == side0:
                notional0 = size_or_notional
                size0 = ''
            else:
                size0 = size_or_notional
                notional0 = ''

            # 下一单
            filled_notional, filled_size, fee = \
                await take_one_order(ws_queue, side0, instrument_id0, notional0, size0, tick_size0)
            # fee 带符号的所以用 + fee
            if 'buy' == side0:
                size_or_notional = filled_size + fee
            else:
                size_or_notional = filled_notional + fee

        logging.info('operate' + json.dumps(('一轮结束', size_or_notional, final_size, init_size)))


loop = asyncio.get_event_loop()
wsAPI = ws.WsAPI()
logging.basicConfig(filename='main.log', level=logging.DEBUG,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s')
logging.getLogger('asyncio').setLevel(logging.ERROR)
logging.getLogger('asyncio.coroutines').setLevel(logging.ERROR)
logging.getLogger('websockets.server').setLevel(logging.ERROR)
logging.getLogger('websockets.protocol').setLevel(logging.ERROR)

url = 'wss://real.okex.com:8443/ws/v3'

api_key = conf.Config.api_key
secret_key = conf.Config.secret_key
passphrase = conf.Config.passphrase


# 拿到所有交易对
spotAPI = spot.SpotAPI(api_key, secret_key, passphrase, False)
result = loop.run_until_complete(spotAPI.get_coin_info())
logging.debug(json.dumps(result))

channels = []                                # channels = ["spot/trade:BTC-USDT", "spot/order:BTC-USDT"]
pair_set = {}                                # pair_set['BTC'] = 1;
pairs = {}                                   # pairs[('USDT', 'BTC')] = (price, size, timestamp, base_coin)
triangle_pairs = []                          # triangle_pairs[] = (base, target1, target2)
ticker_queue = asyncio.Queue(100)                # 用于接收订阅数据
order_queue = asyncio.Queue(100)                # 用于接收订阅数据

# 初始化币对
for coin_info in result:
    instrument_id = coin_info['instrument_id']      # BTC-USDT
    size_increment = coin_info['size_increment']      # 卖交易货币数量精度
    tick_size = coin_info['tick_size']              # 买使用最小交易价格精度
    min_size = coin_info['min_size']                # 最小交易数量
    coins = instrument_id.split('-')

    pair_set[coins[0]] = 1
    pair_set[coins[1]] = 1
    pairs[(coins[1], coins[0])] = (0.0, 0.0, '', coins[1], coins[0], float(min_size), float(tick_size))
    pairs[(coins[0], coins[1])] = (0.0, 0.0, '', coins[1], coins[0], float(min_size), float(size_increment))

    channels.append('spot/ticker:' + instrument_id)
    channels.append('spot/order:' + instrument_id)

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

logging.info('start...')

tasks = [
    # 订阅最新成交记录和订单结果
    asyncio.ensure_future(
        wsAPI.subscribe(url, api_key, passphrase, secret_key, channels, ticker_queue, order_queue)
    ),
    # 保存挂单信息到变量
    asyncio.ensure_future(update_ticker_info(ticker_queue)),
    # 计算 下单
    asyncio.ensure_future(operate(order_queue))
]
finished, pending = loop.run_until_complete(asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION))
for task in finished:
    if task.exception():
        logging.warning("{} got an exception {}, retrying" . format(task, task.exception()))

wsAPI.setRunning(False)
loop.close()

exit()
