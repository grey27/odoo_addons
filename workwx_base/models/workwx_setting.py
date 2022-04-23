from odoo import fields, models, api


class WorkwxSetting(models.Model):
    _name = 'workwx.setting'
    _description = '企业微信配置'

    @api.model
    def get_values(self):
        res = super(WorkwxSetting, self).get_values()
        workwx_setting = self.env.ref('workwx_base.workwx_setting', False)
        workwx_setting and res.update({

        })
        return res

    def set_values(self):
        super(WorkwxSetting, self).set_values()
        workwx_setting = self.env.ref('workwx_base.workwx_setting', False)
        workwx_setting and workwx_setting.write({

        })


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    use_https = fields.Boolean(string='系统部署使用HTTPS协议', config_parameter='workwx_base.use_https',
                               help='''使用nginx部署https协议有可能使用80转发443端口,
                               那么系统获取的接口是http的,但实际上是https,使用js-sdk时加密算法会出错,需要修正协议''')
