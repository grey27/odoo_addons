from odoo import fields, models, api


class WorkwxSetting(models.Model):
    _name = 'workwx.setting'
    _description = '企业微信配置'

    default_workwx_login = fields.Boolean('默认使用企业微信扫码登录')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    workwx_base_default_workwx_login = fields.Boolean('默认使用企业微信扫码登录')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        workwx_setting = self.env.ref('workwx_base.workwx_setting', False)
        workwx_setting and res.update({
            'workwx_base_default_workwx_login': workwx_setting.default_workwx_login,
        })
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        workwx_setting = self.env.ref('workwx_base.workwx_setting', False)
        workwx_setting and workwx_setting.write({
            'default_workwx_login': self.workwx_base_default_workwx_login,
        })

    def action_sync_workwx_department(self):
        return self.env['hr.department'].sync_workwx_department()

    def action_sync_workwx_employee(self):
        return {
            'type': 'ir.actions.act_window',
            'name': '同步企业微信员工',
            'res_model': 'workwx.sync.employee.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    def action_invite_workwx_employee(self):
        return {
            'type': 'ir.actions.act_window',
            'name': '邀请企业微信员工',
            'res_model': 'create.workwx.user.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    def action_workwx_menu_manager(self):
        return {
            'type': 'ir.actions.act_window',
            'name': '应用菜单栏设置',
            'res_model': 'workwx.menu.item',
            'view_type': 'list',
            'view_mode': 'list',
            'domain': [],
            'target': 'new',
        }

    def action_workwx_message(self):
        return {
            'type': 'ir.actions.act_window',
            'name': '企业微信消息推送',
            'res_model': 'workwx.message',
            'view_type': 'list',
            'view_mode': 'list',
            'domain': [],
            'target': 'self',
        }

    def action_workwx_callback_log(self):
        return {
            'type': 'ir.actions.act_window',
            'name': '企业微信回调日志',
            'res_model': 'workwx.callback.log',
            'view_type': 'list',
            'view_mode': 'list',
            'domain': [],
            'target': 'self',
        }
