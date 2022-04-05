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
                    'redirect_uri': request.httprequest.url_root + 'workwx/oauth_signin',
                    'state': '',
                }
                provider['auth_link'] = "%s?%s" % (provider['auth_endpoint'], werkzeug.urls.url_encode(params))
        return providers

    @http.route('/workwx/oauth_signin', type='http', auth='none')
    def oauth_signin(self, **kw):
        code = kw.get('code')
        state = kw.get('state')
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
        try:
            resp = login_and_redirect(request.env.cr.dbname, oauth_user.login, code)
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
