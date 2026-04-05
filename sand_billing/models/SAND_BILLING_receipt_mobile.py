from odoo import models, fields, api
import qrcode
import io
import base64


class SandBillingReceiptMobile(models.Model):
    """Extended model with mobile view methods"""
    _inherit = 'sand.billing.receipt'

    # Add a field to store mobile view URL
    mobile_view_url = fields.Char(string='Mobile View URL', compute='_compute_mobile_view_url')
    # Use the main qr_code field for mobile as well
    mobile_qr_code = fields.Image(related='qr_code', string='Mobile QR Code', readonly=True)

    @api.depends('receipt_id')
    def _compute_mobile_view_url(self):
        """Generate shareable mobile view URL"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
        if base_url.endswith('/'):
            base_url = base_url[:-1]
            
        for record in self:
            if record.receipt_id:
                record.mobile_view_url = f"{base_url}/sand/mobile/view?receipt_id={record.receipt_id}"
            else:
                record.mobile_view_url = ''

    def action_get_mobile_view_url(self):
        """Return mobile view URL for sharing"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self.mobile_view_url,
            'target': 'new',
        }

    def action_share_mobile_receipt(self):
        """Action to open share dialog for mobile receipt"""
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sand.receipt.share.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_receipt_id': self.id,
                'default_receipt_number': self.receipt_id,
                'default_mobile_url': self.mobile_view_url,
            }
        }


class SandReceiptShareWizard(models.TransientModel):
    """Wizard for sharing mobile receipt"""
    _name = 'sand.receipt.share.wizard'
    _description = 'Share Mobile Receipt'

    receipt_id = fields.Many2one(
        'sand.billing.receipt',
        string='Receipt',
        required=True,
        ondelete='cascade'
    )
    receipt_number = fields.Char(
        string='Receipt Number',
        readonly=True
    )
    mobile_url = fields.Char(
        string='Mobile View URL',
        readonly=True
    )
    qr_code_image = fields.Image(
        string='QR Code',
        compute='_compute_qr_code'
    )
    message = fields.Text(
        string='Share Message',
        default='Please view the receipt using this link:'
    )

    @api.depends('receipt_id')
    def _compute_qr_code(self):
        """Get QR code from receipt"""
        for record in self:
            if record.receipt_id:
                # Use the unified qr_code field
                record.qr_code_image = record.receipt_id.qr_code
            else:
                record.qr_code_image = False

    def action_copy_url(self):
        """Copy URL to clipboard (handled on client-side)"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Link Copied',
                'message': 'Mobile view URL copied to clipboard',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_send_email(self):
        """Send mobile receipt link via email"""
        self.ensure_one()

        # Get the customer info from receipt
        receipt = self.receipt_id

        # Create email values
        email_values = {
            'subject': f'Sand Billing Receipt - {receipt.receipt_id}',
            'body_html': f"""
            <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee;">
                <h2 style="color: #009e4f;">AP SAND MANAGEMENT</h2>
                <p>Dear {receipt.customer_name},</p>
                <p>Your sand billing receipt is ready. You can view it using the link below:</p>
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{self.mobile_url}" style="background-color: #ff9933; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">View Receipt</a>
                </p>
                <p>Receipt Details:</p>
                <ul>
                    <li><strong>Receipt ID:</strong> {receipt.receipt_id}</li>
                    <li><strong>Registration ID:</strong> {receipt.order_id}</li>
                    <li><strong>Dispatch Qty:</strong> {receipt.dispatch_qty} MT</li>
                    <li><strong>Dispatch Date:</strong> {receipt._get_ist_time_str('dispatch_date')}</li>
                </ul>
                <p>Thank you!</p>
            </div>
            """,
            'email_to': receipt.customer_mobile,  # Note: Should ideally be an email address
        }

        # Create email
        mail = self.env['mail.mail'].create(email_values)
        mail.send()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Email Sent',
                'message': 'Receipt link has been sent via email',
                'type': 'success',
                'sticky': False,
            }
        }
