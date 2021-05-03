"""
跑一下这3天内，各个时间段的概率。按抗单 0.009 的数据算。如果在时间段内的概率是稳定，那么就说明确实有统计学趋势。
文件 x0.9
"""
import sys
import json

# 读取成交记录
input_file = sys.argv[1]
f = open(input_file, 'r')

while True:
    line_str = f.readline()
    if not line_str:
        break
    line = line_str.split("\t")
    info = json.loads(line[5])
    # 计算 sum
    sum = 0
    for num in info:
        sum += int(info[num])
    # 获取 pos
    pos = int(info["0"])
    # 计算 rate
    rate = pos / sum
    # 输出 time, sum, rate
    print("\t".join((
        line[0],
        str(sum),
        str(rate)
    )))
