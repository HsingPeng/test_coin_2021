"""
并行回测
@Author : bboxhe@gmail.com
"""


def get_para_list():
    # 自己生成参数列表 params, strategy_name, strategy_params
    params = 'ETH-USDT-1620132107000-1620142907000'
    strategy_name = 'spot_neutral_1.SpotNeutral1'

    para_list = []
    for i in range(1, 20):
        para_list.append([
            params,
            strategy_name,
            '%f-ETH-USDT-11' % (i / 10000)
        ])

    return para_list


if __name__ == "__main__":
    print(get_para_list())
