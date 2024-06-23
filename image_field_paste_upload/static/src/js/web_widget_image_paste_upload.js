odoo.define('web_widget_image_paste_upload.widget', function (require) {
    'use strict';

    var FieldBinaryImage = require('web.basic_fields').FieldBinaryImage;

    FieldBinaryImage.include({
        events: _.extend({}, FieldBinaryImage.prototype.events, {
            'paste .o_input_paste_area': '_on_paste',
        }),

        _on_paste: function (event) {
            const items = event.originalEvent.clipboardData.items;
            for (let item of items) {
                if (item.kind === 'file' && item.type.startsWith('image/')) {
                    const file = item.getAsFile();
                    const dataTransfer = new DataTransfer();
                    dataTransfer.items.add(file);
                    this.$('.o_input_file')[0].files = dataTransfer.files;
                    this.$('.o_input_file').trigger('change');
                    break;
                }
            }
        },

        _render: function () {
            this._super();
            const pasteArea = this.$('.o_input_paste_area');
            if (pasteArea.length) {
                pasteArea.empty();
                pasteArea[0].textContent = 'Paste pictures here to upload';
            }
        },

        _renderReadonly: function () {
            this._super();
            const pasteArea = this.$('.o_input_paste_area');
            if (pasteArea.length) {
                pasteArea[0].style.display = "none";
            }
        },

    });
});
