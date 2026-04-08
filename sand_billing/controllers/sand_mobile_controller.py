from odoo import http
from odoo.http import request


class SandMobileViewController(http.Controller):
    """Controller for handling mobile QR code scanning view"""

    @http.route('/sand/mobile/view', type='http', auth='public', website=True)
    def sand_mobile_view(self, **kwargs):
        """
        Displays the mobile view for scanning and viewing sand billing receipts

        URL Parameters:
            - receipt_id: Optional receipt ID to load automatically
        """
        receipt_id = kwargs.get('receipt_id', '')

        # Render the template with context
        return request.render(
            'sand_billing.sand_mobile_qr_scanner',
            {
                'receipt_id': receipt_id,
            }
        )

    @http.route('/sand/api/receipt/<path:receipt_id>', type='http', auth='public', csrf=False, website=True)
    def get_receipt_data(self, receipt_id, **kwargs):
        """
        API endpoint to fetch receipt data for mobile view
        Returns JSON with all receipt details
        """
        import json
        try:
            # Clean receipt_id (handle potential encoding/slashes)
            search_id = receipt_id.strip()
            
            receipt = request.env['sand.billing.receipt'].sudo().search(
                [('receipt_id', '=', search_id)],
                limit=1
            )

            if not receipt:
                return request.make_response(
                    json.dumps({'status': 'error', 'message': f'Receipt ID "{search_id}" not found.'}),
                    headers=[('Content-Type', 'application/json')]
                )

            # Format the response
            response_data = {
                'status': 'success',
                'data': {
                    'receipt_id': receipt.receipt_id,
                    'order_id': receipt.order_id,
                    'trip_no': receipt.trip_no,
                    'dispatch_id': receipt.dispatch_id or '-',
                    'customer_name': receipt.customer_name,
                    'customer_mobile': receipt.customer_mobile,
                    'construction_name': receipt.construction_name,
                    'sand_quantity': receipt.sand_quantity,
                    'sand_supply_point': receipt.sand_supply_point,
                    'dispatch_date': receipt._get_ist_time_str('dispatch_date'),
                    'registration_date': receipt._get_ist_time_str('registration_date'),
                    'registration_type': receipt.registration_type,
                    'registration_qty': receipt.registration_qty,
                    'registration_address': receipt.registration_address,
                    'available_sand_qty': receipt.available_sand_qty,
                    'eligible_sand_qty': receipt.eligible_sand_qty,
                    'driver_name': receipt.driver_name,
                    'driver_phone': receipt.driver_phone,
                    'vehicle_no': receipt.vehicle_no,
                    'address': receipt.address,
                    'state': receipt.state,
                }
            }

            return request.make_response(
                json.dumps(response_data),
                headers=[('Content-Type', 'application/json')]
            )

        except Exception as e:
            return request.make_response(
                json.dumps({'status': 'error', 'message': str(e)}),
                headers=[('Content-Type', 'application/json')]
            )
