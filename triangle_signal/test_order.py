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

api_key = conf.Config.api_key
secret_key = conf.Config.secret_key
passphrase = conf.Config.passphrase

loop = asyncio.get_event_loop()

spotAPI = spot.SpotAPI(api_key, secret_key, passphrase, False)
result = loop.run_until_complete(
    spotAPI.take_order(
        instrument_id='LTC-USDT',
        side='buy',
        client_oid='HK1',
        type='market',
        size='',
        price='',
        order_type=0,
        notional='4'
    )
)
print(result)
