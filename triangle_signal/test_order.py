"""
测试下单
"""
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

url = 'wss://real.okex.com:8443/ws/v3'

api_key = conf.Config.api_key
secret_key = conf.Config.secret_key
passphrase = conf.Config.passphrase


loop = asyncio.get_event_loop()
wsAPI = ws.WsAPI()

spotAPI = spot.SpotAPI(api_key, secret_key, passphrase, False)
ws_queue = asyncio.Queue(100)                # 用于接收订阅数据


async def read_queue(ws_queue):
    while True:
        response = await ws_queue.get()
        print(response)


async def get_filled_order(ws_queue, order_id):
    while True:
        response = await ws_queue.get()

        if 'table' not in response['res']:
            continue
        if not 'spot/order' == response['res']['table']:
            continue
        data = response['res']['data'][0]
        if not order_id == data['order_id']:
            continue
        if not 2 == int(data['state']):
            continue

        filled_notional = data['filled_notional']
        filled_size = data['filled_size']
        return filled_notional, filled_size


async def multi_trade(ws_queue):
    await asyncio.sleep(3)

    # 买一单
    result = await spotAPI.take_order(
            instrument_id='LTC-USDT',
            side='buy',
            client_oid='',
            type='market',
            size='',
            price='',
            order_type=0,
            notional='2.4'
        )

    print(11, result)
    if not result['result']:
        print('交易出错')
        return

    filled_notional, filled_size = await get_filled_order(ws_queue, result['order_id'])
    size = int(float(filled_size) * 1000) / 1000
    print('cc', filled_notional, filled_size, size)

    # 卖一单
    result = await spotAPI.take_order(
        instrument_id='LTC-USDT',
        side='sell',
        client_oid='',
        type='market',
        size=size,
        price='',
        order_type=0,
        notional=''
    )
    print(22, result)
    if not result['result']:
        print('交易出错')
        return

    filled_notional, filled_size = await get_filled_order(ws_queue, result['order_id'])
    print('dd', filled_notional, filled_size)


channels = ['spot/order:LTC-USDT']

tasks = [
    # 订阅挂单信息
    asyncio.ensure_future(wsAPI.subscribe(url, api_key, passphrase, secret_key, channels, ws_queue)),
    # 保存挂单信息到变量
    asyncio.ensure_future(multi_trade(ws_queue))
    # 定时扫描数据，下单
]
loop.run_until_complete(asyncio.wait(tasks))

loop.close()

exit()

"""
result = loop.run_until_complete(
    spotAPI.take_order(
        instrument_id='LTC-USDT',
        side='buy',
        client_oid='',
        type='market',
        size='',
        price='',
        order_type=0,
        notional='4'
    )
)
"""
"""
result = loop.run_until_complete(
    spotAPI.get_order_info(instrument_id='LTC-USDT', order_id='6460399606644736', client_oid='')
)
"""



