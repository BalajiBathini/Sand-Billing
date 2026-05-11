from odoo.addons.web.controllers.home import Home
from odoo.http import request
from odoo import http

class AuthSessionController(Home):

    @http.route()
    def web_login(self, redirect=None, **kw):
        response = super().web_login(redirect=redirect, **kw)
        
        # In Odoo, authenticate() rotates the session SID after the controller finishes.
        # We must flag the session so the next request grabs the freshly rotated SID.
        if request.httprequest.method == 'POST' and request.params.get('login_success'):
            if request.session.uid:
                request.session['update_active_session'] = True

        return response

    @http.route()
    def web_logout(self, redirect='/web', **kw):

        if request.session.uid:
            user = request.env['res.users'].sudo().browse(request.session.uid)
            user.active_session_id = False

        return super().web_logout(redirect=redirect, **kw)