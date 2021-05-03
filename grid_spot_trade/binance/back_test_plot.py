"""
回测图标 价格曲线
"""
import pandas
import matplotlib.pyplot as plt
import sys

file_name = sys.argv[1]

df = pandas.read_csv(
    filepath_or_buffer=file_name,
    encoding='gbk',
    sep="\t",
    index_col=['time'],
    parse_dates=['time'],
)

df = df[['rate']]

df.plot()
plt.show()
exit()
