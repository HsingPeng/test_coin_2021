"""
回测图标 价格曲线
"""
import pandas
import sys
import matplotlib.pyplot as plt


file_name = 'ret/value/value_param_3_0.04'
file_name = sys.argv[1]

df = pandas.read_csv(
    filepath_or_buffer=file_name,
    encoding='gbk',
    sep=",",
    parse_dates=['time'],
    index_col=['time'],
)

df['balance2'] = df['balance'] * 1.5
df = df[[
    # 'balance2',
    'price',
]]

df.plot(title=file_name)
plt.show()
exit()


# 以下代码不知道为什么有问题

plt.figure(figsize=(10, 10))
plt.title('回测' + file_name)
plt.rcParams["font.family"] = 'Arial Unicode MS'

ax1 = plt.subplot(211)
ax1.set_title('价格')
ax1.plot(df['time'], df['price'], 'g')
ax2 = plt.subplot(212)
ax2.set_title('余额')
ax2.plot(df['index'], df['balance'], 'b')

plt.show()
