"""
实盘入口
@Author : bboxhe@gmail.com

"""

import controller


class RealTrading:
    def run(self):
        # 运行
        c = controller.Controller('realtrading')

        strategy_name = 'spot_neutral_1.SpotNeutral1'
        exchange_name = 'exchange.Exchange'
        strategy_params = '0.0007-EOS-USDT-11'

        c.set_exchange(exchange_name)
        c.run(strategy_name, strategy_params)


if __name__ == "__main__":
    trading = RealTrading()
    trading.run()
