"""
测试队列
"""
import asyncio


async def read_queue(ws_queue):
    while True:
        print(111)
        response = await ws_queue.get()
        print(response[10])


async def write_queue(ws_queue):
    while True:
        print(222)
        await ws_queue.put({'a': 1})


loop = asyncio.get_event_loop()
ws_queue = asyncio.Queue(100, loop=loop)     # 用于接收订阅数据

tasks = [asyncio.ensure_future(read_queue(ws_queue), loop=loop), asyncio.ensure_future(write_queue(ws_queue), loop=loop)]
finished, pending = loop.run_until_complete(asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION))
for task in finished:
    if task.exception():
        print("{} got an exception {}, retrying" . format(task, task.exception()))

