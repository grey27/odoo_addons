import hashlib
import logging
import random
import time
import werkzeug

from odoo.addons.web.controllers.main import login_and_redirect
from odoo.addons.auth_oauth.controllers.main import OAuthLogin
from odoo.addons.workwx_base.models.workwx_api import WorkWXAPI
from odoo import http, tools
from odoo.exceptions import AccessDenied
from odoo.http import request

logger = logging.getLogger(__name__)


class WorkWxOAuthLogin(OAuthLogin):
    def list_providers(self):
        providers = super(WorkWxOAuthLogin, self).list_providers()
        for provider in providers:
            if provider.get('id') == request.env.ref('workwx_base.provider_workwx').sudo().id:
                params = {
                    'appid': tools.config.get('workwx_corp_id'),
                    'agentid': tools.config.get('workwx_agent_id'),
                    'redirect_uri': request.env['ir.config_parameter'].sudo().get_param(
                        'web.base.url') + '/workwx/signin',
                    'state': '',
                }
                if params['redirect_uri'].startswith('http://') and request.env['ir.config_parameter'].sudo().get_param(
                        'workwx_base.use_https'):
                    params['redirect_uri'] = params['redirect_uri'].replace('http://', 'https://')
                provider['auth_link'] = "%s?%s" % (provider['auth_endpoint'], werkzeug.urls.url_encode(params))
        return providers

    @http.route('/workwx/signin', type='http', auth='none')
    def oauth_signin(self, code=None, state=None, **kw):
        if not code:
            return self._workwx_login_error('workwx_1')
        provider = request.env.ref('workwx_base.provider_workwx').sudo()
        result, info = WorkWXAPI().get_user_info({'code': code})
        if not result:
            return self._workwx_login_error('workwx_2')
        userid = info.get('UserId')
        oauth_user = request.env['res.users'].sudo().search(
            [("oauth_uid", "=", userid), ('oauth_provider_id', '=', provider.id)])
        if not oauth_user:
            return self._workwx_login_error('workwx_3')
        if oauth_user.employee_id:
            result, user_info = WorkWXAPI().user_get({'userid': userid})
            result and oauth_user.employee_id.update_workwx_info(user_info)
        oauth_user.write({'oauth_access_token': code})
        request.env.cr.commit()
        url = request.httprequest.url_root + (
            'web' if not kw.get('redirect_uri') else kw.get('redirect_uri').lstrip('/'))
        try:
            resp = login_and_redirect(request.env.cr.dbname, oauth_user.login, code, redirect_url=url)
            logger.info(f'{oauth_user.login}通过企业微信扫码登录成功')
            return resp
        except AccessDenied:
            return self._workwx_login_error('workwx_3')

    @staticmethod
    def _workwx_login_error(err_code):
        url = f"/web/login?oauth_error={err_code}"
        redirect = werkzeug.utils.redirect(url, 303)
        redirect.autocorrect_location_header = False
        return redirect

    @http.route()
    def web_login(self, *args, **kw):
        workwx_setting = request.env.ref('workwx_base.workwx_setting').sudo()
        if request.httprequest.method == 'GET' and not request.session.uid and \
                workwx_setting.default_workwx_login and kw.get('login_mode') != 'password':
            return self.workwx_login(*args, **kw)
        response = super(WorkWxOAuthLogin, self).web_login(*args, **kw)
        error = request.params.get('oauth_error')
        if error == 'workwx_1':
            response.qcontext['error'] = '登录失败：获取员工信息失败'
        elif error == 'workwx_2':
            response.qcontext['error'] = '登录失败：请使用企业微信APP进行扫码登录'
        elif error == 'workwx_3':
            response.qcontext['error'] = '登录失败：系统中无法找到对应用户，请联系管理员开通企业微信登录权限'
        return response

    @http.route('/workwx/login', type='http', auth="none")
    def workwx_login(self, *args, **kw):
        kw['login_mode'] = 'password'
        url = '/web/login?%s' % werkzeug.urls.url_encode(kw)
        for provider in self.list_providers():
            if provider.get('id') == request.env.ref("workwx_base.provider_workwx").sudo().id:
                url = provider.get('auth_link')
        return werkzeug.utils.redirect(url, 303)

    @http.route('/workwx/web', type='http', auth="none")
    def workwx_web(self, redirect_uri=None, inner=False, **kw):
        """
        企业微信app内自动登录跳转链接接口
        :param redirect_uri: 跳转地址,需要使用url编码
        :param inner: 是否在企业微信内打开,对移动端无效,移动端只能内部打开
        因为企业微信浏览器内核对odoo页面支持不佳,所以默认为启用外部浏览器打开
        :param kw: 携带参数
        :return: response
        """
        redirect = '/web' if not redirect_uri else f'/web?redirect={redirect_uri}'
        # 这里再次进行编码是为了防止#后参数被企业回调时给忽略
        url = request.httprequest.url_root + f'/workwx/signin?redirect_uri={werkzeug.urls.url_quote_plus(redirect_uri or "/web")}'
        login_redirect_url = self.get_login_redirect_url(url)
        if 'wxwork' not in request.httprequest.headers.get('User-Agent'):
            return werkzeug.utils.redirect(redirect, 303)
        if not inner and self.is_pc(request.httprequest.headers.get('User-Agent')):
            values = self.get_workwx_jssdk_config()
            values.update({'redirect_uri': login_redirect_url})
            return request.render('workwx_base.workwx_open_default_browser', values)
        else:
            if not request.session.uid:
                redirect = login_redirect_url
            return werkzeug.utils.redirect(redirect, 303)

    @staticmethod
    def get_login_redirect_url(url):
        CORPID = tools.config.get('workwx_corp_id')
        return f'https://open.weixin.qq.com/connect/oauth2/authorize?appid={CORPID}&redirect_uri=' \
               f'{werkzeug.urls.url_quote_plus(url)}&response_type=code&scope=snsapi_base&state=odoo#wechat_redirect'

    @staticmethod
    def is_pc(user_agent):
        """通过user_agent判断访问设备是否为桌面端"""
        if not user_agent or not isinstance(user_agent, str):
            return False
        if 'Windows' in user_agent or 'Macintosh' in user_agent:
            return True
        return False

    @staticmethod
    def get_workwx_jssdk_config():
        ticket = WorkWXAPI().get_workwx_token('jsapi_ticket')
        noncestr = ''.join([random.choice('0123456789qwertyuiopasdfghjklzxcvbnm') for _ in range(11)])
        timestamp = int(time.time())
        url = request.httprequest.url.split('#')[0]
        if url.startswith('http://') and request.env['ir.config_parameter'].sudo().get_param('workwx_base.use_https'):
            url = url.replace('http://', 'https://')
        jsapi_ticket = f'jsapi_ticket={ticket}&noncestr={noncestr}&timestamp={timestamp}&url={url}'
        sha = hashlib.sha1(jsapi_ticket.encode('utf-8'))
        signature = sha.hexdigest()
        return {
            'app_id': tools.config.get('workwx_corp_id'),
            'timestamp': timestamp,
            'signature': signature,
            'noncestr': noncestr,
            'ticket': ticket,
            'request_url': url,
        }


class WorkWxController(http.Controller):

    @http.route('/workwx_callback/', type='http', auth='public', csrf=False)
    def workwx_callback(self, **kwargs):
        # get方法为企业微信校验回调地址是否正确
        if request.httprequest.method == 'GET':
            return request.env['workwx.callback'].check_workwx_callback(**kwargs)
        # post方法为接收真实回调数据
        elif request.httprequest.method == 'POST':
            xml_text = request.env['workwx.callback'].handle_workwx_callback(request.httprequest.get_data(), **kwargs)
            return http.Response(xml_text)
