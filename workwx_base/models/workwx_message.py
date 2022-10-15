import logging
from functools import wraps

from odoo import fields, models, api, registry, tools
from odoo.addons.workwx_base.models.workwx_api import WorkWXAPI
from odoo.exceptions import UserError, ValidationError
from odoo.tools.convert import safe_eval

logger = logging.getLogger(__name__)

def after_commit(func):
    @wraps(func)
    def wrapped(self, *args, **kwargs):
        dbname = self.env.cr.dbname
        context = self.env.context
        uid = self.env.uid

        @self.env.cr.postcommit.add
        def called_after():
            db_registry = registry(dbname)
            with db_registry.cursor() as cr:
                env = api.Environment(cr, uid, context)
                try:
                    func(self.with_env(env), *args, **kwargs)
                except Exception as e:
                    logger.warning("发送消息通知失败: %s" % self)
                    logger.exception(e)

    return wrapped


class WorkwxMessage(models.Model):
    _name = 'workwx.message'
    _description = '企业微信消息通知'
    _order = 'id desc'

    state = fields.Selection([('wait', '待发送'), ('fail', '发送失败'), ('done', '已发送'), ('withdraw', '已撤回')], string='状态', default='wait')
    message_type = fields.Selection([('text', '文本')], string='消息类型')
    content = fields.Text('消息内容')
    receiver_ids = fields.Many2many('hr.employee', string='接收者')
    send_time = fields.Datetime('发送时间')
    request_body = fields.Char('请求体')
    msgid = fields.Char('消息ID')

    @after_commit
    def message_send(self):
        result, info = WorkWXAPI().message_post(safe_eval(self.request_body))
        if not result:
            logging.exception(f'发送消息失败，{info}')
            self.state = 'fail'
            self.msgid = info
        else:
            self.state = 'done'
            self.msgid = info.get('msgid')
            self.send_time = fields.Datetime.now()

    @after_commit
    def message_withdraw(self):
        result, info = WorkWXAPI().message_recall({'msgid': self.msgid})
        if not result:
            logging.exception(f'撤回消息失败，{info}')
        else:
            self.state = 'withdraw'

    @api.model_create_multi
    def create(self, vals_list):
        records = super(WorkwxMessage, self).create(vals_list)
        for record in records:
            record.generate_request_body()
        return records
    
    def write(self, vals):
        res = super(WorkwxMessage, self).write(vals)
        if vals.get('message_type') or vals.get('content') or vals.get('receiver_ids'):
            for record in self:
                record.generate_request_body()
        return res

    def generate_request_body(self):
        """根据message_type和content生成对应的request_body"""
        generate_func = self._get_generate_func()
        if not generate_func:
            logging.error(f'未设置{self.message_type}对应的消息体生成方法')
            return
        request_body = {
            'touser': '|'.join(self.receiver_ids.mapped('workwx_id')),
            'msgtype': self.message_type,
            'agentid': tools.config.get('workwx_agent_id'),
        }
        request_body.update(generate_func())
        self.request_body = request_body

    def _get_generate_func(self):
        """分发不同类型的构造方法"""
        return {
            'text': self._generate_request_body_text,
        }.get(self.message_type)

    def _generate_request_body_text(self):
        """生成文本类型消息体"""
        return {'text': {'content': self.content}}

