from odoo import models, fields, api
from datetime import datetime
import qrcode
import io
import base64


class SandBillingReceiptMobile(models.Model):
    """Extended model with mobile view methods"""
    _inherit = 'sand.billing.receipt'

    # Add a field to store mobile view URL
    mobile_view_url = fields.Char(string='Mobile View URL', compute='_compute_mobile_view_url', store=False)
    mobile_qr_code = fields.Image(string='Mobile QR Code', readonly=True, help='QR code for mobile view')

    @api.depends('receipt_id')
    def _compute_mobile_view_url(self):
        """Generate shareable mobile view URL"""
        for record in self:
            if record.receipt_id:
                # Get the base URL from configuration
                base_url = self.env['ir.config_parameter'].sudo().get_param(
                    'web.base.url',
                    'http://localhost:8069'
                )
                record.mobile_view_url = f"{base_url}/sand/mobile/view?receipt_id={record.receipt_id}"
            else:
                record.mobile_view_url = ''

    def generate_mobile_qr_code(self):
        """
        Generate QR code for mobile view URL
        This allows sharing the receipt via QR code for mobile viewing
        """
        for record in self:
            if not record.receipt_id:
                continue

            # Get the mobile view URL
            base_url = self.env['ir.config_parameter'].sudo().get_param(
                'web.base.url',
                'http://localhost:8069'
            )
            mobile_url = f"{base_url}/sand/mobile/view?receipt_id={record.receipt_id}"

            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=2,
            )
            qr.add_data(mobile_url)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            qr_image = base64.b64encode(buffer.getvalue())

            record.write({
                'mobile_qr_code': qr_image
            })

    def action_confirm(self):
        """Override confirm to also generate mobile QR code"""
        # Call parent confirm method
        super().action_confirm()

        # Generate mobile QR code
        self.generate_mobile_qr_code()

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
                record.qr_code_image = record.receipt_id.mobile_qr_code
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

        # Get the customer email from receipt
        receipt = self.receipt_id

        # Create email values
        email_values = {
            'subject': f'Sand Billing Receipt - {receipt.receipt_id}',
            'body_html': f"""
            <p>Dear {receipt.customer_name},</p>
            <p>Your sand billing receipt is ready. You can view it using the link below:</p>
            <p><a href="{self.mobile_url}">View Receipt</a></p>
            <p>Or scan the QR code attached to this email.</p>
            <p>Receipt Details:</p>
            <ul>
                <li>Receipt ID: {receipt.receipt_id}</li>
                <li>Order ID: {receipt.order_id}</li>
                <li>Sand Quantity: {receipt.sand_quantity} MT</li>
            </ul>
            <p>Thank you!</p>
            """,
            'email_to': receipt.customer_mobile,  # You might want to link to a res.partner
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
