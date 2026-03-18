from odoo import models, fields, api
from datetime import datetime
import qrcode
import io
import base64


class SandBillingReceipt(models.Model):
    _name = 'sand.billing.receipt'
    _description = 'Sand Billing Receipt'
    _rec_name = 'receipt_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Receipt Details
    receipt_id = fields.Char(string='Receipt ID', readonly=True, copy=False)
    order_id = fields.Char(string='Order ID', required=True)
    trip_no = fields.Char(string='Trip No', required=True)

    # Customer Details
    customer_name = fields.Char(string='Customer Name', required=True)
    customer_mobile = fields.Char(string='Customer Mobile Number', required=True)

    # Sand Details
    sand_quantity = fields.Float(string='Sand Quantity (Tons)', required=True)
    sand_supply_point = fields.Char(string='Sand Supply Point Name', required=True)

    # Date and Time
    dispatch_date = fields.Datetime(string='Dispatch Date & Time', required=True, default=fields.Datetime.now)
    registration_date = fields.Datetime(string='Registration Date & Time', required=True, default=fields.Datetime.now)

    # Driver Details
    driver_name = fields.Char(string='Driver Name', required=True)
    driver_phone = fields.Char(string='Driver Phone Number', required=True)
    vehicle_no = fields.Char(string='Vehicle No', required=True)

    # Address Details
    address = fields.Text(string='Address', required=True)
    registration_address = fields.Text(string='Registration Address', required=True)

    # Additional Details
    construction_name = fields.Char(string='Construction Name', required=True)
    dispatch_id = fields.Char(string='Dispatch ID', readonly=True, copy=False)

    # Status
    state = fields.Selection(
        [('draft', 'Draft'), ('confirmed', 'Confirmed'), ('printed', 'Printed')],
        string='Status',
        default='draft',
        readonly=True
    )

    # QR Code
    qr_code = fields.Image(string='QR Code', readonly=True)

    # Company Logo
    company_logo = fields.Image(string='Company Logo', related='company_id.logo', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    # Created date for reference
    created_date = fields.Datetime(string='Created Date', readonly=True, default=fields.Datetime.now)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('receipt_id', '/') == '/':
                vals['receipt_id'] = self.env['ir.sequence'].next_by_code('sand.billing.receipt') or '/'
        return super(SandBillingReceipt, self).create(vals_list)

    def action_confirm(self):
        """Confirm receipt and generate QR code"""
        for record in self:
            # Generate Dispatch ID
            if not record.dispatch_id:
                record.dispatch_id = self.env['ir.sequence'].next_by_code('sand.dispatch.id') or 'DISP/'

            # Generate QR Code
            qr_data = (
                f"SAND BILLING RECEIPT\n"
                f"Receipt ID: {record.receipt_id}\n"
                f"Order ID: {record.order_id}\n"
                f"Trip No: {record.trip_no}\n"
                f"Customer: {record.customer_name}\n"
                f"Mobile: {record.customer_mobile}\n"
                f"Quantity: {record.sand_quantity} Tons\n"
                f"Supply Point: {record.sand_supply_point}\n"
                f"Driver: {record.driver_name}\n"
                f"Vehicle: {record.vehicle_no}\n"
                f"Address: {record.address.replace('\n', ' ')}\n"
                f"Dispatch ID: {record.dispatch_id}\n"
                f"Dispatch Date: {record.dispatch_date}"
            ).strip()
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=2,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            qr_image = base64.b64encode(buffer.getvalue())

            record.write({
                'state': 'confirmed',
                'qr_code': qr_image
            })

    def action_print_receipt(self):
        """Generate thermal receipt"""
        return self.env.ref('SAND_BILLING.action_sand_receipt_report').report_action(self)

    def action_reset_to_draft(self):
        """Reset receipt back to draft"""
        for record in self:
            record.write({'state': 'draft'})

