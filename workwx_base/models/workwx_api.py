import json
import logging
import werkzeug
import requests
from cacheout import Cache

from odoo import tools

logger = logging.getLogger(__name__)
token_cache = Cache(ttl=3600)

# 接口详情及更多接口请查看官方文档: https://developer.work.weixin.qq.com/document/path/90664
WORKWX_API_TYPE = {
    'GET_ACCESS_TOKEN': ['/cgi-bin/gettoken', 'GET'],
    'GET_JSAPI_TICKET': ['/cgi-bin/get_jsapi_ticket?access_token=ACCESS_TOKEN', 'GET'],
    'GET_USER_INFO': ['/cgi-bin/user/getuserinfo?access_token=ACCESS_TOKEN', 'GET'],
    'USER_GET': ['/cgi-bin/user/get?access_token=ACCESS_TOKEN', 'GET'],
    'DEPARTMENT_LIST': ['/cgi-bin/department/list?access_token=ACCESS_TOKEN', 'GET'],
    'USER_LIST': ['/cgi-bin/user/list?access_token=ACCESS_TOKEN', 'GET'],
    'USER_CREATE': ['/cgi-bin/user/create?access_token=ADDRESS_TOKEN', 'POST'],
}


class WorkWXAPI:

    @classmethod
    def set_workwx_token(cls, token_key, token):
        token_cache.set(token_key, token)

    def get_workwx_token(self, token_key):
        if not token_cache.get(token_key):
            self.refresh_workwx_token(token_key)
        return token_cache.get(token_key)

    def refresh_workwx_token(self, token_key):
        token = self._get_token_with_request(token_key)
        if token:
            token_cache.set(token_key, token)
            return token

    def _get_token_with_request(self, token_key):
        # 请求企业微信，获取token
        if token_key == 'access_token':
            params = {
                'corpid': tools.config.get('workwx_corp_id'),
                'corpsecret': tools.config.get('workwx_corp_secret'),
            }
            result, info = self._http_cal_with_result('GET_ACCESS_TOKEN', params)
            if not result:
                return False
            return info.get('access_token')
        elif token_key == 'address_token':
            params = {
                'corpid': tools.config.get('workwx_corp_id'),
                'corpsecret': tools.config.get('workwx_address_secret'),
            }
            result, info = self._http_cal_with_result('GET_ACCESS_TOKEN', params)
            if not result:
                return False
            return info.get('access_token')
        elif token_key == 'jsapi_ticket':
            result, info = self._http_cal_with_result('GET_JSAPI_TICKET')
            if not result:
                return False
            return info.get('ticket')
        else:
            raise Exception(f'未知的token类型:{token_key}')

    def _http_cal_with_result(self, url_type, params={}):
        # 记录常规企业微信接口请求
        if url_type not in ['GET_ACCESS_TOKEN']:
            logger.info(f'[workwx_request]url_type:{url_type}, args: {params}')
        try:
            info = self.http_call(url_type, params)
            return True, info
        except Exception as e:
            logger.exception(f"url_type:{url_type}, args: {params}, error_info:{e}")
            return False, f'{e}'

    def http_call(self, url_key, params):
        short_url, method = WORKWX_API_TYPE[url_key]
        url = self._make_url(short_url)
        if params.get('debug') and params.pop('debug'):
            url += '&debug=1'
        real_url = self._append_token(url)
        for retry_cnt in range(3):
            if 'POST' == method:
                response = requests.post(real_url, data=json.dumps(params))
                response_str = response.content.decode('unicode-escape').encode("utf-8")
                response = json.loads(response_str)
            elif 'GET' == method:
                real_url += (('&' if '?' in real_url else '?') + werkzeug.urls.url_encode(params))
                response = requests.get(real_url)
                response = response.json()
            else:
                raise Exception('未知的请求方法')
            # 检查token是否过期
            if self._token_expired(response.get('errcode')):
                self.refresh_token_by_url(short_url)
                continue
            else:
                break
        return self._check_response(response)

    @staticmethod
    def _make_url(short_url):
        base = "https://qyapi.weixin.qq.com"
        if short_url[0] == '/':
            return base + short_url
        else:
            return base + '/' + short_url

    @staticmethod
    def _check_response(response):
        err_code = response.get('errcode')
        err_msg = response.get('errmsg')

        if err_code is 0:
            return response
        else:
            raise Exception(err_code, err_msg)

    @staticmethod
    def _token_expired(err_code):
        if err_code in [40014, 42001, 42007, 42009]:
            return True
        else:
            return False

    def _append_token(self, url):
        if 'ACCESS_TOKEN' in url:
            return url.replace('ACCESS_TOKEN', self.get_workwx_token('access_token'))
        if 'ADDRESS_TOKEN' in url:
            return url.replace('ADDRESS_TOKEN', self.get_workwx_token('address_token'))
        else:
            return url

    def refresh_token_by_url(self, url):
        if 'ACCESS_TOKEN' in url:
            self.refresh_workwx_token('access_token')

    def get_user_info(self, param):
        """获取员工id"""
        return self._http_cal_with_result('GET_USER_INFO', param)

    def user_get(self, param):
        """获取员工详细信息"""
        return self._http_cal_with_result('USER_GET', param)

    def department_list(self, param={}):
        """获取部门列表"""
        return self._http_cal_with_result('DEPARTMENT_LIST', param)

    def user_list(self, param):
        """获取员工列表"""
        return self._http_cal_with_result('USER_LIST', param)

    def user_create(self, param):
        """创建成员"""
        return self._http_cal_with_result('USER_CREATE', param)
