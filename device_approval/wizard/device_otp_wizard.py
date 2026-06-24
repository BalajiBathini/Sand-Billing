# -*- coding: utf-8 -*-
import random
from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class DeviceOtpWizard(models.TransientModel):
    _name = 'device.otp.wizard'
    _description = 'Device OTP Verification Wizard'

    device_id = fields.Many2one(
        'res.user.device', string='Device',
        required=True,
    )
    otp_code = fields.Char(
        string='OTP Code',
        required=True,
        size=6,
        placeholder='Enter 6-digit OTP',
    )

    def action_verify_otp(self):
        self.ensure_one()
        device = self.device_id
        now = fields.Datetime.now()

        if device.otp_code != self.otp_code:
            raise UserError(_('Invalid OTP code. Please check and try again.'))

        if device.otp_expiry and now > device.otp_expiry:
            raise UserError(_('OTP has expired. Please request a new OTP.'))

        device._check_device_limit()
        device.write({
            'status': 'approved',
            'approved_date': now,
            'approved_by': self.env.uid,
            'otp_code': False,
            'otp_expiry': False,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Device Approved via OTP'),
                'message': _('Device has been successfully verified and approved.'),
                'type': 'success',
            },
        }
