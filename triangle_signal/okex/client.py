import aiohttp
import json
from . import consts as c, utils, exceptions
import os


class Client(object):

    def __init__(self, api_key, api_secret_key, passphrase, use_server_time=False, test=False, first=False):

        self.API_KEY = api_key
        self.API_SECRET_KEY = api_secret_key
        self.PASSPHRASE = passphrase
        self.use_server_time = use_server_time
        self.first = first
        self.test = test

    async def _request(self, method, request_path, params, cursor=False):
        if method == c.GET:
            request_path = request_path + utils.parse_params_to_str(params)
        # url
        url = c.API_URL + request_path

        # 获取本地时间
        timestamp = utils.get_timestamp()

        # sign & header
        if self.use_server_time:
            # 获取服务器时间
            timestamp = self._get_timestamp()

        body = json.dumps(params) if method == c.POST else ""
        sign = utils.sign(utils.pre_hash(timestamp, method, request_path, str(body)), self.API_SECRET_KEY)\
            .decode('ascii')
        header = utils.get_header(self.API_KEY, sign, timestamp, self.PASSPHRASE)

        if self.test:
            header['x-simulated-trading'] = '1'
        if self.first:
            print("url:", url)
            self.first = False

        print('client', "url:", url)
        # print("headers:", header)
        print("body:", body)

        # send request
        response = None
        proxy = os.getenv('HTTP_PROXY', None)
        session = aiohttp.ClientSession()
        if method == c.GET:
            response = await session.get(url, headers=header, proxy=proxy)
        elif method == c.POST:
            response = await session.post(url, data=body, headers=header, proxy=proxy)
        elif method == c.DELETE:
            response = await session.delete(url, headers=header, proxy=proxy)

        await response.json()
        await session.close()

        # exception handle
        if not str(response.status).startswith('2'):
            raise exceptions.OkexAPIException(response)
        try:
            res_header = response.headers
            if cursor:
                r = dict()
                try:
                    r['before'] = res_header['OK-BEFORE']
                    r['after'] = res_header['OK-AFTER']
                except:
                    pass
                return await response.json(), r
            else:
                return await response.json()

        except ValueError:
            raise exceptions.OkexRequestException('Invalid Response: %s' % await response.text())

    def _request_without_params(self, method, request_path):
        return self._request(method, request_path, {})

    def _request_with_params(self, method, request_path, params, cursor=False):
        return self._request(method, request_path, params, cursor)

    async def _get_timestamp(self):
        url = c.API_URL + c.SERVER_TIMESTAMP_URL
        session = aiohttp.ClientSession()
        proxy = os.getenv('HTTP_PROXY', None)

        response = await session.get(url, proxy=proxy)
        await response.read()
        await session.close()

        if response.status == 200:
            return (await response.json())['iso']
        else:
            return ""
