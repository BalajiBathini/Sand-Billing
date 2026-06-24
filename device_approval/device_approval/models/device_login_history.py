# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class DeviceLoginHistory(models.Model):
    _name = 'device.login.history'
    _description = 'Device Login History'
    _order = 'login_date desc'
    _rec_name = 'login_date'

    user_id = fields.Many2one(
        'res.users', string='User',
        required=True, ondelete='cascade',
        index=True,
    )
    device_id = fields.Many2one(
        'res.user.device', string='Device',
        ondelete='set null', index=True,
    )
    login_date = fields.Datetime(
        string='Login Date',
        default=fields.Datetime.now,
        required=True,
    )
    ip_address = fields.Char(string='IP Address')
    browser = fields.Char(string='Browser')
    os_name = fields.Char(string='Operating System')
    fingerprint = fields.Char(string='Device Fingerprint')
    login_status = fields.Selection(
        selection=[
            ('success', 'Success'),
            ('blocked', 'Blocked – Pending Approval'),
            ('rejected', 'Blocked – Rejected'),
            ('failed', 'Failed – Wrong Credentials'),
        ],
        string='Status',
        required=True,
        default='success',
    )
    user_agent = fields.Char(string='User Agent')

    @api.model
    def log_attempt(self, user_id, fingerprint, device_info, status):
        """Create a login history record."""
        try:
            self.sudo().create({
                'user_id': user_id,
                'fingerprint': fingerprint,
                'ip_address': device_info.get('ip_address', ''),
                'browser': device_info.get('browser', ''),
                'os_name': device_info.get('os_name', ''),
                'user_agent': device_info.get('user_agent', ''),
                'login_status': status,
            })
        except Exception as e:
            _logger.warning('Failed to log device login attempt: %s', e)
