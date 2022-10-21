import io
import json
import base64
import zipfile
from odoo import http
from odoo.http import request
from odoo.http import content_disposition


class DownloadAllMain(http.Controller):

    @http.route('/web/content/ir.attachment/download_all', type='http', auth='public')
    def download_all(self, res_id, model):
        record_id = request.env[model].browse(int(res_id))
        file_content = self.zip_record_attachments(int(res_id), model)
        return http.request.make_response(file_content,
                                          [("Content-Type", "application/zip"),
                                           ("Content-Disposition",
                                            content_disposition(f'{record_id.display_name}.zip'))])

    @staticmethod
    def zip_record_attachments(res_id, res_model):
        tmp = io.BytesIO()
        f = zipfile.ZipFile(tmp, 'w', zipfile.ZIP_STORED)
        for attachment in request.env['ir.attachment'].sudo().search(
                [('res_id', '=', res_id), ('res_model', '=', res_model)]):
            status, headers, content = request.env['ir.http'].binary_content(model=attachment._name, id=attachment.id,
                                                                             filename=attachment.name, field='datas',
                                                                             download=True)
            f.writestr(attachment.name, base64.b64decode(content))
        f.close()
        return tmp.getvalue()
