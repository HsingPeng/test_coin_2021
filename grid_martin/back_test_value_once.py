"""
回测图标 价格曲线
"""
import pandas
import matplotlib.pyplot as plt

file_name = 'once/ret/1_001_value'
file_name = 'once/ret/1_003_value'
file_name = 'once/ret/3_002_value'
file_name = 'once/ret/2_002_value'

file_name = 'once/ret/0_003_value'
file_name = 'once/ret/0_004_value'
file_name = 'once/ret/1_0007_value'
file_name = 'once/ret/1_0005_value'
file_name = 'once/ret/1_002_value'
file_name = 'once/ret/2_001_value'

df = pandas.read_csv(
    filepath_or_buffer=file_name,
    encoding='gbk',
    sep="\t",
    index_col=['index'],
)

df.plot()
plt.show()
exit()
