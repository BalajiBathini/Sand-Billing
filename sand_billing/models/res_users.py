from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'
    
    active_session_id = fields.Char("Active Session ID")
