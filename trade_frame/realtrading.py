"""
实盘入口
@Author : bboxhe@gmail.com

"""

import controller


class RealTrading:
    def run(self):
        # 运行
        c = controller.Controller('realtrading.log')

        strategy_name = 'spot_neutral_1.SpotNeutral1'
        exchange_name = 'Exchange'

        c.set_exchange(exchange_name)
        c.run(strategy_name)


if __name__ == "__main__":
    trading = RealTrading()
    trading.run()
