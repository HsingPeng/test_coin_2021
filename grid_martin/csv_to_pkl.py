"""
csv 文件转 pkl，读取速度快
"""
import pandas
import sys

if len(sys.argv) < 2:
    print('输入CSV文件名称，无后缀。文件后缀必须为.csv')
    exit(1)

file_name = sys.argv[1]

source_df = pandas.read_csv(
    # filepath_or_buffer='ETH-USDT2_2000.csv',
    filepath_or_buffer=file_name + '.csv',
    encoding='gbk',
    parse_dates=['candle_begin_time'],
    index_col=['candle_begin_time'],
)

# pkl格式
source_df.to_pickle(file_name + '.pkl')  # 格式另存

# df = pd.read_pickle('xxx.pkl')  # 读取
