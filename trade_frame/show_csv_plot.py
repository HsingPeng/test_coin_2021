"""
csv数据可视化
"""
import pandas
import sys
import pyecharts


def line(data, file_name):
    lineFig = pyecharts.charts.Line()
    lineFig.set_global_opts(
        title_opts=pyecharts.options.TitleOpts(
            title=file_name,
            title_textstyle_opts=pyecharts.options.TextStyleOpts(
                font_size=10
            )
        ),
        legend_opts=pyecharts.options.LegendOpts(pos_top=10),
        datazoom_opts=pyecharts.options.DataZoomOpts(type_="slider")
    )
    if isinstance(data, pandas.Series):
        lineFig.add_xaxis(data.index.tolist())
        lineFig.add_yaxis(data.name, data.values.tolist())
    elif isinstance(data, pandas.DataFrame):
        useCols = data.columns
        manyLineConfig = {}
        for i in useCols:
            lineFig.add_xaxis(data.index.tolist())\
                .add_yaxis(i, data[i].tolist(), **manyLineConfig.get(i, {}))
    lineFig.set_series_opts(label_opts=pyecharts.options.LabelOpts(is_show=False))
    lineFig.render(file_name + '.html')


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

line(df, file_name)
