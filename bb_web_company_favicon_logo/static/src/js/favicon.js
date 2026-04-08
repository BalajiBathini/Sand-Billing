/** @odoo-module **/

import { WebClient } from "@web/webclient/webclient";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";

patch(WebClient.prototype, {
    setup() {
        super.setup();

        onMounted(() => {
            const companyId = odoo.session_info?.user_companies?.current_company;

            if (!companyId) return;

            const favicon = `/web/image/res.company/${companyId}/favicon`;

            document.querySelectorAll("link[rel*='icon']")
                .forEach(icon => icon.href = favicon);

            const msIcon = document.querySelector("meta[name='msapplication-TileImage']");
            if (msIcon) {
                msIcon.content = favicon;
            }
        });
    },
});