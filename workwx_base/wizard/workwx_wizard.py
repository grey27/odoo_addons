import base64
import logging
import requests
from odoo import fields, models, api
from odoo.addons.workwx_base.models.workwx_api import WorkWXAPI
from odoo.exceptions import UserError

logger = logging.getLogger(__name__)


class CreateWorkwxUserWizard(models.TransientModel):
    _name = 'create.workwx.user.wizard'
    _description = '创建企业微信用户向导'

    @api.model
    def _get_department_list(self):
        result, info = WorkWXAPI().department_list()
        if not result:
            logger.exception(f"获取企业微信部门失败:{info}")
            return []
        department_map = [(item['id'], item['name']) for item in info.get('department')]
        return department_map

    @api.model
    def _get_join_qrcode(self):
        result, info = WorkWXAPI().get_join_qrcode()
        if not result:
            raise UserError(f"获取邀请二维码失败:{info}")
        qr_code = info.get("join_qrcode")
        try:
            response = requests.get(qr_code)
            return base64.b64encode(response.content)
        except Exception as e:
            logger.exception(f'下载邀请二维码失败:{e}')
        return False

    user_id = fields.Char('员工id', required=1,
                          help='对应管理端的帐号，企业内必须唯一。长度为1~64个字节。只能由数字、字母和“_-@.”四种字符组成，'
                               '且第一个字符必须是数字或字母。系统进行唯一性检查时会忽略大小写。')
    name = fields.Char('员工姓名', required=1)
    mobile = fields.Char('手机号码')
    email = fields.Char('邮箱')
    department = fields.Selection(_get_department_list, '部门', required=1)
    position = fields.Char('职务')
    gender = fields.Selection([('1', '男'), ('2', '女')], '性别')
    create_user = fields.Boolean('同步创建odoo账号', default=True)
    join_qrcode = fields.Image(default=_get_join_qrcode, string='邀请二维码')

    def action_invite(self):
        param = {
            'userid': self.user_id,
            'name': self.name,
            'department': [int(self.department)],
        }
        for field in ['mobile', 'email', 'position', 'gender']:
            self[field] and param.update({field: self[field]})
        result, info = WorkWXAPI().user_create(param)
        if not result:
            raise UserError(f"创建企业微信员工失败:{info}")
        msg = f'已成功邀请{self.name}'
        try:
            self.create_user and self._create_user()
        except Exception as e:
            logger.exception(e)
            msg += ',创建系统用户出现异常请手动创建'
        return {
            'type': 'ir.actions.client',
            'tag': 'dialog',
            'params': {
                'title': '邀请成功',
                '$content': f'<h5 style=" text-align:center; ">{msg}</h5>',
                'size': 'medium',
            }
        }

    def _create_employee_user(self):
        department_id = self.env['hr.department'].search([('workwx_id', '=', self.department)])
        employee_id = self.env['hr.employee'].search([('workwx_id', '=', self.user_id)])
        if not employee_id:
            employee_id = self.env['hr.employee'].create({
                'name': self.name,
                'workwx_id': self.user_id,
                'work_phone': self.mobile,
                'work_email': self.email,
                'department_id': department_id.id if department_id else False,
                'gender': {'1': 'male', '2': 'male'}.get(self.gender, False),
                'job_title': self.position,
            })
        count, info = self.env['workwx.sync.employee.wizard'].create_sys_user(employee_id)
        if not count:
            raise UserError(F'创建用户失败:{info}')


class SyncEmployeeWizard(models.TransientModel):
    _name = 'workwx.sync.employee.wizard'
    _description = '同步企业微信员工向导'

    department_ids = fields.Many2many('hr.department', string='需要同步的部门', domain=[['workwx_id', '!=', False]])
    fetch_child = fields.Boolean('同步获取子部门员工', default=True)
    del_nonexistent_employee = fields.Boolean('删除不存在的员工', help='删除企业微信架构中不存在的员工,如果员工存在odoo用户也会一并删除')
    create_user = fields.Boolean('创建odoo用户')

    def sync_workwx_employee(self, ):
        add_count = 0
        del_count = 0
        create_user_ids = self.env['hr.employee']
        for department_id in self.department_ids:
            # todo: fetch_child参数在最新的接口文档中已经去除,但目前还可用(2022.7.9),不确定是否参数后续会失效
            params = {'fetch_child': 1 if self.fetch_child else 0, 'department_id': department_id.workwx_id}
            result, info = WorkWXAPI().user_list(params)
            if not result:
                raise UserError(f"同步企业微信部门失败:{info}")
            for employee_info in info.get('userlist'):
                employee_id = self.env['hr.employee'].search([('workwx_id', '=', employee_info.get('userid'))])
                if not employee_id:
                    add_count += 1
                    employee_id = self.env['hr.employee'].create({
                        'name': employee_info.get('name'),
                        'work_email': employee_info.get('email') or False,
                        'work_phone': employee_info.get('mobile') or False,
                    })
                employee_id.update_workwx_info(employee_info)
                if self.create_user and not employee_id.user_id:
                    create_user_ids |= employee_id
            if self.del_nonexistent_employee:
                del_employee_ids = self._del_nonexistent_employee(department_id, info.get('userlist'))
                del_count += len(del_employee_ids)
        msg = f'共同步企业微信员工{len(info.get("userlist"))}个,新增{add_count}个,删除{del_count}个'
        if create_user_ids:
            count, create_fail = self.create_sys_user(create_user_ids)
            msg += f',新建odoo用户{count}个'
            for fail in create_fail:
                msg += f'\n{fail["name"]}创建odoo用户失败:{fail["error"]}'
        logger.info(msg)
        msg = msg.replace('\n', '<br/>')
        return {
            'type': 'ir.actions.client',
            'tag': 'dialog',
            'params': {
                'title': '同步完成',
                '$content': f'<h5 style=" text-align:center; ">{msg}</h5>',
                'size': 'medium',
            }
        }

    def _del_nonexistent_employee(self, department_id, userlist):
        """删除员工"""
        if self.fetch_child:
            department_id_list = self.env['hr.department'].search([('id', 'child_of', department_id.id)]).ids
        else:
            department_id_list = department_id.ids
        userlist = [info.get('userid') for info in userlist]
        del_employee_ids = self.env['hr.employee'].search(
            [('workwx_id', 'not in', userlist), ('department_id', 'in', department_id_list)])
        for del_employee_id in del_employee_ids:
            del_employee_id.active = False
            if del_employee_id.user_id:
                del_employee_id.user_id.action_archive()
                del_employee_id.user_id.partner_id and del_employee_id.user_id.partner_id.action_archive()
        return del_employee_ids

    def create_sys_user(self, create_user_ids):
        default_user = self.env.ref('base.default_user').sudo()
        provider = self.env.ref('workwx_base.provider_workwx').sudo()
        create_fail = []
        count = 0
        for employee_id in create_user_ids:
            if not employee_id.work_email and not employee_id.work_phone:
                create_fail.append({'name': employee_id.name, 'error': '创建odoo用户员工信息邮箱/手机号二选一必填'})
                continue
            try:
                with self.env.cr.savepoint():
                    user_id = self.env['res.users'].sudo().with_context(active_test=False).search(
                        [('oauth_provider_id', '=', provider.id), ('oauth_uid', '=', employee_id.workwx_id)])
                    if user_id and not user_id.active:
                        create_fail.append({
                            'name': employee_id.name,
                            'error': f'odoo中已存在账号为{employee_id.work_email or employee_id.work_phone}的归档用户,'
                                     f'请将归档用户删除或者更改账号'})
                        continue
                    if not user_id:
                        user_id = default_user.copy({
                            'active': True,
                            'name': employee_id.name,
                            'login': employee_id.work_email or employee_id.work_phone,
                            'image_1920': employee_id.image_1920,
                            'oauth_provider_id': provider.id,
                            'oauth_uid': employee_id.workwx_id,
                        })
            except Exception as e:
                logger.exception(e)
                if 'res_users_login_key' in str(e):
                    create_fail.append({
                        'name': employee_id.name,
                        'error': f'odoo中已存在账号为{employee_id.work_email or employee_id.work_phone}的用户'})
                if 'res_users_uniq_users_oauth_provider_oauth_uid' in str(e):
                    create_fail.append({
                        'name': employee_id.name,
                        'error': f'odoo中已存在OAuth用户ID为{employee_id.workwx_id}的用户'})
                continue
            employee_id.user_id = user_id.id
            count += 1
        return count, create_fail
