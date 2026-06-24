# -*- coding: utf-8 -*-
import json
import logging
import hashlib

from odoo import http, _
from odoo.http import request
from odoo.addons.web.controllers.home import Home
from odoo.exceptions import AccessDenied

_logger = logging.getLogger(__name__)


def _parse_user_agent(user_agent_string):
    """Simple UA parser — replace with ua-parser lib for production."""
    ua = user_agent_string or ''
    browser = 'Unknown'
    os_name = 'Unknown'

    # Browser detection
    if 'Edg/' in ua:
        browser = 'Edge'
    elif 'OPR/' in ua or 'Opera' in ua:
        browser = 'Opera'
    elif 'Chrome/' in ua:
        browser = 'Chrome'
    elif 'Firefox/' in ua:
        browser = 'Firefox'
    elif 'Safari/' in ua and 'Chrome' not in ua:
        browser = 'Safari'

    # OS detection
    if 'Windows NT 10' in ua:
        os_name = 'Windows 11/10'
    elif 'Windows NT 6' in ua:
        os_name = 'Windows (older)'
    elif 'Macintosh' in ua or 'Mac OS X' in ua:
        os_name = 'macOS'
    elif 'Linux' in ua and 'Android' not in ua:
        os_name = 'Linux'
    elif 'Android' in ua:
        os_name = 'Android'
    elif 'iPhone' in ua or 'iPad' in ua:
        os_name = 'iOS'

    return browser, os_name


def _build_server_fingerprint(request_obj, client_fp=''):
    """Build a stable fingerprint from server-side data + client hint."""
    ua = request_obj.httprequest.user_agent.string or ''
    browser, os_name = _parse_user_agent(ua)
    raw = f"{ua}|{browser}|{os_name}|{client_fp}"
    return hashlib.sha256(raw.encode()).hexdigest(), browser, os_name


def _get_client_ip(request_obj):
    forwarded = request_obj.httprequest.headers.get('X-Forwarded-For')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request_obj.httprequest.remote_addr or ''


class DeviceApprovalHome(Home):
    """Override the standard login controller to enforce device approval."""

    @http.route('/web/login', type='http', auth='none', methods=['POST'], csrf=False, save_session=False)
    def web_login(self, redirect=None, **kw):
        """
        Intercept login POST:
        1. Let Odoo authenticate credentials normally.
        2. On success, check device fingerprint.
        3. Block if device is not approved.
        """
        # ── Run normal login flow first ──────────────────────────────────────
        response = super().web_login(redirect=redirect, **kw)

        # If the standard flow didn't create a valid session, return as-is
        # (wrong password, inactive user, etc.)
        if not request.session.uid:
            return response

        # ── Device check ─────────────────────────────────────────────────────
        env = request.env(user=request.session.uid)
        user = env['res.users'].sudo().browse(request.session.uid)

        # Skip check if device approval is disabled for this user
        if not user.device_approval_enabled:
            return response

        # Skip check for internal admin (uid=1) to avoid lockout
        if request.session.uid == 1:
            return response

        # Build fingerprint
        client_fp = kw.get('device_fingerprint', '')
        fingerprint, browser, os_name = _build_server_fingerprint(request, client_fp)
        ip_address = _get_client_ip(request)
        ua = request.httprequest.user_agent.string or ''

        device_name = f"{browser} on {os_name}"
        device_info = {
            'device_name': device_name,
            'browser': browser,
            'os_name': os_name,
            'ip_address': ip_address,
            'user_agent': ua,
        }

        DeviceModel = env['res.user.device'].sudo()
        HistoryModel = env['device.login.history'].sudo()

        device, is_new = DeviceModel.get_or_create_device(
            user_id=request.session.uid,
            fingerprint=fingerprint,
            device_info=device_info,
        )

        if device.status == 'approved':
            # ✅ Allow login — update last login timestamp
            device.write({'last_login': env['res.lang']._lang_get(
                user.lang or 'en_US') and __import__('odoo').fields.Datetime.now()})
            device.last_login = __import__('odoo').fields.Datetime.now()
            HistoryModel.log_attempt(
                user_id=request.session.uid,
                fingerprint=fingerprint,
                device_info=device_info,
                status='success',
            )
            return response

        # ❌ Block login — destroy session
        status = 'blocked'
        if device.status == 'rejected':
            status = 'rejected'

        HistoryModel.log_attempt(
            user_id=request.session.uid,
            fingerprint=fingerprint,
            device_info=device_info,
            status=status,
        )
        request.session.logout(keep_db=True)

        if device.status == 'pending':
            message = _(
                'Your device is not approved yet. '
                'An administrator has been notified. '
                'Please contact your administrator or wait for approval.'
            )
        else:
            message = _(
                'Access from this device has been rejected. '
                'Please contact your administrator.'
            )

        # Re-render login page with error
        return request.redirect(
            f'/web/login?device_blocked=1&device_status={device.status}'
        )

    # ── AJAX Endpoints ────────────────────────────────────────────────────────

    @http.route('/device_approval/verify_otp', type='json', auth='public', methods=['POST'])
    def verify_otp(self, otp_code, fingerprint, **kw):
        """Allow users to self-approve their device via OTP."""
        import odoo.fields as F
        env = request.env
        device = env['res.user.device'].sudo().search([
            ('fingerprint', '=', fingerprint),
            ('otp_code', '=', otp_code),
            ('status', '=', 'pending'),
        ], limit=1)

        if not device:
            return {'success': False, 'message': _('Invalid OTP code.')}

        if device.otp_expiry and F.Datetime.now() > device.otp_expiry:
            return {'success': False, 'message': _('OTP has expired. Please request a new one.')}

        try:
            device._check_device_limit()
        except Exception as e:
            return {'success': False, 'message': str(e)}

        device.write({
            'status': 'approved',
            'approved_date': F.Datetime.now(),
            'otp_code': False,
            'otp_expiry': False,
        })
        return {'success': True, 'message': _('Device approved! You can now log in.')}

    @http.route('/device_approval/pending_count', type='json', auth='user')
    def pending_count(self, **kw):
        """Return count of pending device approvals (for dashboard badge)."""
        count = request.env['res.user.device'].sudo().search_count([
            ('status', '=', 'pending')
        ])
        return {'count': count}
