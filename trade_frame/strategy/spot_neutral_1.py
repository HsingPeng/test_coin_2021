"""
中性做市策略，一种网格
@Author : bboxhe@gmail.com

假设 diff=0.09%
1 个单位的币：
1 上涨到-> 1.009 平掉 0.0009
1 下跌到-> 0.991 开仓 0.0009
基于此思路扩展

# 开始
按市场价买入 1 个单位的币（这一步先手动操作吧）
balance_coin = 当前币的数量

开始循环
1. 按当前价格开一买单 price = std_price - diff_price
2. 按当前价格开一卖单 price = std_price + diff_price
3. 等待完全成交，先使用轮询，后续要求快的话，可以使用 websocket
- 只要其中一单完全成交，撤销剩下的单子。如果两个单子都成交，以卖单为准。
4.1 如果触发卖单完全成交，当前循环结束
4.2 如果触发买单完全成交，进入回调等待阶段
回调等待阶段:
- 最新成交价格比最低成交价格高一个 diff_price，代表回调完成。
5. 如果在最低价回调 diff_price，当前循环结束。
当前循环结束
"""

import controller
import backtesting
import json


class SpotNeutral1:
    def exec(self, _controller: controller.Controller, params: str):
        exchange = _controller.get_exchange()
        logger = exchange.logger

        diff_rate, target_coin, base_coin, total_coin_value = params.split('-')

        # 初始化
        # diff_rate = "0dot0009"
        # base_coin = 'USDT'
        # target_coin = 'ETH'
        # per_usdt = 11  # 由于当前比较特殊，资金不够。所以每次交易都用11usdt。之后改成比例

        diff_rate = float(diff_rate)
        total_coin_value = float(total_coin_value)
        per_usdt = total_coin_value * diff_rate
        min_usdt = 10
        if per_usdt < min_usdt:
            raise Exception('由于 binance 限制，每次开单必须要大于%su' % min_usdt)

        symbol = target_coin + '/' + base_coin

        sleep_time = 0.1        # 睡眠时间
        win_num = 1
        lose_num = 1
        init_price = None
        init_value = None   # 初始价值
        max_value = None    # 最高价值，用于计算回撤
        min_value = None    # 最低价值，用于计算回撤
        if 'extra' == exchange.get_fee_mode():
            extra_fee_mode = True
        else:
            extra_fee_mode = False

        log_startone_header = ['realtime', 'std_price', 'target_coin', 'base_coin', 'fee_usdt',
                               'init_value', 'current_value', 'profit_rate', 'max_drawdown', 'win_num', 'lose_num',
                               'win_rate', 'profit_rate_nofee', 'current_coin_value']
        _controller.header_to_csv(log_startone_header, 'startone')

        # 第一次平衡资金
        ticker_info = exchange.fetch_ticker(symbol)
        std_price = ticker_info['last']  # 基准价格，每轮重置
        balance_info = exchange.fetch_balance()

        balance_order_info = None
        default_coin_value = balance_info[target_coin]['total'] * std_price
        if total_coin_value - default_coin_value > min_usdt:     # 少了买一点
            balance_amount = total_coin_value - default_coin_value
            balance_order_info = exchange.create_market_buy_order(symbol, balance_amount)
            logger.info('[balance value]buy target coin=%s cost=%s' % (target_coin, balance_amount))
        elif default_coin_value - total_coin_value > min_usdt:   # 多了卖一点
            balance_amount = (default_coin_value - total_coin_value) / std_price
            balance_order_info = exchange.create_market_sell_order(symbol, balance_amount)
            logger.info('[balance value]sell target coin=%s amount=%s' % (target_coin, balance_amount))

        if balance_order_info is not None:
            # 循环等待完全成交
            not_finish = True
            while not_finish:
                # 如果没有完成，休眠
                exchange.sleep(sleep_time * 2)
                orders_info = exchange.fetch_orders(symbol)
                for one_order in orders_info:
                    if balance_order_info['id'] == one_order['id'] and 'closed' == one_order['status']:
                        if extra_fee_mode:
                            exchange.add_fee_usdt(one_order['cost'])
                        not_finish = False

        # 开始循环
        while True:
            # 每轮都重新获取当前价格
            ticker_info = exchange.fetch_ticker(symbol)
            std_price = ticker_info['last']     # 基准价格，每轮重置
            min_price = ticker_info['last']            # 判断回调使用，每轮重置

            balance_info = exchange.fetch_balance()
            if init_value is None:
                init_price = std_price
                init_value = balance_info[target_coin]['total'] * init_price + balance_info[base_coin]['total']
                default_coin_value = balance_info[target_coin]['total'] * init_price

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

            # 平衡资金
            if total_coin_value - current_coin_value > min_usdt:  # 少了买一点
                balance_amount = total_coin_value - current_coin_value
                balance_order_info = exchange.create_market_buy_order(symbol, balance_amount)
                logger.info('[balance value]buy target coin=%s cost=%s current_value=%s' % (target_coin, balance_amount, current_value))
            elif current_coin_value - total_coin_value > min_usdt:  # 多了卖一点
                balance_amount = (current_coin_value - total_coin_value) / std_price
                balance_order_info = exchange.create_market_sell_order(symbol, balance_amount)
                logger.info('[balance value]sell target coin=%s amount=%s current_value=%s' % (target_coin, balance_amount, current_value))
            if balance_order_info is not None:
                # 循环等待完全成交
                not_finish = True
                while not_finish:
                    # 如果没有完成，休眠
                    exchange.sleep(sleep_time * 2)
                    orders_info = exchange.fetch_orders(symbol)
                    for one_order in orders_info:
                        if balance_order_info['id'] == one_order['id'] and 'closed' == one_order['status']:
                            if extra_fee_mode:
                                exchange.add_fee_usdt(one_order['cost'])
                            not_finish = False
                continue

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
                'win_rate': (win_num / (lose_num + win_num) - 0.5),
            }
            _controller.data_to_csv(log_startone_header, [log_startone], 'startone')
            logline = []
            for key in log_startone:
                logline.append('%s=%s' % (key, log_startone[key]))
            logger.info("[start one]%s" % "\t".join(logline))

            # 开一单，卖单
            pos_price = std_price * (1 + diff_rate)
            pos_value_diff = balance_info[target_coin]['total'] * pos_price - default_coin_value
            sell_order_info = None

            # 开一单，买单
            negative_price = std_price * (1 - diff_rate)
            negative_value_diff = default_coin_value - balance_info[target_coin]['total'] * negative_price
            buy_order_info = None
            print(111, pos_value_diff, negative_value_diff)
            if pos_value_diff > min_usdt:       # 卖掉多的币
                amount = (balance_info[target_coin]['total'] * pos_price - default_coin_value) / pos_price
                sell_order_info = exchange.create_limit_sell_order(symbol, amount, pos_price)
                logger.debug('[%s] [create sell]amount=%s, price=%s' %
                             (exchange.get_str_time(), sell_order_info['amount'], sell_order_info['price']))
            if negative_value_diff > min_usdt:  # 买
                amount = (default_coin_value - balance_info[target_coin]['total'] * negative_price) / negative_price
                buy_order_info = exchange.create_limit_buy_order(symbol, amount, negative_price)
                logger.debug('[%s] [create buy]amount=%s, price=%s' %
                             (exchange.get_str_time(), buy_order_info['amount'], buy_order_info['price']))

            # 循环等待完全成交
            not_finish = True
            while not_finish:
                # 如果没有完成，休眠 0.01 秒
                exchange.sleep(sleep_time * 2)

                orders_info = exchange.fetch_orders(symbol)
                for one_order in orders_info:
                    if buy_order_info['id'] == one_order['id'] and 'closed' == one_order['status']:
                        not_finish = False
                        std_price = one_order['price']
                        lose_num += 1

                        if extra_fee_mode:
                            exchange.add_fee_usdt(one_order['cost'])

                        # 把剩余的撤单
                        exchange.cancel_order(sell_order_info['id'], symbol)

                        logger.debug('[%s] [closed buy]amount=%s, price=%s' %
                                      (exchange.get_str_time(), one_order['amount'], one_order['price']))

                        # 循环等待回调
                        while True:
                            ticker_info = exchange.fetch_ticker(symbol)
                            current_price = ticker_info['last']
                            min_price = min(min_price, current_price)
                            logger.debug('[%s] [waiting finish]min_price=%s, current_price=%s' %
                                          (exchange.get_str_time(), min_price, current_price))
                            if (current_price - min_price) > (std_price * diff_rate):  # 代表回调了一个diff价格
                                break
                            exchange.sleep(sleep_time * 4)  # 轮询
                    if sell_order_info['id'] == one_order['id'] and 'closed' == one_order['status']:
                        not_finish = False
                        std_price = one_order['price']
                        win_num += 1

                        # 把剩余的撤单
                        exchange.cancel_order(buy_order_info['id'], symbol)

                        logger.debug('[%s] [closed sell]amount=%s, price=%s' %
                                      (exchange.get_str_time(), one_order['amount'], one_order['price']))

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
