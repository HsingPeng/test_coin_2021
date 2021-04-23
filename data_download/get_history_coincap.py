# -*- coding: utf-8 -*-

import requests
import time
import sys

''' 从数据里解析每一天的开盘价和收盘价（第二天的开盘价），存储到csv文件
输出示例：
date,open,close
2003-01-02,14.36,14.8
2003-01-03,14.8,14.9
2003-01-06,15.03,14.9
2003-01-07,14.79,14.85
2003-01-08,14.58,14.55
'''
def jsonToCsv(json, csv_name):
    file = open(csv_name, 'w')
    file.write("date,open,close\n")
    open_price = None
    for day in json['data']:
        close_price = day['priceUsd']
        if open_price == None:
            open_price = close_price
            continue
        dt = time.strftime("%Y-%m-%d", time.localtime(day['time'] / 1000 - 3600 * 24))
        file.write("%s,%s,%s\n" % (dt, open_price, close_price))
        open_price = close_price

'''
返回示例：
{"data":[{
    "id":"bitcoin",
    "rank":"1",
    "symbol":"BTC",
    "name":"Bitcoin",
    "supply":"17631162.0000000000000000",
    "maxSupply":"21000000.0000000000000000",
    "marketCapUsd":"91253324284.7632911367934616",
    "volumeUsd24Hr":"5693060234.9839984925307336",
    "priceUsd":"5175.6840691931303868",
    "changePercent24Hr":"3.1378111969188786",
    "vwap24Hr":"5035.0813959363026487"
},...
'''
assets_url = 'https://api.coincap.io/v2/assets'
ret = requests.get(assets_url)
ret_list = ret.json()
coin_list = []
for item in ret_list['data']:
    print('set coin:%s' % item['id'])
    coin_list.append(item['id'])

'''
返回示例
{'data': [
{'priceUsd': '13430.4026814754906770', 'time': 1514764800000, 'date': '2018-01-01T00:00:00.000Z'},
 {'priceUsd': '13882.5933520000409847', 'time': 1514851200000, 'date': '2018-01-02T00:00:00.000Z'}, ...
'''
for coin in coin_list:
    # 1514736000000 2018年1月1日 到 1546272000000 2018年12月31日
    history_url = 'https://api.coincap.io/v2/assets/%s/history?interval=d1&start=1514736000000&end=1546272000000' % coin
    print('set url:%s' % history_url)
    ret = requests.get(history_url)
    jsonToCsv(ret.json(), 'sk_csv/sk_history_%s_2018.csv' % coin)
    
