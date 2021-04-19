# -*- coding: utf-8 -*-

import requests
import time
import datetime
import sys


def jsonToCsv(is_first, json, csv_name):
    """
    从数据里解析数据，存储到csv文件
        输出示例：
        time,aggid,price,quantity,firstid,lastid,ismake
        2017-06-30 11:35:09.153,26129,0.01633102,4.70443515,27781,27781,1
    :param json:
    [
      {
        "a": 26129,         // 归集成交ID
        "p": "0.01633102",  // 成交价
        "q": "4.70443515",  // 成交量
        "f": 27781,         // 被归集的首个成交ID
        "l": 27781,         // 被归集的末个成交ID
        "T": 1498793709153, // 成交时间
        "m": true,          // 是否为主动卖出单
        "M": true           // 是否为最优撮合单(可忽略，目前总为最优撮合)
      }
    ]
    :param csv_name:
    :return :
    """
    file = open(csv_name, 'a')

    if is_first:
        file.write("time,aggid,price,quantity,firstid,lastid,ismake\n")

    for deal in json:
        dt = datetime.datetime.fromtimestamp(deal['T'] / 1000)
        strdt = dt.strftime("%Y-%m-%d %H:%M:%S.%f")
        file.write("%s,%s,%s,%s,%s,%s,%s\n" %
                   (strdt, deal['a'], deal['p'], deal['q'], deal['f'], deal['l'], 1 if deal['m'] else 0))


# proxies = {"http": "socks5h://127.0.0.1:1086", "https": "socks5h://127.0.0.1:1086"}
proxies = {"http": "socks5h://127.0.0.1:1080", "https": "socks5h://127.0.0.1:1080"}

coin_list = [
    'ETHUSDT',
]

'''
接口：https://binance-docs.github.io/apidocs/spot/cn/#c59e471e81

返回示例
[
  {
    "a": 26129,         // 归集成交ID
    "p": "0.01633102",  // 成交价
    "q": "4.70443515",  // 成交量
    "f": 27781,         // 被归集的首个成交ID
    "l": 27781,         // 被归集的末个成交ID
    "T": 1498793709153, // 成交时间
    "m": true,          // 是否为主动卖出单
    "M": true           // 是否为最优撮合单(可忽略，目前总为最优撮合)
  }
]
'''

for coin in coin_list:
    is_first = True
    from_id = 0
    from_id_param = ''
    current_time = time.time()
    filename = 'data/binance_csv/trade_%s_%s.csv' % (coin, current_time)
    while True:
        if from_id > 0:
            is_first = False
            from_id_param = '&fromId=%s' % from_id

        trade_url = 'https://api.binance.com/api/v3/aggTrades?symbol=%s%s&limit=10000' % (coin, from_id_param)
        print('set url:%s' % trade_url)
        ret = requests.get(trade_url, proxies=proxies)

        json_data = ret.json()
        if len(json_data) == 0:
            break

        json_data = sorted(json_data, key=lambda d: -d['a'])
        jsonToCsv(is_first, json_data, filename)
        from_id = json_data[-1]['a'] - 1000
        print(from_id)
