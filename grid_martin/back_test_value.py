"""
回测图标 价格曲线
"""
import pandas
import matplotlib.pyplot as plt


file_name = 'ret/finish/2_039_value'
file_name = 'ret/finish/5_023_value'
file_name = 'ret/finish/5_023_value1'
file_name = 'ret/finish/2_039_value1'
file_name = 'ret/finish/2_007_value1'
file_name = 'ret/finish/6_039_value1'
file_name = 'ret/finish/9_033_value1'
file_name = 'ret/finish/9_033_value'
file_name = 'ret/finish/10_011_value1'

df = pandas.read_csv(
    filepath_or_buffer=file_name,
    encoding='gbk',
    sep="\t",
    index_col=['index'],
)

df.plot()
plt.show()
exit()

# 以下代码不知道为什么有问题

plt.figure(figsize=(10, 10))
plt.title('回测' + file_name)
plt.rcParams["font.family"] = 'Arial Unicode MS'

ax1 = plt.subplot(211)
ax1.set_title('价格')
ax1.plot(df['index'], df['price'], 'g')
ax2 = plt.subplot(212)
ax2.set_title('余额')
ax2.plot(df['index'], df['value'], 'b')

plt.show()
