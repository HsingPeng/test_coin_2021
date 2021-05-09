"""
csv数据可视化
"""
import pandas
from eplot import eplot
import matplotlib.pyplot as plt
import sys

if 2 > len(sys.argv):
    print('usage:python3 show_csv_plot.py filename index_column [show_column_1,show_column_2,show_column_3]')
    exit(1)

file_name = sys.argv[1]
index_column = sys.argv[2]
if len(sys.argv) >= 4:
    show_column_list = sys.argv[3].split(',')
else:
    show_column_list = None

df = pandas.read_csv(
    filepath_or_buffer=file_name,
    encoding='utf8',
    sep="\t",
    index_col=[index_column],
)

if show_column_list is not None:
    df = df[show_column_list]

"""
df.plot()
plt.show()
exit()
"""

eplot.Config = {'return_type': 'file'}
line = df.eplot.line(title=file_name)
line.render(file_name + '.html')
