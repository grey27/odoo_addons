import logging
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
            if provider.get('name') == '企业微信':
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
        response = super(WorkWxOAuthLogin, self).web_login(*args, **kw)
        error = request.params.get('oauth_error')
        if error == 'workwx_1':
            response.qcontext['error'] = '登录失败：获取员工信息失败'
        elif error == 'workwx_2':
            response.qcontext['error'] = '登录失败：请使用企业微信APP进行扫码登录'
        elif error == 'workwx_3':
            response.qcontext['error'] = '登录失败：系统中无法找到对应用户，请联系管理员开通企业微信登录权限'
        return response

    """
    企业微信app内自动登录跳转链接接口
    因为浏览器会默认截断"#"之后的参数,所以odoo原生页面链接中#需要替换为?
    例如要打开一个odoo常规页面:/web#action=70&model=res.users&view_type=list&cids=&menu_id=4
    改造为: /workwx/web?redirect_uri=/web?action=70&model=res.users&view_type=list&cids=&menu_id=4
    如果需要打开一个自定义页面: /workwx/web?redirect_uri=/customize_route
    """
    @http.route('/workwx/web', type='http', auth="none")
    def workwx_web(self, redirect_uri=None, **kw):
        if not redirect_uri or request.session.uid or 'wxwork' not in request.httprequest.headers.get('User-Agent'):
            return werkzeug.utils.redirect('/web', 303)
        if redirect_uri.startswith('/web?'):
            redirect_uri = redirect_uri.replace('/web?', '/web#')
            redirect_uri += ('&' + werkzeug.urls.url_encode(kw))
        url = request.httprequest.url_root + '/workwx/signin?' + werkzeug.urls.url_encode({'redirect_uri': redirect_uri})
        REDIRECT_URI = werkzeug.urls.url_quote(url)
        CORPID = tools.config.get('workwx_corp_id')
        authorize_url = f'https://open.weixin.qq.com/connect/oauth2/authorize?appid={CORPID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=snsapi_base&state=odoo#wechat_redirect'
        return http.local_redirect(authorize_url)
