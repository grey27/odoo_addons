odoo.define('download_all_attachment/static/src/js/download_all_attachment.js', function (require) {
    'use strict';

    const {patch} = require('web.utils');
    const components = {
        AttachmentBox: require('mail/static/src/components/attachment_box/attachment_box.js'),
    };

    patch(components.AttachmentBox, 'download_all_attachment/static/src/js/download_all_attachment.js', {
        _onClickDownloadAll(ev) {
            ev.stopPropagation();
            const thread = this.env.models['mail.thread'].get(this.props.threadLocalId)
            window.location = `/web/content/ir.attachment/download_all?res_id=${thread.id}&model=${thread.model}`;
        }
    });


});

