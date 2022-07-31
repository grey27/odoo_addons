import base64
import logging

import requests

from odoo import fields, models, api
from odoo.addons.workwx_base.models.workwx_api import WorkWXAPI
from odoo.exceptions import UserError

logger = logging.getLogger(__name__)


class WorkwxHrDepartment(models.Model):
    _inherit = 'hr.department'

    workwx_id = fields.Char('企业微信部门id')
    workwx_leader_ids = fields.Many2many('hr.employee', string='企业微信部门领导')

    @api.model
    def sync_workwx_department(self, id=None):
        params = {'id': id} if id else {}
        result, info = WorkWXAPI().department_list(params)
        if not result:
            raise UserError(f"获取企业微信部门失败:{info}")
        add_count = 0
        all_department_id_list = []
        for department_info in info.get('department'):
            all_department_id_list.append(department_info.get('id'))
            department_id = self.search([('workwx_id', '=', department_info.get('id'))])
            if not department_id:
                add_count += 1
                department_id = self.create({'name': department_info.get('name')})
            department_id.workwx_id = department_info.get('id')
            department_id.name = department_info.get('name')
            if department_info.get('department_leader'):
                leader_ids = self.env['hr.employee'].search(
                    [('workwx_id', 'in', department_info.get('department_leader'))])
                leader_ids and department_id.write({'workwx_leader_ids': [(6, 0, leader_ids.ids)]})
                if len(leader_ids) == 1:
                    department_id.manager_id = leader_ids.id
            parent_department_id = self.search([('workwx_id', '=', department_info.get('parentid'))])
            parent_department_id and department_id.write({'parent_id': parent_department_id.id})
        del_department_ids = self.search([('workwx_id', 'not in', all_department_id_list)])
        del_department_ids.active = False
        msg = f'共同步企业微信部门{len(info.get("department"))}个,新增{add_count}个部门,删除{len(del_department_ids)}个部门'
        logger.info(msg)
        return {
            'type': 'ir.actions.client',
            'tag': 'dialog',
            'params': {
                'title': '同步完成',
                '$content': f'<h4 style=" text-align:center; ">{msg}</h2>',
                'size': 'medium',
            }
        }


class WorkwxHrEmployeeBase(models.AbstractModel):
    _inherit = 'hr.employee.base'

    workwx_id = fields.Char('企业微信部门id')

    def update_workwx_info(self, info):
        vals = {
            'workwx_id': info.get('userid'),
            'name': info.get('name'),
            'work_phone': info.get('mobile'),
            'department_id': self.env['hr.department'].search([('workwx_id', '=',
                                                                info.get('department')[0]
                                                                if isinstance(info.get('department'), list) else
                                                                info.get('department'))]).id,
            'job_title': info.get('position'),
            'gender': {'0': 'other', '1': 'male', '2': 'female'}.get(info.get('gender')),
            'work_email': info.get('email'),
            'image_1920': self._get_workwx_avatar_image(info.get('avatar')),
        }
        return self.write(vals)

    @staticmethod
    def _get_workwx_avatar_image(url):
        if not url:
            return False
        try:
            resp = requests.get(url)
            if resp.status_code == 200:
                return base64.b64encode(resp.content)
            raise Exception(resp)
        except Exception as e:
            logger.exception(f'请求企业微信头像失败,{e}')
        return False
    
    def write(self, vals):
        return super(WorkwxHrEmployeeBase, self).write(vals)
