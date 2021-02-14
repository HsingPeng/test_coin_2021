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

"""
async def read_queue(ws_queue):
    while True:
        response = await ws_queue.get()
        print(response)


channels = ['spot/order:LTC-USDT']

tasks = [
    # 订阅挂单信息
    asyncio.ensure_future(wsAPI.subscribe(url, api_key, passphrase, secret_key, channels, ws_queue)),
    # 保存挂单信息到变量
    asyncio.ensure_future(read_queue(ws_queue))
    # 定时扫描数据，下单
]
loop.run_until_complete(asyncio.wait(tasks))

loop.close()

exit()
"""


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


result = loop.run_until_complete(
    spotAPI.take_order(
        instrument_id='LTC-USDT',
        side='sell',
        client_oid='',
        type='market',
        size='0.01',
        price='',
        order_type=0,
        notional=''
    )
)

print(result)
