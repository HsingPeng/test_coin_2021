"""
okex监控永续资金费率，每天8：05运行，发送信息包含 当日，7日年化，30日年化，
本程序按utc时间撰写
更新时间：20200926
"""
import ccxt
import pandas as pd
import math
from time import sleep
import hmac
import hashlib
import base64
import json
import requests
import time
import traceback
from urllib import parse
from datetime import datetime, timedelta
import conf

pd.set_option('expand_frame_repr', False)
# pd.set_option('display.max_rows', 500)
# pd.set_option('display.min_rows', 500)

# ===创建交易所实例（使用公共接口，不需要apikey）
okex = ccxt.okex()

wx_webhook = conf.Config.wx_webhook
# 针对网络设置代理
if conf.Config.proxies is not None:
    okex.proxies = conf.Config.proxies


def send_weixin_msg(content, webhook):
    try:
        headers = {"Content-Type": "application/json;charset=utf-8"}
        msg = {
            "msgtype": "markdown",
            "markdown": {
                "content": content,
            }
        }
        body = json.dumps(msg)
        requests.post(webhook, data=body, headers=headers)
        print('成功发送钉钉')
    except Exception as e:
        print("发送钉钉失败:", e)


# ===定时运行
def next_run_time():
    now = datetime.utcnow()
    now = now.replace(hour=0, minute=0, second=0, microsecond=0)
    target_time = now + timedelta(days=1)
    target_time += timedelta(minutes=5)

    return target_time

# ===获取单个币种的资金费率
# 获取资金费率
def get_swap_funding_rate(instrument_id, max_try_num=5):
    param = {'instrument_id': instrument_id, 'limit': 100}  # limit最大为100，获取过去30天的历史资金费率
    for i in range(max_try_num):
        try:
            rate = okex.swap_get_instruments_instrument_id_historical_funding_rate(param)
            return pd.DataFrame(rate, dtype=float)
        except Exception as e:
            print(f'获取{instrument_id}资金费率错误，1s后重试:{e}')
            sleep(1)


# 单币种数据处理
def funding_rate_analyse(instrument_id):

    _df = get_swap_funding_rate(instrument_id)

    # ==整体时间并转化为1天的周期
    _df['funding_time'] = pd.to_datetime(_df['funding_time'])  #
    _df = _df.resample(rule='1D', on='funding_time', label='left', closed='left').agg(
        {
            'instrument_id': 'first',
            'funding_rate': 'sum',  # 稍微有些差异，本应该是复利连乘，这里采为sum，近似相等
            'realized_rate': 'sum',
         })

    # 重置index
    _df.reset_index(inplace=True)

    # 剔除最后一条数据。utc 0点运行，当天的只产生一条数据，求年化失真
    _df = _df[:-1]
    # ===计算统计量（当日年化， 7日年化，30日年化 %）    日复利
    # 当日年化
    _df['当日年化'] = round((pow((1 + _df['realized_rate']), 365) - 1) * 100, 2)
    # 7日年化
    _df['rtn_7d'] = _df['realized_rate'].rolling(7).apply(lambda x: (1 + x).prod())
    _df['7日年化'] = round((pow(_df['rtn_7d'], 365 / 7) - 1) * 100, 2)
    # 30日年化
    _df['rtn_30d'] = _df['realized_rate'].rolling(30).apply(lambda x: (1 + x).prod())
    _df['30日年化'] = round((pow(_df['rtn_30d'], 365 / 30) - 1) * 100, 2)

    # 保留数据
    _df = _df[['funding_time', 'instrument_id', 'realized_rate', '30日年化', '7日年化', '当日年化']]

    return _df


# ===主函数
def main():
    # ===查找所有币本位永续的instrument_id
    instrument_id_list = okex.swap_get_instruments()
    instrument_id_list = pd.DataFrame(instrument_id_list)
    instrument_id_list = list(instrument_id_list[instrument_id_list['quote_currency'].isin(['USD', 'USDT'])]['instrument_id'])
    # instrument_id_list = ['ETH-USD-SWAP', 'BTC-USD-SWAP']
    # ===获取永续的资金费率，合并
    all_coin_rate = pd.DataFrame()
    # 循环计算数据
    for instrument_id in instrument_id_list:
        df = funding_rate_analyse(instrument_id)
        all_coin_rate = all_coin_rate.append(df.iloc[-1], ignore_index=True)

    # 整理结果
    all_coin_rate = all_coin_rate[['instrument_id', '30日年化', '7日年化', '当日年化']]
    all_coin_rate.sort_values(by=['30日年化', '7日年化', '当日年化'], ascending=[0, 0, 0], inplace=True)
    all_coin_rate.set_index('instrument_id', drop=True, inplace=True)

    # 发送通知
    content = '## **OKEX永续币本位资金费率** \n'
    content += '  **| 30日年化% | 7日年化% | 当日年化% |** \n'
    i = 0
    for x, y in all_coin_rate.iterrows():
        # x = x.replace('-USDT-SWAP', '')
        content += '\n|**' + str(x) + '**：'
        y = list(y)
        for _ in y:
            content += str(_) + '  |  '
        content += ' \n'
        i += 1
        if i % 30 == 29:
            send_weixin_msg(content, wx_webhook)
            print(content)
            content = ''
    content += ' \n ' + datetime.now().strftime("%m-%d %H:%M:%S")
    print(content)
    send_weixin_msg(content, wx_webhook)

    # ===定时自动运行
    target_time = next_run_time()  # 北京时间每天早08：05, 即utc时间00：05
    print('本次运行完成，下次运行时间(UTC)：', target_time)
    sleep(max(0, (target_time - datetime.utcnow()).seconds))


# 主程序
if __name__ == '__main__':
    i = 0
    while True:
        try:
            main()
            i = 0
        except Exception as e:
            traceback.print_exc()
            print(e)
            print(f'okex资金费率监控，第{i}次尝试，运行报错{e}')
            send_weixin_msg(f'okex资金费率监控，第{i}次尝试，运行报错{e}', wx_webhook)
            sleep(10)
            if i >= 5:
                print('程序重试次数过多，退出')
                send_weixin_msg(f'资金费率，程序重试次数过多，已退出', wx_webhook)
                exit()
