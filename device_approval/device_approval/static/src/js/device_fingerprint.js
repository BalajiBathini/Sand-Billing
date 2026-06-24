/**
 * Device Approval – Client-side Fingerprint & Login UX
 *
 * Generates a stable browser-side device fingerprint and injects it
 * into the Odoo login form as a hidden field so the server can use it
 * alongside User-Agent for a more reliable device identity.
 *
 * Also shows a friendly blocked-device banner when the server redirects
 * back with ?device_blocked=1.
 */
(function () {
    "use strict";

    /* ── Fingerprint Generation ──────────────────────────────────────────── */

    /**
     * Generate a lightweight, privacy-respecting device fingerprint.
     * Stored in localStorage so it survives across sessions on the same browser.
     */
    async function getOrCreateFingerprint() {
        const STORAGE_KEY = "odoo_device_fp";
        let fp = localStorage.getItem(STORAGE_KEY);
        if (fp) return fp;

        // Build fingerprint from stable browser properties
        const components = [
            navigator.userAgent,
            navigator.language,
            screen.colorDepth,
            screen.width + "x" + screen.height,
            new Date().getTimezoneOffset(),
            navigator.hardwareConcurrency || "",
            navigator.platform || "",
        ].join("|");

        // Use SubtleCrypto if available, else a simple hash
        if (window.crypto && window.crypto.subtle) {
            const encoder = new TextEncoder();
            const data = encoder.encode(components);
            const hashBuffer = await window.crypto.subtle.digest("SHA-256", data);
            const hashArray = Array.from(new Uint8Array(hashBuffer));
            fp = hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
        } else {
            // Fallback: djb2
            let hash = 5381;
            for (let i = 0; i < components.length; i++) {
                hash = (hash * 33) ^ components.charCodeAt(i);
            }
            fp = (hash >>> 0).toString(16);
        }

        localStorage.setItem(STORAGE_KEY, fp);
        return fp;
    }

    /* ── Inject into Login Form ──────────────────────────────────────────── */

    async function injectFingerprint() {
        const form = document.querySelector("form.oe_login_form");
        if (!form) return;

        const fp = await getOrCreateFingerprint();
        let input = form.querySelector('input[name="device_fingerprint"]');
        if (!input) {
            input = document.createElement("input");
            input.type = "hidden";
            input.name = "device_fingerprint";
            form.appendChild(input);
        }
        input.value = fp;
    }

    /* ── Blocked Device Banner ───────────────────────────────────────────── */

    function showBlockedBanner() {
        const params = new URLSearchParams(window.location.search);
        if (!params.get("device_blocked")) return;

        const status = params.get("device_status") || "pending";
        const container = document.querySelector(".oe_login_form") ||
                          document.querySelector("main") ||
                          document.body;

        const isPending = status === "pending";
        const div = document.createElement("div");
        div.className = "o_device_blocked_alert" + (isPending ? "" : " rejected");
        div.innerHTML = isPending
            ? `<div class="o_device_icon">🔒</div>
               <strong>Device Not Approved</strong>
               Your device is pending administrator approval.
               You will receive an email when your device is approved.`
            : `<div class="o_device_icon">🚫</div>
               <strong>Device Access Denied</strong>
               Access from this device has been rejected.
               Please contact your administrator.`;

        container.insertBefore(div, container.firstChild);
    }

    /* ── Init ────────────────────────────────────────────────────────────── */

    document.addEventListener("DOMContentLoaded", function () {
        injectFingerprint();
        showBlockedBanner();
    });
})();
