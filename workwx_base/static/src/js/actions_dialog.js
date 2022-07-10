odoo.define('woekwx_base.actions_dialog_view', function (require) {
    'use strict';

    // 增加一个dialog动作,可在python方法中直接返回一个窗口,使用方法如下:
    // def action_dialog(self):
    //     return {
    //         'type': 'ir.actions.client',
    //         'tag': 'dialog',
    //         'params': {
    //              'title': '提示信息',
    //              '$content': '<h2 style="color:red; text-align:center; ">123456789</h2>',
    //              'size': 'extra-large',
    //             }
    //         }
    //

    var core = require('web.core');
    var Dialog = require('web.Dialog');

    function AlertDialog (parent, action) {
        var dialog = new Dialog(this, action.params);
        dialog.open();
    }

    core.action_registry.add("dialog", AlertDialog);
});
