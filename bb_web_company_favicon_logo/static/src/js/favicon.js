/** @odoo-module **/

import { WebClient } from "@web/webclient/webclient";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(WebClient.prototype, {
    setup() {
        super.setup();

        const user = useService("user");   // ✅ correct service

        const companyId = user.currentCompany?.id;  // ✅ safe access

        if (!companyId) {
            return; // prevent crash
        }

        const favicon = `/web/image/res.company/${companyId}/favicon`;

        const icons = document.querySelectorAll("link[rel*='icon']");
        const msIcon = document.querySelector("meta[name='msapplication-TileImage']");

        for (const icon of icons) {
            icon.href = favicon;
        }

        if (msIcon) {
            msIcon.content = favicon;
        }
    },
});