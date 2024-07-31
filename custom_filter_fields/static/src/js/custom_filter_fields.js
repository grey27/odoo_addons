odoo.define("custom_filter_fields.custom_filter_item", function (require) {
    "use strict";

    const {patch} = require("@web/core/utils/patch");
    const {CustomFilterItem} = require("@web/search/filter_menu/custom_filter_item");

    patch(CustomFilterItem.prototype, "custom_filter_fields", {

        _onSearchInput(ev) {
            var filter = ev.target.value.toLowerCase();
            var options = ev.target.nextElementSibling.options;
            var hasMatch = false;
            for (var i = 0; i < options.length; i++) {
                var optionText = options[i].text.toLowerCase();
                if (optionText.includes(filter)) {
                    options[i].style.display = '';
                    hasMatch = true;
                } else {
                    options[i].style.display = 'none';
                }

            }
            if (!hasMatch) {
                for (var i = 0; i < options.length; i++) {
                    options[i].style.display = '';
                }
            }
        }

    })

});