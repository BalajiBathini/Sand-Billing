# -*- coding: utf-8 -*-
import secrets
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResUserDevice(models.Model):
    _name = 'res.user.device'
    _description = 'User Device'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'device_name'

    # ── Core Fields ─────────────────────────────────────────────────────────
    user_id = fields.Many2one(
        'res.users', string='User',
        required=True, ondelete='cascade',
        tracking=True,
    )
    device_name = fields.Char(
        string='Device Name', required=True,
        help='Human-readable device identifier',
    )
    browser = fields.Char(string='Browser', tracking=True)
    os_name = fields.Char(string='Operating System', tracking=True)
    ip_address = fields.Char(string='IP Address', tracking=True)
    fingerprint = fields.Char(
        string='Device Fingerprint',
        required=True, index=True,
        help='Unique hash identifying this device',
    )
    status = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('revoked', 'Revoked'),
        ],
        string='Status',
        default='pending',
        required=True,
        tracking=True,
    )

    # ── Dates ────────────────────────────────────────────────────────────────
    last_login = fields.Datetime(string='Last Login', readonly=True)
    approved_date = fields.Datetime(string='Approved On', readonly=True)
    rejected_date = fields.Datetime(string='Rejected On', readonly=True)

    # ── Approval ─────────────────────────────────────────────────────────────
    approved_by = fields.Many2one(
        'res.users', string='Approved By', readonly=True,
    )
    rejection_reason = fields.Text(string='Rejection Reason')

    # ── OTP ──────────────────────────────────────────────────────────────────
    otp_code = fields.Char(string='OTP Code', copy=False)
    otp_expiry = fields.Datetime(string='OTP Expiry', copy=False)

    # ── Computed ─────────────────────────────────────────────────────────────
    login_count = fields.Integer(
        string='Login Count',
        compute='_compute_login_count',
        store=True,
    )
    color = fields.Integer(compute='_compute_color')

    # ── Constraints ──────────────────────────────────────────────────────────
    _sql_constraints = [
        ('fingerprint_user_uniq',
         'UNIQUE(fingerprint, user_id)',
         'This device is already registered for this user.'),
    ]

    # ── Compute Methods ───────────────────────────────────────────────────────
    @api.depends('status')
    def _compute_color(self):
        color_map = {
            'pending': 3,    # yellow
            'approved': 10,  # green
            'rejected': 1,   # red
            'revoked': 6,    # dark red
        }
        for rec in self:
            rec.color = color_map.get(rec.status, 0)

    def _compute_login_count(self):
        history_model = self.env['device.login.history']
        for rec in self:
            rec.login_count = history_model.search_count(
                [('device_id', '=', rec.id)]
            )

    # ── Action Methods ────────────────────────────────────────────────────────
    def action_approve(self):
        self.ensure_one()
        if self.status not in ('pending', 'rejected'):
            raise UserError(_('Only pending or rejected devices can be approved.'))
        self._check_device_limit()
        self.write({
            'status': 'approved',
            'approved_date': fields.Datetime.now(),
            'approved_by': self.env.uid,
        })
        self._send_status_notification('approved')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Device Approved'),
                'message': _('Device "%s" has been approved for %s.') % (
                    self.device_name, self.user_id.name),
                'type': 'success',
            },
        }

    def action_reject(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Device'),
            'res_model': 'device.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_device_id': self.id},
        }

    def action_revoke(self):
        self.ensure_one()
        if self.status != 'approved':
            raise UserError(_('Only approved devices can be revoked.'))
        self.write({
            'status': 'revoked',
            'approved_by': False,
        })
        self._send_status_notification('revoked')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Device Revoked'),
                'message': _('Device "%s" has been revoked.') % self.device_name,
                'type': 'warning',
            },
        }

    def action_send_otp(self):
        """Generate and send OTP to user's email for self-service approval."""
        self.ensure_one()
        import random
        from datetime import timedelta
        otp = str(random.randint(100000, 999999))
        expiry = fields.Datetime.now() + timedelta(minutes=15)
        self.write({'otp_code': otp, 'otp_expiry': expiry})
        template = self.env.ref(
            'device_approval.mail_template_device_otp', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('OTP Sent'),
                'message': _('OTP has been sent to %s.') % self.user_id.email,
                'type': 'info',
            },
        }

    def action_view_login_history(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Login History'),
            'res_model': 'device.login.history',
            'view_mode': 'list,form',
            'domain': [('device_id', '=', self.id)],
            'context': {'default_device_id': self.id},
        }

    # ── Helper Methods ────────────────────────────────────────────────────────
    def _check_device_limit(self):
        """Ensure user has not exceeded the device limit."""
        limit = int(self.env['ir.config_parameter'].sudo().get_param(
            'device_approval.max_devices_per_user', default=5))
        approved_count = self.search_count([
            ('user_id', '=', self.user_id.id),
            ('status', '=', 'approved'),
        ])
        if approved_count >= limit:
            raise UserError(_(
                'User %s has reached the maximum device limit (%d). '
                'Please revoke an existing device before approving a new one.'
            ) % (self.user_id.name, limit))

    def _send_status_notification(self, status):
        """Disabled: Do not send email notification to user about device status change."""
        pass

    @api.model
    def _notify_admin_new_device(self, device):
        """Notify administrators about a new pending device via internal activities."""
        admin_group = self.env.ref('base.group_system', raise_if_not_found=False)
        if not admin_group:
            return
            
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        activity_type_id = activity_type.id if activity_type else 4
        model_id = self.env['ir.model']._get_id('res.user.device')
        
        for admin in admin_group.users:
            self.env['mail.activity'].create({
                'res_model_id': model_id,
                'res_id': device.id,
                'activity_type_id': activity_type_id,
                'user_id': admin.id,
                'summary': 'Review New Device Login',
                'note': f'A new device ({device.device_name}) login attempt by {device.user_id.name} is waiting for approval.',
            })

    @api.model
    def get_or_create_device(self, user_id, fingerprint, device_info):
        """
        Find existing device record or create a pending one.
        Returns (device, is_new) tuple.
        """
        device = self.sudo().search([
            ('user_id', '=', user_id),
            ('fingerprint', '=', fingerprint),
        ], limit=1)

        if device:
            return device, False

        # Create new pending device
        device = self.sudo().create({
            'user_id': user_id,
            'fingerprint': fingerprint,
            'device_name': device_info.get('device_name', 'Unknown Device'),
            'browser': device_info.get('browser', 'Unknown'),
            'os_name': device_info.get('os_name', 'Unknown'),
            'ip_address': device_info.get('ip_address', ''),
            'status': 'pending',
        })
        self._notify_admin_new_device(device)
        return device, True
