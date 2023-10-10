from odoo import models, api
from odoo.tools.profiler import QwebTracker


class IrQWeb(models.AbstractModel):
    _inherit = 'ir.qweb'

    @QwebTracker.wrap_render
    @api.model
    def _render(self, template, values=None, **options):
        if template == 'web.login':
            values.update({'icp_display_name': self.env['ir.config_parameter'].sudo().get_param('cn_icp.display_name')})
        return super(IrQWeb, self)._render(template, values, **options)
