# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class DeviceRejectWizard(models.TransientModel):
    _name = 'device.reject.wizard'
    _description = 'Device Rejection Wizard'

    device_id = fields.Many2one(
        'res.user.device', string='Device',
        required=True, readonly=True,
    )
    rejection_reason = fields.Text(
        string='Rejection Reason',
        required=True,
        placeholder='Enter the reason for rejecting this device...',
    )

    def action_confirm_reject(self):
        self.ensure_one()
        device = self.device_id
        if device.status not in ('pending', 'approved'):
            raise UserError(_('This device cannot be rejected in its current state.'))
        device.write({
            'status': 'rejected',
            'rejection_reason': self.rejection_reason,
            'rejected_date': fields.Datetime.now(),
        })
        # User email notification has been intentionally disabled here
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Device Rejected'),
                'message': _('Device "%s" has been rejected.') % device.device_name,
                'type': 'warning',
            },
        }
