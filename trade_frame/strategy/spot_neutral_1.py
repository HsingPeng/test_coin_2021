"""
中性做市策略，一种网格
@Author : bboxhe@gmail.com

假设 diff=0.09%
1 -> 1.009 平掉 0.0009
1 -> 0.99 开仓 0.0009
基于此思路

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

        diff_rate, target_coin, base_coin, per_usdt = params.split('-')

        # 初始化
        # diff_rate = "0dot0009"
        # base_coin = 'USDT'
        # target_coin = 'ETH'
        # per_usdt = 11  # 由于当前比较特殊，资金不够。所以每次交易都用11usdt。之后改成比例

        diff_rate = float(diff_rate)
        per_usdt = float(per_usdt)
        symbol = target_coin + '/' + base_coin

        sleep_time = 0.1        # 睡眠时间
        win_num = 0
        lose_num = 0
        init_price = None
        init_value = None   # 初始价值
        max_value = None    # 最高价值，用于计算回撤
        min_value = None    # 最低价值，用于计算回撤
        if 'extra' == exchange.get_fee_mode():
            extra_fee_mode = True
        else:
            extra_fee_mode = False

        log_startone_header = ['realtime', 'std_price', 'target_coin', 'base_coin', 'total_value', 'fee_usdt',
                               'init_value', 'current_value', 'profit_rate', 'max_drawdown', 'win_num', 'lose_num']
        _controller.header_to_csv(log_startone_header, 'startone')

        # 开始循环
        while True:
            # 每轮都重新获取当前价格
            ticker_info = exchange.fetch_ticker(symbol)
            std_price = ticker_info['last']     # 基准价格，每轮重置
            min_price = std_price            # 判断回调使用，每轮重置

            balance_info = exchange.fetch_balance()
            if init_value is None:
                init_price = std_price
                init_value = balance_info[target_coin]['total'] * init_price + balance_info[base_coin]['total']

            current_value = balance_info[target_coin]['total'] * init_price + balance_info[base_coin]['total'] \
                - exchange.get_fee_usdt()
            if min_value is None:
                min_value = current_value
            else:
                min_value = min(min_value, current_value)
            if max_value is None:
                max_value = current_value
            else:
                max_value = max(max_value, current_value)

            # 平衡资金
            if current_value < per_usdt * 2:
                raise Exception('balance is not enough, something wrong happened')

            balance_order_info = None
            if balance_info[base_coin]['total'] > per_usdt * 400:  # base coin 多于400次，立刻买入，只留200次，因为要尽量持有
                balance_amount = balance_info[base_coin]['total'] - per_usdt * 200
                balance_order_info = exchange.create_market_buy_order(symbol, balance_amount)
                logger.info('[balance value]buy target coin=%s cost=%s' % (target_coin, balance_amount))
            elif balance_info[base_coin]['total'] < per_usdt * 2:      # base coin 不足，卖一些 target coin，得到50次
                balance_amount = per_usdt / std_price * 100
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

                continue    # 重开一轮

            log_startone = {
                'realtime': exchange.get_str_time(),
                'std_price': std_price,
                'target_coin': balance_info[target_coin]['total'],
                'base_coin': balance_info[base_coin]['total'],
                'total_value': (balance_info[base_coin]['total']
                                + std_price * balance_info[target_coin]['total'] - exchange.get_fee_usdt()),
                'fee_usdt': exchange.get_fee_usdt(),
                'init_value': init_value,
                'current_value': current_value,
                'profit_rate': ((current_value - init_value) / init_value),
                'max_drawdown': ((max_value - min_value) / max_value),
                'win_num': win_num,
                'lose_num': lose_num,
            }
            _controller.data_to_csv(log_startone_header, [log_startone], 'startone')
            logline = []
            for key in log_startone:
                logline.append('%s=%s' % (key, log_startone[key]))
            logger.info("[start one]%s" % "\t".join(logline))

            # 开一单，卖单
            price = std_price * (1 + diff_rate)
            amount = per_usdt / price
            sell_order_info = exchange.create_limit_sell_order(symbol, amount, price)
            logger.debug('[%s] [create sell]amount=%s, price=%s' %
                          (exchange.get_str_time(), sell_order_info['amount'], sell_order_info['price']))

            # 开一单，买单
            price = std_price * (1 - diff_rate)
            amount = per_usdt / price
            buy_order_info = exchange.create_limit_buy_order(symbol, amount, price)
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

            current_value = balance_info[target_coin]['total'] * init_price + balance_info[base_coin]['total'] \
                - exchange.get_fee_usdt()
            min_value = min(min_value, current_value)
            max_value = max(max_value, current_value)
            logger.info("[finish one]%s" % "\t".join(
                [
                    'realtime=%s' % exchange.get_str_time(),
                    'std_price=%f' % std_price,
                    'target_coin=%f' % balance_info[target_coin]['total'],
                    'base_coin=%f' % balance_info[base_coin]['total'],
                    'total_value=%f' % (balance_info[base_coin]['total']
                                        + std_price * balance_info[target_coin]['total'] - exchange.get_fee_usdt()),
                    'fee_usdt=%f' % exchange.get_fee_usdt(),
                    'init_value=%f' % init_value,
                    'current_value=%f' % current_value,
                    'profit_rate=%f' % ((current_value - init_value) / init_value),
                    'max_drawdown=%f' % ((max_value - min_value) / max_value),
                ]
            ))
