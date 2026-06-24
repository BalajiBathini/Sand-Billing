# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.exceptions import AccessDenied

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    device_ids = fields.One2many(
        'res.user.device', 'user_id',
        string='Registered Devices',
    )
    approved_device_count = fields.Integer(
        string='Approved Devices',
        compute='_compute_device_counts',
    )
    pending_device_count = fields.Integer(
        string='Pending Devices',
        compute='_compute_device_counts',
    )
    device_approval_enabled = fields.Boolean(
        string='Device Approval Enabled',
        default=True,
        help='If disabled, this user can login from any device.',
    )

    def _compute_device_counts(self):
        DeviceModel = self.env['res.user.device'].sudo()
        for user in self:
            user.approved_device_count = DeviceModel.search_count([
                ('user_id', '=', user.id),
                ('status', '=', 'approved'),
            ])
            user.pending_device_count = DeviceModel.search_count([
                ('user_id', '=', user.id),
                ('status', '=', 'pending'),
            ])

    def action_view_devices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Devices for %s') % self.name,
            'res_model': 'res.user.device',
            'view_mode': 'list,form',
            'domain': [('user_id', '=', self.id)],
            'context': {'default_user_id': self.id},
        }
