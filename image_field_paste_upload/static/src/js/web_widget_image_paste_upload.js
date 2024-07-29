odoo.define("web_widget_image_paste_upload.image_paste_upload", function (require) {
    "use strict";

    const {patch} = require("@web/core/utils/patch");
    const {ImageField} = require("@web/views/fields/image/image_field");

    patch(ImageField.prototype, "web_widget_image_paste_upload", {

        onFilePaste(ev) {
            var self = this;
            const items = ev.clipboardData.items;
            for (let item of items) {
                if (item.kind === 'file' && item.type.startsWith('image/')) {
                    const file = item.getAsFile();
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        const base64String = e.target.result;
                        self.onFileUploaded({
                            data: base64String.split(',')[1],
                        })
                    };
                    reader.readAsDataURL(file);
                }
            }
        },

        cleanPaste(ev) {
            document.querySelector('.o_input_paste_area').innerHTML = '<i class="fa fa-copy fa-fw"></i>';
        },

    })

});