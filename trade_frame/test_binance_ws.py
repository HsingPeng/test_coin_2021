"""
测试 binance 的 websocket
"""

import threading
import logging
import time
import websocket
import conf.conf


class WsThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.ws = None
        self.url = 'wss://stream.binance.com:9443/stream?streams=btcusdt@aggTrade/T80T31ljwp4Sz0G1HAOGbhxOjD3OuB3RiFPyjJqr8PV4dNPkUrjDHNf0yv23'

    def run(self):
        self.ws = websocket.WebSocketApp(self.url,
                                         on_open=self.on_open,
                                         on_message=self.on_message,
                                         on_error=self.on_error,
                                         on_close=self.on_close)
        # 针对网络设置代理
        if conf.conf.Config.http_proxy_host is not None:
            host = conf.conf.Config.http_proxy_host
            port = conf.conf.Config.http_proxy_port
            proxy_type = conf.conf.Config.proxy_type
            self.ws.run_forever(http_proxy_host=host, http_proxy_port=port, proxy_type=proxy_type)
        else:
            self.ws.run_forever()

    def on_message(self, ws, message):
        print("####### on_message #######")
        print(self)
        print(message)

    def on_error(self, ws, error):
        print("####### on_error #######")
        print(self)
        print(error)

    def on_close(self, ws, close_status_code, close_msg):
        print("####### on_close #######")
        print(self)
        print("####### closed #######")
        self.ws = None

    def on_open(self, ws):
        print("####### on_open #######")
        print(self)

    def heartbeat(self):
        print("####### heartbeat #######")


class HeartbeatThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        # TODO: listen key续期
        time.sleep(28)
        while True:
            time.sleep(28)


if __name__ == "__main__":
    websocket.enableTrace(False)

    wsT = WsThread()
    wsT.start()
    hbT = HeartbeatThread()
    hbT.start()

"""
行情通道可以和账户通道同时订阅

行情返回：
{"stream":"btcusdt@aggTrade","data":{"e":"aggTrade","E":1623679087810,"s":"BTCUSDT","a":807067972,"p":"40489.99000000","q":"0.00069100","f":909203645,"l":909203645,"T":1623679087810,"m":true,"M":true}}


下单返回3个：

新下单：
{"stream":"T80T31ljwp4Sz0G1HAOGbhxOjD3OuB3RiFPyjJqr8PV4dNPkUrjDHNf0yv23","data":{"e":"executionReport","E":1623677989738,"s":"EOSUSDT","c":"and_f4ebcde107ba499db8572eb01d0c304c","S":"BUY","o":"MARKET","f":"GTC","q":"1.95000000","p":"0.00000000","P":"0.00000000","F":"0.00000000","g":-1,"C":"","x":"NEW","X":"NEW","r":"NONE","i":2175686150,"l":"0.00000000","z":"0.00000000","L":"0.00000000","n":"0","N":null,"T":1623677989737,"t":-1,"I":4480149832,"w":true,"m":false,"M":false,"O":1623677989737,"Z":"0.00000000","Y":"0.00000000","Q":"10.00000000"}}
单成交：
{"stream":"T80T31ljwp4Sz0G1HAOGbhxOjD3OuB3RiFPyjJqr8PV4dNPkUrjDHNf0yv23","data":{"e":"executionReport","E":1623677989738,"s":"EOSUSDT","c":"and_f4ebcde107ba499db8572eb01d0c304c","S":"BUY","o":"MARKET","f":"GTC","q":"1.95000000","p":"0.00000000","P":"0.00000000","F":"0.00000000","g":-1,"C":"","x":"TRADE","X":"FILLED","r":"NONE","i":2175686150,"l":"1.95000000","z":"1.95000000","L":"5.12800000","n":"0.00002007","N":"BNB","T":1623677989737,"t":146728940,"I":4480149833,"w":false,"m":false,"M":true,"O":1623677989737,"Z":"9.99960000","Y":"9.99960000","Q":"10.00000000"}}
余额变化：
{"stream":"T80T31ljwp4Sz0G1HAOGbhxOjD3OuB3RiFPyjJqr8PV4dNPkUrjDHNf0yv23","data":{"e":"outboundAccountPosition","E":1623677989738,"u":1623677989737,"B":[{"a":"BNB","f":"0.19238282","l":"0.00000000"},{"a":"EOS","f":"1.95000000","l":"0.00000000"},{"a":"USDT","f":"2407.69271910","l":"0.00000000"}]}}


"""

