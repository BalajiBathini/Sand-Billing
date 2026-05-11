from odoo.addons.web.controllers.home import Home
from odoo.http import request
from odoo import http

class AuthSessionController(Home):

    @http.route()
    def web_logout(self, redirect='/web', **kw):

        if request.session.uid:
            user = request.env['res.users'].sudo().browse(request.session.uid)
            user.active_session_id = False

        return super().web_logout(redirect=redirect, **kw)