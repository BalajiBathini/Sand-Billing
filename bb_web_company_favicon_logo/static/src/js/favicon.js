/** @odoo-module **/

import { WebClient } from "@web/webclient/webclient";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";

patch(WebClient.prototype, {
    setup() {
        super.setup();

        onMounted(() => {
            const companyId = odoo.session_info?.user_companies?.current_company || odoo.session_info?.company_id;

            if (!companyId) return;

            // Add unique timestamp for cache-busting
            const favicon = `/web/image/res.company/${companyId}/favicon?unique=${Date.now()}`;

            document.querySelectorAll("link[rel*='icon']")
                .forEach(icon => {
                    icon.href = favicon;
                    // For Chrome/Safari on mobile sometimes need to force re-render
                    const parent = icon.parentNode;
                    parent.removeChild(icon);
                    parent.appendChild(icon);
                });

            const msIcon = document.querySelector("meta[name='msapplication-TileImage']");
            if (msIcon) {
                msIcon.content = favicon;
            }
        });
    },
});