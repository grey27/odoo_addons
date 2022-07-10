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
            if '企业微信' in provider.get('name'):
                params = {
                    'appid': tools.config.get('workwx_corp_id'),
                    'agentid': tools.config.get('workwx_agent_id'),
                    'redirect_uri': request.httprequest.url_root + 'workwx/signin',
                    'state': '',
                }
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
        # if userid:
        #     result, user_info = WorkWXAPI().user_get({'userid': userid})
        oauth_user = request.env['res.users'].sudo().search(
            [("oauth_uid", "=", userid), ('oauth_provider_id', '=', provider.id)])
        if not oauth_user:
            return self._workwx_login_error('workwx_3')
        oauth_user.write({'oauth_access_token': code})
        request.env.cr.commit()
        url = '/web' if not kw.get('redirect_uri') else kw.get('redirect_uri')
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
            if '企业微信' in provider.get('name'):
                url = provider.get('auth_link')
        return werkzeug.utils.redirect(url, 303)

    @http.route('/workwx/web', type='http', auth="none")
    def workwx_web(self, redirect_uri=None, inner=False, **kw):
        """
        企业微信app内自动登录跳转链接接口
        因为浏览器会默认截断"#"之后的参数,所以odoo原生页面链接中#需要替换为?
        例如要打开一个odoo常规页面:/web#action=70&model=res.users&view_type=list&cids=&menu_id=4
        改造为: /workwx/web?redirect_uri=/web?action=70&model=res.users&view_type=list&cids=&menu_id=4
        如果需要打开一个自定义页面: /workwx/web?redirect_uri=/customize_route
        :param redirect_uri: 跳转地址
        :param inner: 是否在企业微信内打开,对移动端无效,移动端只能内部打开 因为企业微信浏览器内核对odoo页面支持不佳,所以默认为启用外部浏览器打开
        :param kw: 携带参数
        :return: response
        """
        if not redirect_uri or 'wxwork' not in request.httprequest.headers.get('User-Agent'):
            return werkzeug.utils.redirect('/web', 303)
        if redirect_uri.startswith('/web?'):
            redirect_uri = redirect_uri.replace('/web?', '/web#')
        if kw:
            redirect_uri += ('&' + werkzeug.urls.url_encode(kw))
        if request.session.uid:
            return werkzeug.utils.redirect(f'/web?redirect={redirect_uri}', 303)
        url = request.httprequest.url_root + '/workwx/signin?' + werkzeug.urls.url_encode({'redirect_uri': redirect_uri})
        REDIRECT_URI = werkzeug.urls.url_quote(url)
        CORPID = tools.config.get('workwx_corp_id')
        authorize_url = f'https://open.weixin.qq.com/connect/oauth2/authorize?appid={CORPID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=snsapi_base&state=odoo#wechat_redirect'
        if inner or ('Windows' not in request.httprequest.headers.get('User-Agent') and 'Macintosh' not in request.httprequest.headers.get('User-Agent')):
            return http.local_redirect(authorize_url)
        values = self.get_workwx_jssdk_config()
        values.update({'redirect_uri': authorize_url})
        response = request.render('workwx_base.workwx_open_default_browser', values)
        return response

    @staticmethod
    def get_workwx_jssdk_config():
        ticket = WorkWXAPI().get_workwx_token('jsapi_ticket')
        noncestr = ''.join([random.choice('0123456789qwertyuiopasdfghjklzxcvbnm') for _ in range(11)])
        timestamp = int(time.time())
        url = request.httprequest.url.split('#')[0]
        if url.startswith('http://') and request.env['ir.config_parameter'].sudo().get_param('workwx_base.use_https'):
            url = url.replace('http://', 'https://')
        base_url, path = url.split('?')
        if path:
            url = base_url + '?' + werkzeug.urls.url_unquote_plus(path)
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
