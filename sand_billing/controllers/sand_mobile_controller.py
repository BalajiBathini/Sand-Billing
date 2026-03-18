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
            'SAND_BILLING.sand_mobile_qr_scanner',
            {
                'receipt_id': receipt_id,
            }
        )

    @http.route('/sand/api/receipt/<receipt_id>', type='json', auth='public')
    def get_receipt_data(self, receipt_id, **kwargs):
        """
        API endpoint to fetch receipt data for mobile view

        Returns JSON with all receipt details
        """
        try:
            receipt = request.env['sand.billing.receipt'].sudo().search(
                [('receipt_id', '=', receipt_id)],
                limit=1
            )

            if not receipt:
                return {'status': 'error', 'message': 'Receipt not found'}

            # Format the response
            response_data = {
                'status': 'success',
                'data': {
                    'receipt_id': receipt.receipt_id,
                    'order_id': receipt.order_id,
                    'trip_no': receipt.trip_no,
                    'dispatch_id': receipt.dispatch_id,
                    'customer_name': receipt.customer_name,
                    'customer_mobile': receipt.customer_mobile,
                    'construction_name': receipt.construction_name,
                    'sand_quantity': receipt.sand_quantity,
                    'sand_supply_point': receipt.sand_supply_point,
                    'dispatch_date': receipt.dispatch_date.isoformat() if receipt.dispatch_date else None,
                    'registration_date': receipt.registration_date.isoformat() if receipt.registration_date else None,
                    'driver_name': receipt.driver_name,
                    'driver_phone': receipt.driver_phone,
                    'vehicle_no': receipt.vehicle_no,
                    'address': receipt.address,
                    'registration_address': receipt.registration_address,
                    'state': receipt.state,
                    'qr_code': receipt.qr_code,
                }
            }

            return response_data

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
