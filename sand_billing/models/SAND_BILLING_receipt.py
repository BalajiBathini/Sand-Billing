from odoo import models, fields, api
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError
import qrcode
import io
import base64
import pytz


class SandBillingReceipt(models.Model):
    _name = 'sand.billing.receipt'
    _description = 'Sand Billing Receipt'
    _rec_name = 'receipt_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def write(self, vals):
        for rec in self:
            if rec.state == 'printed' and not self.env.user.has_group('sand_billing.group_sand_manager') and 'state' not in vals:
                raise ValidationError("You cannot edit a receipt after it has been printed!")
        return super(SandBillingReceipt, self).write(vals)

    # Receipt Details
    receipt_id = fields.Char(string='Receipt ID', readonly=True, copy=False)
    order_id = fields.Char(string='Registration ID', required=True)
    trip_no = fields.Char(string='Trip Number',default='1', required=True)

    # Consumer Details
    customer_name = fields.Char(string='Consumer Name', required=True)
    customer_mobile = fields.Char(string='Consumer Mobile', required=True)

    # Registration Details
    registration_date = fields.Datetime(string='Registration Date', required=True, default=fields.Datetime.now)
    registration_type = fields.Selection([
        ('general', 'GENERAL SAND CONSUMPTION')
    ], string='Registration Type', default='general', required=True)
    registration_qty = fields.Float(string='Registration QTY(in Tons)', default=480.0, required=True)
    registration_address = fields.Text(string='Registration Address', required=True)

    # Sand Calculations
    available_sand_qty = fields.Float(string='Available Sand QTY(in Tons)')
    eligible_sand_qty = fields.Float(string='Eligible Sand QTY(in Tons)', compute='_compute_eligible_sand_qty', store=True)

    # Dispatch Details
    dispatch_id = fields.Char(string='Dispatch ID', readonly=True, copy=False)
    hologram_id = fields.Char(string='Hologram Id', copy=False)
    vehicle_no = fields.Char(string='Vehicle Number', required=True)
    vehicle_type = fields.Selection([('ace','Ace Auto'),
('tractor','Tractor'),('6_tyre','6-Tyre'),('10_tyre','10-Tyre') ,('12_tyre','12-Tyre'),('14_tyre','14-Tyre'),('16_tyre', '16-Tyre'),], string='Vehicle Type', required=True)
    dispatch_qty = fields.Float(string='Dispatch QTY(in Tons)', required=True)
    dispatch_date = fields.Datetime(string='Dispatch Date Time', required=True, default=fields.Datetime.now)
    address = fields.Text(string='Dispatch Address',related='registration_address', required=True)

    # Driver Details
    driver_name = fields.Char(string='Driver Name', required=True)
    driver_phone = fields.Char(string='Driver Mobile No', required=True)

    # Sand Details (Legacy/Internal)
    sand_quantity = fields.Float(string='Sand Quantity (Tons)', related='dispatch_qty', readonly=False)
    sand_supply_point = fields.Char(string='Sand Supply Point Name',default='CC REVU-C Venkatapathi', required=True)

    # Additional Details
    construction_name = fields.Char(string='Construction Name', required=True)
    gps_coordinates = fields.Char(string='GPS Coordinates')

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
    user_id = fields.Many2one('res.users', string='Salesperson / Owner', default=lambda self: self.env.user, tracking=True)

    def _get_ist_time_str(self, field_name):
        """Helper to return IST formatted string (12-hour) for a datetime field"""
        self.ensure_one()
        dt_value = getattr(self, field_name)
        if not dt_value:
            return '-'
        
        # Odoo datetimes are stored in UTC
        if not dt_value.tzinfo:
            dt_value = pytz.utc.localize(dt_value)
        
        # Convert to Asia/Kolkata
        ist_tz = pytz.timezone('Asia/Kolkata')
        ist_dt = dt_value.astimezone(ist_tz)
        
        return ist_dt.strftime('%d-%m-%Y %I:%M %p')

    @api.depends('registration_qty')
    def _compute_eligible_sand_qty(self):
        for record in self:
            record.eligible_sand_qty = record.registration_qty

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('receipt_id', '/') == '/':
                vals['receipt_id'] = self.env['ir.sequence'].next_by_code('sand.billing.receipt') or '/'
        return super(SandBillingReceipt, self).create(vals_list)

    def action_confirm(self):
        """Confirm receipt and generate QR code"""
        for record in self:
            # Generate Dispatch ID: GCTR + Timestamp(IST) + C1 + 8-digit Sequence
            if not record.dispatch_id:
                ist_tz = pytz.timezone('Asia/Kolkata')
                now = datetime.now(pytz.utc).astimezone(ist_tz)
                timestamp = now.strftime('%Y%m%d%H%M%S')
                seq_num = self.env['ir.sequence'].next_by_code('sand.dispatch.id.number') or '186566' # Fallback for demo
                record.dispatch_id = f"GCTR{timestamp}C1{seq_num}"

            # Generate QR Code URL
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
            # Ensure URL doesn't have trailing slash
            if base_url.endswith('/'):
                base_url = base_url[:-1]
            
            qr_data = f"{base_url}/sand/mobile/view?receipt_id={record.receipt_id}"
            
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
        for record in self:
            if record.state == 'confirmed':
                record.state = 'printed'
        return self.env.ref('sand_billing.action_sand_receipt_report').report_action(self)

    def action_reset_to_draft(self):
        """Reset receipt back to draft"""
        for record in self:
            record.write({'state': 'draft'})

