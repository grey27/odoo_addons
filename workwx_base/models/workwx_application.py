import logging
from odoo import fields, models, api, tools
from odoo.exceptions import UserError
from odoo.addons.workwx_base.models.workwx_api import WorkWXAPI

logger = logging.getLogger(__name__)


class WorkwxMenuItem(models.Model):
    _name = 'workwx.menu.item'
    _description = '企业微信菜单栏'
    _rec_name = 'name'
    _order = 'parent_button_id'

    name = fields.Char('名称')
    type = fields.Selection([('click', '点击'), ('view', '跳转URL'), ('scancode_waitmsg', '扫码')],
                            '类型', default='click')
    key = fields.Char('KEY')
    url = fields.Char('URL')
    parent_button_id = fields.Many2one('workwx.menu.item', '父按钮')
    sub_button_ids = fields.One2many('workwx.menu.item', 'parent_button_id', '子按钮')
    sequence = fields.Integer('排序')

    _sql_constraints = [('key_uniq', 'unique (key)', "key值不允许重复")]

    @api.onchange('sub_button_ids')
    def _onchange_sub_button_ids(self):
        if self._origin.id and self.sub_button_ids and self._origin.id in self.sub_button_ids.ids:
            raise UserError('不允许选择自身作为子按钮')

    def action_refresh_menu(self):
        """企业微信菜单"""
        result, info = WorkWXAPI().menu_delete()
        if not result:
            logger.exception(f'删除企业微信菜单栏失败：{info}')
            raise UserError('删除企业微信菜单栏失败,请联系开发人员')
        param = self._get_create_menu_param()
        result, info = WorkWXAPI().menu_create(param)
        if not result:
            logger.exception(f'创建企业微信菜单栏失败：{info}')
            raise UserError('创建企业微信菜单栏失败,请联系开发人员')
        return {
            'type': 'ir.actions.client',
            'tag': 'dialog',
            'params': {
                'title': '提示',
                '$content': f'<h4 style=" text-align:center; ">刷新菜单栏成功</h2>',
                'size': 'medium',
            }
        }

    def _get_create_menu_param(self):
        """ 组装创建菜单栏参数 """
        button_list = []
        for item in self.search([('parent_button_id', '=', False)], order='sequence'):
            button_list.append(item._get_button_dic())
        return {'button': button_list}

    def _get_button_dic(self):
        """组装按钮格式"""
        button = {
            'type': self.type,
            'name': self.name,
        }
        if self.sub_button_ids:
            sub_button = []
            for sub_item in self.sub_button_ids.sorted(key='sequence'):
                sub_button.append(sub_item._get_button_dic())
            button.pop('type')
            button['sub_button'] = sub_button
        elif self.type in ['click', 'scancode_waitmsg']:
            button['key'] = self.key
        elif self.type == 'view':
            button['url'] = self.url
        return button

    @api.model
    def callback_click(self, xml_dict):
        logger.info(f'{xml_dict.get("FromUserName")}点击了按钮{xml_dict.get("EventKey")}')

    @api.model
    def callback_scancode(self, xml_dict):
        logger.info(f'{xml_dict.get("FromUserName")}使用扫码按钮{xml_dict.get("EventKey")}上传了{xml_dict.get("ScanCodeInfo")}')


class WorkwxCallback(models.AbstractModel):
    _inherit = 'workwx.callback'

    @api.model
    def get_event_callback_func(self, xml_dict):
        if xml_dict.get('MsgType') == 'event' and xml_dict.get('Event') == 'click':
            return self.env['workwx.menu.item'].sudo().callback_click
        if xml_dict.get('MsgType') == 'event' and xml_dict.get('Event') == 'scancode_waitmsg':
            return self.env['workwx.menu.item'].sudo().callback_scancode
        return super(WorkwxCallback, self).get_event_callback_func(xml_dict)
