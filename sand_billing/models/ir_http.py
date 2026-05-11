from odoo import models
from odoo.http import request
from werkzeug.utils import redirect

class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _dispatch(cls):

        excluded_paths = [
            '/web/login',
            '/web/session/logout',
            '/web/webclient/version_info',
        ]

        if request.httprequest.path in excluded_paths:
            return super()._dispatch()

        if request and request.session.uid:

            user = request.env['res.users'].sudo().browse(request.session.uid)

            if (
                user.exists()
                and user.active_session_id
                and user.active_session_id != request.session.sid
            ):

                request.session.logout(keep_db=True)

                return redirect(
                    '/web/login?message=Logged+in+from+another+device'
                )

        return super()._dispatch()