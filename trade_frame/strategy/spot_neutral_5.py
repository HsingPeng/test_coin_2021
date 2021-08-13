"""
中性做市策略，一种网格。spot_neutral_4 的舍弃第一单的版本。spot_neutral_3 指标策略的可执行版本。
@Author : bboxhe@gmail.com

假设 diff = 1%
1 个单位的币：
1 上涨到-> 1.01 盈利卖出 全部
1 下跌到-> 0.99 止损卖出 全部（再等待价格回调一个diff）
基于此思路扩展

# 开始
balance_coin = 当前币的数量
std_price = 当前的标准价格
diff_price = std_price * diff_rate
std_amount 表示一次交易的币数量

开始循环
1. 按当前价格 std_price = current_price 为准，开一买单 price = std_price，amount = std_amount
2.1 如果价格上涨到 price = std_price + diff_price卖出，卖单要提前挂，成交就代表循环结束
2.2 如果价格下跌到 price = std_price - diff_price，卖出全部 amount = std_amount
3 进入回调等待阶段
- 接收最新成交价，标记最低价格 min_price = std_price - N * diff_price
- 当价格回调到 std_price - (N - 1) * diff_price，当前循环结束

"""

import controller
import math
import backtesting
import json
import pandas


class SpotNeutral5:
    def __win_rate(self, df, exchange, hour_section):
        df = df[df['time'] > (exchange.get_int_time() - int(3600 * hour_section))]  # 保留指定小时
        return df['win_num'].sum() / (df['lose_num'].sum() + df['win_num'].sum()) - 0.5

    def exec(self, _controller: controller.Controller, params: str):
        exchange = _controller.get_exchange()
        logger = exchange.logger

        diff_rate, target_coin, base_coin, total_coin_value = params.split('-')

        diff_rate = float(diff_rate)
        total_coin_value = float(total_coin_value)
        per_usdt = total_coin_value

        symbol = target_coin + '/' + base_coin

        sleep_time = 0.01        # 睡眠时间
        win_num = 1
        lose_num = 1
        all_num = 2
        df = pandas.DataFrame()
        series = pandas.Series({
            'time': exchange.get_int_time(),
            'win_num': 1,
            'lose_num': 1,
            'all_num': 2,
        }, name=exchange.get_int_time())
        df = df.append(series, ignore_index=True)

        init_value = None   # 初始价值
        max_value = None    # 最高价值，用于计算回撤
        min_value = None    # 最低价值，用于计算回撤

        log_startone_header = ['realtime', 'std_price', 'target_coin', 'base_coin', 'fee_usdt',
                               'init_value', 'current_value', 'profit_rate', 'max_drawdown', 'win_num', 'lose_num',
                               'all_num', 'win_rate', 'win_rate_12h', 'win_rate_6h', 'win_rate_3h', 'win_rate_1h',
                               'win_rate_0.5h',
                               'profit_rate_nofee', 'current_coin_value']
        _controller.header_to_csv(log_startone_header, 'startone')

        # 开始循环
        while True:
            ticker_info = exchange.fetch_ticker(symbol)
            std_price = ticker_info['last']  # 基准价格
            diff_price = std_price * diff_rate

            # 如果价格上涨了，本轮就结束
            while True:
                ticker_info = exchange.fetch_ticker(symbol)
                current_price = ticker_info['last']  # 基准价格
                if std_price - current_price >= diff_price:     # 下跌
                    finish = False
                    break
                elif current_price - std_price >= diff_price:   # 上涨
                    finish = True
                    break
            if finish:
                logger.debug('[%s] [skip one]std_price=%s, current_price=%s' %
                             (exchange.get_str_time(), std_price, current_price))
                continue
            std_price = current_price

            balance_info = exchange.fetch_balance()
            if init_value is None:
                init_price = std_price
                init_value = balance_info[target_coin]['total'] * init_price + balance_info[base_coin]['total']

            current_value = balance_info[target_coin]['total'] * std_price + balance_info[base_coin]['total'] \
                - exchange.get_fee_usdt()
            current_coin_value = balance_info[target_coin]['total'] * std_price

            if min_value is None:
                min_value = current_value
            else:
                min_value = min(min_value, current_value)
            if max_value is None:
                max_value = current_value
            else:
                max_value = max(max_value, current_value)

            df = df[df['time'] > (exchange.get_int_time() - 3600 * 12)]     # 12小时
            log_startone = {
                'realtime': exchange.get_str_time(),
                'std_price': std_price,
                'target_coin': balance_info[target_coin]['total'],
                'base_coin': balance_info[base_coin]['total'],
                'current_coin_value': current_coin_value,
                'fee_usdt': exchange.get_fee_usdt(),
                'init_value': init_value,
                'current_value': current_value,
                'profit_rate': ((current_value - init_value) / init_value),
                'profit_rate_nofee': ((current_value - init_value + exchange.get_fee_usdt()) / init_value),
                'max_drawdown': ((max_value - min_value) / max_value),
                'win_num': win_num,
                'lose_num': lose_num,
                'all_num': all_num,
                'win_rate': (win_num / (lose_num + win_num) - 0.5),
                'win_rate_12h': self.__win_rate(self, df, exchange, 12),
                'win_rate_6h': self.__win_rate(self, df, exchange, 6),
                'win_rate_3h': self.__win_rate(self, df, exchange, 3),
                'win_rate_1h': self.__win_rate(self, df, exchange, 1),
                'win_rate_0.5h': self.__win_rate(self, df, exchange, 0.5),
            }
            _controller.data_to_csv(log_startone_header, [log_startone], 'startone')
            logline = []
            for key in log_startone:
                logline.append('%s=%s' % (key, log_startone[key]))
            logger.info("[start one]%s" % "\t".join(logline))

            # 1 开一单，市价买单
            buy_order_info = exchange.create_market_buy_order(symbol, per_usdt)
            logger.debug('[%s] [create buy]cost=%s, price=%s' %
                         (exchange.get_str_time(), buy_order_info['cost'], buy_order_info['price']))

            # 等待成交
            waiting = True
            buy_amount = 0
            while waiting:
                orders_info = exchange.fetch_orders(symbol)
                for one_order in orders_info:
                    # 成交了
                    if buy_order_info['id'] == one_order['id'] and 'closed' == one_order['status']:
                        buy_amount = one_order['amount']

                        logger.debug('[%s] [closed buy]amount=%s, price=%s' %
                                     (exchange.get_str_time(), one_order['amount'], one_order['price']))

                        waiting = False
                        break

                exchange.sleep(sleep_time)

            # 开卖单
            pos_price = std_price + diff_price
            amount = buy_amount
            sell_order_info = exchange.create_limit_sell_order(symbol, amount, pos_price)
            logger.debug('[%s] [create sell]amount=%s, price=%s' %
                         (exchange.get_str_time(), sell_order_info['amount'], sell_order_info['price']))

            # 等待成交 或者等待下跌
            waiting = True
            while waiting:
                orders_info = exchange.fetch_orders(symbol)
                for one_order in orders_info:
                    if sell_order_info['id'] == one_order['id'] and 'closed' == one_order['status']:
                        waiting = False
                        win_num += 1
                        all_num += 1
                        series = pandas.Series({
                            'time': exchange.get_int_time(),
                            'win_num': 1,
                            'lose_num': 0,
                            'all_num': 1,
                        }, name=exchange.get_int_time())
                        df = df.append(series, ignore_index=True)

                        logger.debug('[%s] [closed sell]amount=%s, price=%s' %
                                     (exchange.get_str_time(), one_order['amount'], one_order['price']))
                        break

                if not waiting:
                    break

                # 等待下跌回调
                ticker_info = exchange.fetch_ticker(symbol)
                current_price = ticker_info['last']
                if std_price - current_price > diff_price:
                    # 下跌了一个diff，撤掉之前的单子
                    exchange.cancel_order(sell_order_info['id'], symbol)
                    # 立刻卖掉
                    amount = sell_order_info['amount']
                    sell_order_info = exchange.create_market_sell_order(symbol, amount)
                    logger.debug('[%s] [create market sell]amount=%s' %
                                 (exchange.get_str_time(), sell_order_info['amount']))

                    lose_num += 1
                    all_num += 1
                    series = pandas.Series({
                        'time': exchange.get_int_time(),
                        'win_num': 0,
                        'lose_num': 1,
                        'all_num': 1,
                    }, name=exchange.get_int_time())
                    df = df.append(series, ignore_index=True)

                    # 进入下跌回调等待
                    min_price = current_price
                    while True:
                        ticker_info = exchange.fetch_ticker(symbol)
                        current_price = ticker_info['last']
                        N = math.floor((std_price - current_price) / diff_price)
                        min_price = min(min_price, std_price - N * diff_price)
                        if current_price - min_price > diff_price:
                            waiting = False
                            logger.debug('[%s] [finish wait]current_price=%s std_price=%s' %
                                         (exchange.get_str_time(), current_price, std_price))
                            break

            balance_info = exchange.fetch_balance()
            current_value = balance_info[target_coin]['total'] * std_price + balance_info[base_coin]['total'] \
                - exchange.get_fee_usdt()
            min_value = min(min_value, current_value)
            max_value = max(max_value, current_value)
            logger.info("[finish one]%s" % "\t".join(
                [
                    'realtime=%s' % exchange.get_str_time(),
                    'std_price=%f' % std_price,
                    'target_coin=%f' % balance_info[target_coin]['total'],
                    'base_coin=%f' % balance_info[base_coin]['total'],
                    'target_coin_value=%f' % (std_price * balance_info[target_coin]['total']),
                    'fee_usdt=%f' % exchange.get_fee_usdt(),
                    'init_value=%f' % init_value,
                    'current_value=%f' % current_value,
                    'profit_rate=%f' % ((current_value - init_value) / init_value),
                    'profit_rate_nofee=%f' % ((current_value - init_value + exchange.get_fee_usdt()) / init_value),
                    'max_drawdown=%f' % ((max_value - min_value) / max_value),
                ]
            ))
